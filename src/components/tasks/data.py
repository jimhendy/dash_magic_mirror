from __future__ import annotations

import calendar
import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from utils.dates import local_today, utc_now


class TaskRecurrence(StrEnum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(slots=True)
class TaskPerson:
    id: str
    name: str
    created_at: str


@dataclass(slots=True)
class TaskItem:
    id: str
    title: str
    person_id: str
    due_on: date
    recurrence: TaskRecurrence
    created_at: str
    completed_at: str | None = None
    last_completed_at: str | None = None

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def is_recurring(self) -> bool:
        return self.recurrence != TaskRecurrence.ONCE


@dataclass(slots=True)
class TaskSnapshot:
    people: list[TaskPerson]
    tasks: list[TaskItem]


@dataclass(slots=True)
class TaskDigestRow:
    """One line in the compact summary: a single open task plus the person it
    belongs to and whether it's already overdue.
    """

    task: TaskItem
    person: TaskPerson
    overdue: bool


@dataclass(slots=True)
class TaskGroup:
    person: TaskPerson
    tasks: list[TaskItem]
    overdue_count: int


DEFAULT_TASKS_FILE = Path.home() / ".local" / "state" / "magic_mirror" / "tasks.json"


class TaskStore:
    def __init__(self, path: Path | None = None):
        configured = os.environ.get("MAGIC_MIRROR_TASKS_FILE")
        self.path = path or (
            Path(configured).expanduser() if configured else DEFAULT_TASKS_FILE
        )
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> TaskSnapshot:
        with self._lock:
            payload = self._read_payload()
        return TaskSnapshot(
            people=[self._person_from_dict(person) for person in payload["people"]],
            tasks=[self._task_from_dict(task) for task in payload["tasks"]],
        )

    def add_person(self, name: str) -> TaskSnapshot:
        clean_name = " ".join(name.split())
        if not clean_name:
            msg = "Enter a name first."
            raise ValueError(msg)

        with self._lock:
            payload = self._read_payload()
            if any(
                person["name"].strip().casefold() == clean_name.casefold()
                for person in payload["people"]
            ):
                msg = f"{clean_name} already exists."
                raise ValueError(msg)
            payload["people"].append(
                {
                    "id": uuid.uuid4().hex,
                    "name": clean_name,
                    "created_at": utc_now().isoformat(),
                },
            )
            self._write_payload(payload)

        return self.load()

    def add_task(
        self,
        *,
        title: str,
        person_id: str,
        due_on: str,
        recurrence: str,
    ) -> TaskSnapshot:
        clean_title = " ".join(title.split())
        if not clean_title:
            msg = "Enter a task title first."
            raise ValueError(msg)
        if not person_id:
            msg = "Choose a person for the task."
            raise ValueError(msg)

        try:
            due_date = date.fromisoformat(due_on)
        except ValueError as exc:
            msg = "Choose a valid due date."
            raise ValueError(msg) from exc

        recurrence_value = TaskRecurrence(recurrence)

        with self._lock:
            payload = self._read_payload()
            if not any(person["id"] == person_id for person in payload["people"]):
                msg = "Choose an existing person for the task."
                raise ValueError(msg)
            payload["tasks"].append(
                {
                    "id": uuid.uuid4().hex,
                    "title": clean_title,
                    "person_id": person_id,
                    "due_on": due_date.isoformat(),
                    "recurrence": recurrence_value.value,
                    "created_at": utc_now().isoformat(),
                    "completed_at": None,
                    "last_completed_at": None,
                },
            )
            self._write_payload(payload)

        return self.load()

    def complete_task(
        self,
        task_id: str,
        *,
        completed_on: date | None = None,
    ) -> TaskSnapshot:
        today = completed_on or local_today()
        completed_at = utc_now().isoformat()

        with self._lock:
            payload = self._read_payload()
            updated = False
            for task in payload["tasks"]:
                if task["id"] != task_id:
                    continue
                recurrence = TaskRecurrence(task["recurrence"])
                if recurrence == TaskRecurrence.ONCE:
                    if task.get("completed_at"):
                        msg = "That task is already complete."
                        raise ValueError(msg)
                    task["completed_at"] = completed_at
                else:
                    next_due = next_due_date(
                        date.fromisoformat(task["due_on"]),
                        recurrence,
                        reference_date=today,
                    )
                    task["due_on"] = next_due.isoformat()
                    task["last_completed_at"] = completed_at
                updated = True
                break

            if not updated:
                msg = "Task not found."
                raise ValueError(msg)

            self._write_payload(payload)

        return self.load()

    def delete_task(self, task_id: str) -> TaskSnapshot:
        """Remove a task outright - the only way to stop a recurring task,
        which "Done" merely rolls forward to its next occurrence.
        """
        with self._lock:
            payload = self._read_payload()
            remaining = [task for task in payload["tasks"] if task.get("id") != task_id]
            if len(remaining) == len(payload["tasks"]):
                msg = "Task not found."
                raise ValueError(msg)
            payload["tasks"] = remaining
            self._write_payload(payload)

        return self.load()

    def _read_payload(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {"people": [], "tasks": []}
        try:
            with self.path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {"people": [], "tasks": []}

        people = payload.get("people") if isinstance(payload, dict) else None
        tasks = payload.get("tasks") if isinstance(payload, dict) else None
        return {
            "people": people if isinstance(people, list) else [],
            "tasks": tasks if isinstance(tasks, list) else [],
        }

    def _write_payload(self, payload: dict[str, list[dict[str, Any]]]) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        tmp_path.replace(self.path)

    @staticmethod
    def _person_from_dict(payload: dict[str, Any]) -> TaskPerson:
        return TaskPerson(
            id=str(payload.get("id", "")),
            name=str(payload.get("name", "")).strip(),
            created_at=str(payload.get("created_at", "")),
        )

    @staticmethod
    def _task_from_dict(payload: dict[str, Any]) -> TaskItem:
        recurrence = TaskRecurrence(
            str(payload.get("recurrence", TaskRecurrence.ONCE.value)),
        )
        due_on_value = str(payload.get("due_on") or local_today().isoformat())
        return TaskItem(
            id=str(payload.get("id", "")),
            title=str(payload.get("title", "")).strip(),
            person_id=str(payload.get("person_id", "")),
            due_on=date.fromisoformat(due_on_value),
            recurrence=recurrence,
            created_at=str(payload.get("created_at", "")),
            completed_at=payload.get("completed_at"),
            last_completed_at=payload.get("last_completed_at"),
        )


def active_tasks(snapshot: TaskSnapshot) -> list[TaskItem]:
    return [task for task in snapshot.tasks if not task.is_complete]


def overdue_task_count(
    snapshot: TaskSnapshot,
    person_id: str,
    *,
    today: date | None = None,
) -> int:
    current_day = today or local_today()
    return sum(
        1
        for task in active_tasks(snapshot)
        if task.person_id == person_id and task.due_on < current_day
    )


def upcoming_task_rows(
    snapshot: TaskSnapshot,
    *,
    limit: int = 5,
    today: date | None = None,
) -> tuple[list[TaskDigestRow], int]:
    """The next `limit` open tasks across everyone, soonest-due first so
    overdue work floats to the top and genuinely upcoming tasks follow it.

    Returns the visible rows plus the count of further open tasks that
    didn't fit, so the caller can render a "+N more" line.
    """
    current_day = today or local_today()
    people_by_id = {person.id: person for person in snapshot.people}
    rows = [
        TaskDigestRow(
            task=task,
            person=people_by_id[task.person_id],
            overdue=task.due_on < current_day,
        )
        for task in active_tasks(snapshot)
        if task.person_id in people_by_id
    ]
    rows.sort(
        key=lambda row: (
            row.task.due_on,
            row.person.name.casefold(),
            row.task.title.casefold(),
        ),
    )
    visible = rows[:limit]
    return visible, len(rows) - len(visible)


def grouped_open_tasks(snapshot: TaskSnapshot) -> list[TaskGroup]:
    active = active_tasks(snapshot)
    today = local_today()
    groups: list[TaskGroup] = []
    for person in sorted(snapshot.people, key=lambda item: item.name.casefold()):
        tasks = sorted(
            [task for task in active if task.person_id == person.id],
            key=lambda item: (item.due_on, item.title.casefold()),
        )
        groups.append(
            TaskGroup(
                person=person,
                tasks=tasks,
                overdue_count=sum(1 for task in tasks if task.due_on < today),
            ),
        )
    return groups


def recurrence_label(recurrence: TaskRecurrence) -> str:
    return {
        TaskRecurrence.ONCE: "One-off",
        TaskRecurrence.DAILY: "Daily",
        TaskRecurrence.WEEKLY: "Weekly",
        TaskRecurrence.MONTHLY: "Monthly",
    }[recurrence]


def due_label(task: TaskItem, *, today: date | None = None) -> str:
    current_day = today or local_today()
    if task.due_on < current_day:
        return f"Overdue since {_day_month(task.due_on)}"
    if task.due_on == current_day:
        return "Due today"
    if task.due_on == current_day + timedelta(days=1):
        return "Due tomorrow"
    return f"Due {task.due_on.strftime('%a')} {_day_month(task.due_on)}"


def short_due_label(task: TaskItem, *, today: date | None = None) -> str:
    """A terse right-aligned due marker for the compact summary: "Overdue 3 Sep",
    "Today", "Tomorrow", a weekday within the coming week, or "Sat 13 Sep"
    further out.
    """
    current_day = today or local_today()
    delta = (task.due_on - current_day).days
    if delta < 0:
        return f"Overdue {_day_month(task.due_on)}"
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    if delta < 7:
        return task.due_on.strftime("%A")
    return f"{task.due_on.strftime('%a')} {_day_month(task.due_on)}"


def next_due_date(
    due_on: date,
    recurrence: TaskRecurrence,
    *,
    reference_date: date,
) -> date:
    """The occurrence a recurring task rolls to when its current one is
    completed. Completing an occurrence always consumes it, so this always
    advances at least once - even when the task was ticked off early and
    `due_on` is still in the future - then keeps skipping any occurrences
    that have already passed relative to `reference_date` (the completion
    date), so a long-overdue task lands on its next genuinely upcoming slot
    rather than another date in the past.
    """
    next_due = _advance_once(due_on, recurrence)
    while next_due <= reference_date:
        next_due = _advance_once(next_due, recurrence)
    return next_due


def _advance_once(due_on: date, recurrence: TaskRecurrence) -> date:
    if recurrence == TaskRecurrence.DAILY:
        return due_on + timedelta(days=1)
    if recurrence == TaskRecurrence.WEEKLY:
        return due_on + timedelta(days=7)
    if recurrence == TaskRecurrence.MONTHLY:
        year = due_on.year + (1 if due_on.month == 12 else 0)
        month = 1 if due_on.month == 12 else due_on.month + 1
        day = min(due_on.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    msg = f"Unsupported recurring schedule: {recurrence}"
    raise ValueError(msg)


def _day_month(value: date) -> str:
    return f"{value.day} {value.strftime('%b')}"
