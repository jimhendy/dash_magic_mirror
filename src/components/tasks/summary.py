from dash import html

from utils.ui import badge, empty_state, icon

from .data import TaskSnapshot, active_tasks, short_due_label, upcoming_task_rows

_SUMMARY_TASK_LIMIT = 8


def render_tasks_summary(snapshot: TaskSnapshot) -> html.Div:
    if not snapshot.people:
        return empty_state("Tap to add people and tasks", "mdi:account-plus-outline")

    rows, overflow = upcoming_task_rows(snapshot, limit=_SUMMARY_TASK_LIMIT)
    if not rows:
        return empty_state("All caught up", "mdi:check-all")

    children = [
        html.Div(
            [
                icon(
                    "mdi:alert-circle"
                    if row.overdue
                    else "mdi:checkbox-blank-circle-outline",
                    "task-mini__check",
                ),
                html.Div(
                    [
                        html.Div(row.task.title, className="task-mini__title truncate"),
                        html.Div(
                            row.person.name, className="task-mini__person truncate"
                        ),
                    ],
                    className="task-mini__text",
                ),
                html.Span(short_due_label(row.task), className="task-mini__due"),
            ],
            className="task-mini" + (" is-overdue" if row.overdue else ""),
        )
        for row in rows
    ]
    if overflow > 0:
        children.append(html.Div(f"+{overflow} more", className="more"))
    return html.Div(children, className="task-minis")


def render_tasks_badge(snapshot: TaskSnapshot):
    rows, overflow = upcoming_task_rows(snapshot, limit=10_000)
    overdue = sum(1 for row in rows if row.overdue)
    if overdue:
        return badge(f"{overdue} overdue", "bad", "mdi:alert-circle-outline")
    open_count = len(active_tasks(snapshot)) if snapshot.people else 0
    if open_count:
        return badge(f"{open_count} open", "neutral")
    return None
