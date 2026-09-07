from __future__ import annotations

from typing import Any, cast

import dash_mantine_components as dmc
from dash import html

from utils.dates import local_today
from utils.styles import (
    COLORS,
    FONT_SIZES,
    SPACE,
    WEIGHT,
    kicker_style,
    row_style,
)

from .data import (
    TaskGroup,
    TaskRecurrence,
    TaskSnapshot,
    due_label,
    grouped_open_tasks,
    recurrence_label,
)

# The full-screen modal (#full-screen-modal, see core_layout.py) is a plain
# div at z-index 9999. Mantine resolves a Select/DateInput popover's
# z-index to a literal inline style at render time (not a CSS var), so a
# global CSS override can't reach it - it has to be set per-component here,
# above the modal's own z-index, or the popover opens invisibly behind it.
_POPOVER_PROPS = {"zIndex": 10_000}


def render_tasks_fullscreen(
    snapshot: TaskSnapshot,
    component_id: str,
    feedback: dict[str, str] | None = None,
    *,
    pending_delete_id: str | None = None,
) -> html.Div:
    people_options = [
        {"value": person.id, "label": person.name}
        for person in sorted(snapshot.people, key=lambda item: item.name.casefold())
    ]
    groups = grouped_open_tasks(snapshot)

    return html.Div(
        [
            _feedback_row(feedback),
            _people_section(component_id),
            _task_form_section(component_id, people_options),
            _task_list_section(groups, component_id, pending_delete_id),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": SPACE["xl"],
            "padding": SPACE["xl"],
        },
    )


def _feedback_row(feedback: dict[str, str] | None) -> html.Div | None:
    if not feedback or not feedback.get("message"):
        return None

    is_error = feedback.get("tone") == "error"
    accent_color = COLORS["urgent"] if is_error else COLORS["accent"]
    return html.Div(
        feedback["message"],
        style={
            "borderLeft": f"2px solid {accent_color}",
            "paddingLeft": SPACE["md"],
            "color": COLORS["text"],
            "fontSize": FONT_SIZES["meta"],
        },
    )


def _people_section(component_id: str) -> html.Div:
    return html.Div(
        [
            html.Div("People", style=kicker_style()),
            html.Div(
                [
                    dmc.TextInput(
                        id=f"{component_id}-person-name",
                        placeholder="Add a person",
                        size="md",
                    ),
                    dmc.Button(
                        "Add person",
                        id=f"{component_id}-add-person",
                        color="teal",
                        variant="light",
                        size="md",
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr auto",
                    "gap": SPACE["md"],
                    "alignItems": "center",
                },
            ),
        ],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["md"]},
    )


def _task_form_section(
    component_id: str,
    people_options: list[dict[str, str]],
) -> html.Div:
    no_people = not people_options
    form_children = [
        dmc.TextInput(
            id=f"{component_id}-task-title",
            placeholder="Task title",
            disabled=no_people,
            size="md",
        ),
        html.Div(
            [
                dmc.Select(
                    id=f"{component_id}-task-person",
                    data=cast("Any", people_options),
                    placeholder="Assign to",
                    clearable=False,
                    disabled=no_people,
                    size="md",
                    comboboxProps=cast("Any", _POPOVER_PROPS),
                ),
                dmc.DateInput(
                    id=f"{component_id}-task-due-on",
                    value=local_today().isoformat(),
                    valueFormat="D MMM YYYY",
                    clearable=False,
                    disabled=no_people,
                    size="md",
                    popoverProps=cast("Any", _POPOVER_PROPS),
                ),
                dmc.Select(
                    id=f"{component_id}-task-recurrence",
                    data=cast(
                        "Any",
                        [
                            {"value": value.value, "label": recurrence_label(value)}
                            for value in TaskRecurrence
                        ],
                    ),
                    value=TaskRecurrence.ONCE.value,
                    clearable=False,
                    disabled=no_people,
                    size="md",
                    comboboxProps=cast("Any", _POPOVER_PROPS),
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "1.3fr 0.9fr 0.9fr",
                "gap": SPACE["md"],
            },
        ),
        dmc.Button(
            "Add task",
            id=f"{component_id}-add-task",
            color="teal",
            variant="light",
            size="md",
            disabled=no_people,
            style={"alignSelf": "flex-start"},
        ),
    ]
    if no_people:
        form_children.append(
            html.Div(
                "Add a person first, then assign them tasks.",
                style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["meta"]},
            ),
        )

    return html.Div(
        [html.Div("Tasks", style=kicker_style()), *form_children],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["md"]},
    )


def _task_list_section(
    groups: list[TaskGroup],
    component_id: str,
    pending_delete_id: str | None,
) -> html.Div:
    has_tasks = any(group.tasks for group in groups)
    body = (
        [
            html.Div(
                "No open tasks yet.",
                style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["meta"]},
            ),
        ]
        if not has_tasks
        else [_task_group(group, component_id, pending_delete_id) for group in groups]
    )

    return html.Div(
        [html.Div("Open tasks", style=kicker_style()), *body],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["lg"]},
    )


def _task_group(
    group: TaskGroup,
    component_id: str,
    pending_delete_id: str | None,
) -> html.Div:
    header = group.person.name
    if group.overdue_count:
        header = f"{header} · {group.overdue_count} overdue"

    return html.Div(
        [
            html.Div(
                header,
                style=kicker_style(color=COLORS["text_secondary"]),
            ),
            html.Div(
                [
                    _task_row(
                        task,
                        component_id,
                        index == len(group.tasks) - 1,
                        pending_delete_id,
                    )
                    for index, task in enumerate(group.tasks)
                ]
                or [
                    html.Div(
                        "No open tasks.",
                        style={
                            "color": COLORS["text_muted"],
                            "fontSize": FONT_SIZES["meta"],
                        },
                    ),
                ],
                style={"display": "flex", "flexDirection": "column"},
            ),
        ],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["sm"]},
    )


def _task_row(
    task,
    component_id: str,
    is_last: bool,
    pending_delete_id: str | None = None,
) -> html.Div:
    overdue = task.due_on < local_today()
    recurrence_text = recurrence_label(task.recurrence)
    awaiting_confirm = pending_delete_id == task.id
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        task.title,
                        style={
                            "fontSize": FONT_SIZES["primary"],
                            "fontWeight": WEIGHT["regular"],
                            "color": COLORS["text"],
                        },
                    ),
                    html.Div(
                        f"{due_label(task)} · {recurrence_text}",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["urgent"]
                            if overdue
                            else COLORS["text_secondary"],
                            "marginTop": SPACE["xs"],
                        },
                    ),
                ],
                style={"minWidth": 0, "flex": 1},
            ),
            _task_row_actions(task, component_id, awaiting_confirm=awaiting_confirm),
        ],
        style=row_style(
            divider=not is_last,
            accent=overdue or awaiting_confirm,
            display="flex",
            alignItems="center",
            justifyContent="space-between",
            gap=SPACE["lg"],
        ),
    )


def _task_row_actions(
    task,
    component_id: str,
    *,
    awaiting_confirm: bool,
) -> html.Div:
    """The right-hand controls for a task row. Removing a task is a two-tap
    action - "Remove" only arms it, then a distinct "Confirm" commits -
    since deleting a recurring task is the one irreversible thing here.

    Every button (Done / Remove / Confirm / Cancel) is rendered for every
    row on every render, with the pair not relevant to the current state
    just hidden. They're the `Input`s of one pattern-matching callback, and
    a pattern `Input` that matches *zero* live components on a given render
    desynchronises that callback's argument list (Dash raises an
    IndexError building the call) - so the Confirm/Cancel controls must
    stay mounted even while no row is armed.
    """
    hide = {"display": "none"}
    return html.Div(
        [
            dmc.Button(
                "Done",
                id={"type": f"{component_id}-complete-task", "task_id": task.id},
                n_clicks=0,
                color="teal",
                variant="subtle",
                size="xs",
                style=hide if awaiting_confirm else None,
            ),
            dmc.Button(
                "Remove",
                id={"type": f"{component_id}-delete-task", "task_id": task.id},
                n_clicks=0,
                color="red",
                variant="subtle",
                size="xs",
                style=hide if awaiting_confirm else None,
            ),
            html.Span(
                "Remove?",
                style={
                    "fontSize": FONT_SIZES["small"],
                    "color": COLORS["text_secondary"],
                    **({} if awaiting_confirm else hide),
                },
            ),
            dmc.Button(
                "Confirm",
                id={"type": f"{component_id}-confirm-delete", "task_id": task.id},
                n_clicks=0,
                color="red",
                variant="filled",
                size="xs",
                style=None if awaiting_confirm else hide,
            ),
            dmc.Button(
                "Cancel",
                id={"type": f"{component_id}-cancel-delete", "task_id": task.id},
                n_clicks=0,
                color="gray",
                variant="subtle",
                size="xs",
                style=None if awaiting_confirm else hide,
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": SPACE["xs"],
            "flexShrink": 0,
        },
    )
