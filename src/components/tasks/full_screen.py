from __future__ import annotations

from typing import Any, cast

import dash_mantine_components as dmc
from dash import html

from utils.dates import local_today
from utils.ui import empty_state, icon

from .data import (
    TaskGroup,
    TaskRecurrence,
    TaskSnapshot,
    due_label,
    grouped_open_tasks,
    recurrence_label,
)


def people_options(snapshot: TaskSnapshot) -> list[dict[str, str]]:
    return [
        {"value": person.id, "label": person.name}
        for person in sorted(snapshot.people, key=lambda item: item.name.casefold())
    ]


def render_tasks_panel(snapshot: TaskSnapshot, component_id: str) -> html.Div:
    """Static shell of the Tasks panel: the open-task list (refreshed by
    callbacks via `{component_id}-list`) next to the add-task/add-person
    forms. The forms are rendered once with the page and never replaced,
    so a background refresh can't wipe what someone is halfway through
    typing.
    """
    options = people_options(snapshot)
    return html.Div(
        [
            html.Div(
                [
                    html.H3("Open tasks", className="section__title"),
                    html.Div(
                        render_task_list(snapshot, component_id, None),
                        id=f"{component_id}-list",
                    ),
                ],
                className="tasks-list-col",
            ),
            html.Div(
                [
                    html.Div(id=f"{component_id}-feedback", className="toast-slot"),
                    _task_form(component_id, options),
                    _person_form(component_id),
                ],
                className="tasks-form-col",
            ),
        ],
        className="detail tasks-detail",
    )


def render_feedback(feedback: dict[str, str] | None, key: str) -> html.Div | None:
    if not feedback or not feedback.get("message"):
        return None
    is_error = feedback.get("tone") == "error"
    return html.Div(
        [
            icon(
                "mdi:alert-circle-outline" if is_error else "mdi:check-circle-outline",
                "ic",
            ),
            feedback["message"],
        ],
        className="toast" + (" is-error" if is_error else ""),
        key=key,
    )


def _task_form(component_id: str, options: list[dict[str, str]]) -> html.Div:
    return html.Div(
        [
            html.H3("New task", className="section__title"),
            dmc.TextInput(
                id=f"{component_id}-task-title",
                placeholder="What needs doing?",
                size="lg",
            ),
            html.Div("Who", className="field-label"),
            dmc.SegmentedControl(
                id=f"{component_id}-task-person",
                data=cast("Any", options),
                value=options[0]["value"] if options else None,
                fullWidth=True,
                size="md",
                color="teal",
            ),
            html.Div("When", className="field-label"),
            dmc.DatePickerInput(
                id=f"{component_id}-task-due-on",
                value=local_today().isoformat(),
                valueFormat="ddd D MMM YYYY",
                dropdownType="modal",
                firstDayOfWeek=1,
                size="lg",
                leftSection=icon("mdi:calendar", "ic"),
            ),
            html.Div("Repeat", className="field-label"),
            dmc.SegmentedControl(
                id=f"{component_id}-task-recurrence",
                data=cast(
                    "Any",
                    [
                        {"value": v.value, "label": recurrence_label(v)}
                        for v in TaskRecurrence
                    ],
                ),
                value=TaskRecurrence.ONCE.value,
                fullWidth=True,
                size="md",
                color="teal",
            ),
            html.Button(
                [icon("mdi:plus", "ic"), "Add task"],
                id=f"{component_id}-add-task",
                n_clicks=0,
                className="btn btn--primary",
            ),
        ],
        className="card form",
    )


def _person_form(component_id: str) -> html.Div:
    return html.Div(
        [
            html.H3("Add a person", className="section__title"),
            html.Div(
                [
                    dmc.TextInput(
                        id=f"{component_id}-person-name",
                        placeholder="Name",
                        size="lg",
                    ),
                    html.Button(
                        [icon("mdi:account-plus-outline", "ic"), "Add"],
                        id=f"{component_id}-add-person",
                        n_clicks=0,
                        className="btn btn--secondary",
                    ),
                ],
                className="inline-form",
            ),
        ],
        className="card form",
    )


def render_task_list(
    snapshot: TaskSnapshot,
    component_id: str,
    pending_delete_id: str | None,
) -> html.Div:
    groups = grouped_open_tasks(snapshot)
    if not snapshot.people:
        return empty_state(
            "Add a person first, then give them tasks", "mdi:account-plus-outline"
        )
    if not any(group.tasks for group in groups):
        return empty_state("No open tasks – all caught up", "mdi:check-all")
    return html.Div(
        [
            _task_group(group, component_id, pending_delete_id)
            for group in groups
            if group.tasks
        ],
        className="task-groups",
    )


def _task_group(
    group: TaskGroup, component_id: str, pending_delete_id: str | None
) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        group.person.name[:1].upper(), className="person__avatar"
                    ),
                    html.Span(group.person.name, className="task-group__name"),
                    html.Span(
                        f"{group.overdue_count} overdue", className="badge badge--bad"
                    )
                    if group.overdue_count
                    else html.Span(
                        f"{len(group.tasks)}", className="task-group__count"
                    ),
                ],
                className="task-group__head",
            ),
            html.Div(
                [
                    _task_row(task, component_id, pending_delete_id == task.id)
                    for task in group.tasks
                ],
                className="task-rows",
            ),
        ],
        className="card task-group",
    )


def _action(
    component_id: str,
    action: str,
    task_id: str,
    children,
    class_name: str,
    title: str = "",
):
    return html.Button(
        children,
        id={"type": f"{component_id}-act", "action": action, "task_id": task_id},
        n_clicks=0,
        className=class_name,
        title=title,
    )


def _task_row(task, component_id: str, awaiting_confirm: bool) -> html.Div:
    overdue = task.due_on < local_today()
    if awaiting_confirm:
        actions = [
            html.Span("Remove for good?", className="task-row__confirm-text"),
            _action(
                component_id, "confirm", task.id, "Remove", "btn btn--danger btn--sm"
            ),
            _action(component_id, "cancel", task.id, "Keep", "btn btn--ghost btn--sm"),
        ]
    else:
        actions = [
            _action(
                component_id,
                "arm",
                task.id,
                icon("mdi:trash-can-outline", "ic"),
                "icon-btn icon-btn--muted",
                "Remove task",
            ),
        ]
    meta = [due_label(task)]
    if task.is_recurring:
        meta.append(recurrence_label(task.recurrence))
    return html.Div(
        [
            _action(
                component_id,
                "complete",
                task.id,
                icon("mdi:check-bold", "ic"),
                "check-btn",
                "Mark done",
            ),
            html.Div(
                [
                    html.Div(task.title, className="task-row__title"),
                    html.Div(
                        [
                            icon("mdi:repeat", "task-row__repeat")
                            if task.is_recurring
                            else None,
                            " · ".join(meta),
                        ],
                        className="task-row__meta",
                    ),
                ],
                className="task-row__text",
            ),
            html.Div(actions, className="task-row__actions"),
        ],
        className="task-row"
        + (" is-overdue" if overdue else "")
        + (" is-confirming" if awaiting_confirm else ""),
    )
