from datetime import date

import pytest

from components.tasks.data import (
    TaskRecurrence,
    TaskStore,
    active_tasks,
    next_due_date,
    overdue_task_count,
    short_due_label,
    upcoming_task_rows,
)
from utils.dates import local_today


@pytest.fixture
def store(tmp_path):
    return TaskStore(tmp_path / "tasks.json")


def test_add_person_rejects_duplicate_case_insensitive(store):
    store.add_person("Alice")

    with pytest.raises(ValueError, match="already exists"):
        store.add_person(" alice ")


def test_add_task_persists_and_is_counted(store):
    snapshot = store.add_person("Alice")
    person_id = snapshot.people[0].id

    snapshot = store.add_task(
        title="Take bins out",
        person_id=person_id,
        due_on="2026-09-01",
        recurrence=TaskRecurrence.ONCE.value,
    )

    assert len(active_tasks(snapshot)) == 1
    assert overdue_task_count(snapshot, person_id, today=date(2026, 9, 5)) == 1


def test_complete_one_off_marks_task_complete(store):
    snapshot = store.add_person("Alice")
    person_id = snapshot.people[0].id
    snapshot = store.add_task(
        title="Take bins out",
        person_id=person_id,
        due_on="2026-09-01",
        recurrence=TaskRecurrence.ONCE.value,
    )

    snapshot = store.complete_task(snapshot.tasks[0].id, completed_on=date(2026, 9, 5))

    assert active_tasks(snapshot) == []
    assert snapshot.tasks[0].completed_at is not None


def test_complete_recurring_task_advances_to_next_future_slot(store):
    snapshot = store.add_person("Alice")
    person_id = snapshot.people[0].id
    snapshot = store.add_task(
        title="Water plants",
        person_id=person_id,
        due_on="2026-09-01",
        recurrence=TaskRecurrence.WEEKLY.value,
    )

    snapshot = store.complete_task(snapshot.tasks[0].id, completed_on=date(2026, 9, 15))

    assert snapshot.tasks[0].due_on == date(2026, 9, 22)
    assert snapshot.tasks[0].completed_at is None
    assert snapshot.tasks[0].last_completed_at is not None


def test_complete_recurring_task_early_advances_to_next_occurrence(store):
    snapshot = store.add_person("Alice")
    person_id = snapshot.people[0].id
    snapshot = store.add_task(
        title="Water plants",
        person_id=person_id,
        due_on="2026-09-20",
        recurrence=TaskRecurrence.WEEKLY.value,
    )

    # Ticked off nearly two weeks before it's due - it should still roll
    # forward to the following week, not sit unchanged.
    snapshot = store.complete_task(snapshot.tasks[0].id, completed_on=date(2026, 9, 7))

    assert snapshot.tasks[0].due_on == date(2026, 9, 27)
    assert snapshot.tasks[0].last_completed_at is not None


def test_delete_task_removes_it_entirely(store):
    snapshot = store.add_person("Alice")
    person_id = snapshot.people[0].id
    snapshot = store.add_task(
        title="Water plants",
        person_id=person_id,
        due_on="2026-09-01",
        recurrence=TaskRecurrence.WEEKLY.value,
    )
    task_id = snapshot.tasks[0].id

    snapshot = store.delete_task(task_id)

    assert snapshot.tasks == []
    with pytest.raises(ValueError, match="Task not found"):
        store.delete_task(task_id)


def test_monthly_next_due_clamps_to_last_day_of_month():
    assert next_due_date(
        date(2026, 1, 31),
        TaskRecurrence.MONTHLY,
        reference_date=date(2026, 1, 31),
    ) == date(2026, 2, 28)


def test_one_off_next_due_is_rejected():
    with pytest.raises(ValueError, match="Unsupported recurring schedule"):
        next_due_date(
            date(2026, 1, 31),
            TaskRecurrence.ONCE,
            reference_date=date(2026, 1, 31),
        )


def test_upcoming_task_rows_orders_overdue_then_upcoming_and_reports_overflow(store):
    snapshot = store.add_person("Alice")
    person_id = snapshot.people[0].id
    for title, due_on in (
        ("Take bins out", "2026-09-01"),
        ("Pay rent", "2026-09-07"),
        ("Dentist", "2026-09-09"),
        ("Book holiday", "2026-09-30"),
    ):
        snapshot = store.add_task(
            title=title,
            person_id=person_id,
            due_on=due_on,
            recurrence=TaskRecurrence.ONCE.value,
        )

    rows, overflow = upcoming_task_rows(snapshot, limit=3, today=date(2026, 9, 7))

    assert [row.task.title for row in rows] == ["Take bins out", "Pay rent", "Dentist"]
    assert [row.overdue for row in rows] == [True, False, False]
    assert overflow == 1


def test_short_due_label_covers_overdue_today_and_week():
    from components.tasks.data import TaskItem

    def item(task_id: str, due_on: date) -> TaskItem:
        return TaskItem(
            id=task_id,
            title="x",
            person_id="p1",
            due_on=due_on,
            recurrence=TaskRecurrence.ONCE,
            created_at="2026-09-05T00:00:00+00:00",
        )

    today = date(2026, 9, 7)
    assert short_due_label(item("1", date(2026, 9, 1)), today=today) == "Overdue 1 Sep"
    assert short_due_label(item("2", today), today=today) == "Today"
    assert short_due_label(item("3", date(2026, 9, 8)), today=today) == "Tomorrow"
    assert short_due_label(item("4", date(2026, 9, 11)), today=today) == "Friday"


def test_missing_due_date_falls_back_to_today(store):
    snapshot = store.add_person("Alice")
    person_id = snapshot.people[0].id
    store.path.write_text(
        (
            '{"people":[{"id":"'
            + person_id
            + '","name":"Alice","created_at":"2026-09-05T00:00:00+00:00"}],'
            '"tasks":[{"id":"task-1","title":"Bins","person_id":"'
            + person_id
            + '","recurrence":"once","created_at":"2026-09-05T00:00:00+00:00"}]}'
        ),
        encoding="utf-8",
    )

    loaded = store.load()

    assert loaded.tasks[0].due_on == local_today()
