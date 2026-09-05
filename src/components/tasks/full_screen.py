from __future__ import annotations

from dash import dcc, html
import dash_mantine_components as dmc

from utils.dates import local_today
from utils.styles import COLORS, FONT_SIZES, SPACE, WEIGHT, kicker_style, panel_style, row_style

from .data import TaskGroup, TaskRecurrence, TaskSnapshot, due_label, grouped_open_tasks, recurrence_label


_INPUT_STYLE = {
    "width": "100%",
    "background": COLORS["surface"],
    "border": f"1px solid {COLORS['hairline_strong']}",
    "borderRadius": "0.7rem",
    "color": COLORS["text"],
    "padding": "0.7rem 0.9rem",
    "fontSize": FONT_SIZES["meta"],
    "boxSizing": "border-box",
}

_DROPDOWN_STYLE = {
    "background": COLORS["bg"],
    "color": COLORS["text"],
}


def render_tasks_fullscreen(
    snapshot: TaskSnapshot,
    component_id: str,
    feedback: dict[str, str] | None = None,
) -> html.Div:
    people_options = [
        {"label": person.name, "value": person.id}
        for person in sorted(snapshot.people, key=lambda item: item.name.casefold())
    ]
    groups = grouped_open_tasks(snapshot)

    return html.Div(
        [
            _feedback_banner(feedback),
            _add_person_section(component_id),
            _add_task_section(component_id, people_options),
            _task_list_section(groups, component_id),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": SPACE["xl"],
            "padding": SPACE["xl"],
        },
    )


def _feedback_banner(feedback: dict[str, str] | None) -> html.Div | None:
    if not feedback or not feedback.get("message"):
        return None

    tone = feedback.get("tone", "success")
    border_color = COLORS["urgent"] if tone == "error" else COLORS["accent"]
    text_color = COLORS["urgent"] if tone == "error" else COLORS["text"]
    return html.Div(
        feedback["message"],
        style=panel_style(
            padding=SPACE["lg"],
            border=f"1px solid {border_color}",
            color=text_color,
            fontSize=FONT_SIZES["meta"],
        ),
    )


def _add_person_section(component_id: str) -> html.Div:
    return html.Div(
        [
            html.Div("People", style=kicker_style()),
            html.Div(
                [
                    dcc.Input(
                        id=f"{component_id}-person-name",
                        type="text",
                        placeholder="Add a person",
                        style=_INPUT_STYLE,
                    ),
                    dmc.Button(
                        "Add person",
                        id=f"{component_id}-add-person",
                        color="teal",
                        variant="light",
                    ),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr auto", "gap": SPACE["md"]},
            ),
        ],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["md"]},
    )


def _add_task_section(component_id: str, people_options: list[dict[str, str]]) -> html.Div:
    form_children = [
        dcc.Input(
            id=f"{component_id}-task-title",
            type="text",
            placeholder="Task title",
            style=_INPUT_STYLE,
        ),
    ]

    if not people_options:
        form_children.append(
            html.Div(
                "Add a person first, then assign them tasks.",
                style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["meta"]},
            ),
        )
    else:
        form_children.extend(
            [
                html.Div(
                    [
                        dcc.Dropdown(
                            id=f"{component_id}-task-person",
                            options=people_options,
                            placeholder="Assign to",
                            clearable=False,
                            style=_DROPDOWN_STYLE,
                        ),
                        dcc.Input(
                            id=f"{component_id}-task-due-on",
                            type="date",
                            value=local_today().isoformat(),
                            style=_INPUT_STYLE,
                        ),
                        dcc.Dropdown(
                            id=f"{component_id}-task-recurrence",
                            options=[
                                {"label": recurrence_label(value), "value": value.value}
                                for value in TaskRecurrence
                            ],
                            value=TaskRecurrence.ONCE.value,
                            clearable=False,
                            style=_DROPDOWN_STYLE,
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
                    style={"alignSelf": "flex-start"},
                ),
            ],
        )

    return html.Div(
        [html.Div("Tasks", style=kicker_style()), *form_children],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["md"]},
    )


def _task_list_section(groups: list[TaskGroup], component_id: str) -> html.Div:
    has_tasks = any(group.tasks for group in groups)
    body = (
        [
            html.Div(
                "No open tasks yet.",
                style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["meta"]},
            ),
        ]
        if not has_tasks
        else [_task_group(group, component_id) for group in groups]
    )

    return html.Div(
        [html.Div("Open tasks", style=kicker_style()), *body],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["lg"]},
    )


def _task_group(group: TaskGroup, component_id: str) -> html.Div:
    header = group.person.name
    if group.overdue_count:
        header = f"{header} · {group.overdue_count} overdue"

    return html.Div(
        [
            html.Div(
                header,
                style={
                    **kicker_style(color=COLORS["text_secondary"]),
                    "display": "block",
                },
            ),
            html.Div(
                [
                    _task_row(task, component_id, index == len(group.tasks) - 1)
                    for index, task in enumerate(group.tasks)
                ]
                or [
                    html.Div(
                        "No open tasks.",
                        style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["meta"]},
                    ),
                ],
                style=panel_style(padding=f"0 {SPACE['lg']}"),
            ),
        ],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["sm"]},
    )


def _task_row(task, component_id: str, is_last: bool) -> html.Div:
    overdue = task.due_on < local_today()
    recurrence_text = recurrence_label(task.recurrence)
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
                            "color": COLORS["urgent"] if overdue else COLORS["text_secondary"],
                            "marginTop": SPACE["xs"],
                        },
                    ),
                ],
                style={"minWidth": 0, "flex": 1},
            ),
            html.Button(
                "Done",
                id={"type": f"{component_id}-complete-task", "task_id": task.id},
                n_clicks=0,
                style={
                    "background": "transparent",
                    "border": f"1px solid {COLORS['hairline_strong']}",
                    "borderRadius": "999px",
                    "color": COLORS["text"],
                    "padding": "0.45rem 0.9rem",
                    "cursor": "pointer",
                    "fontSize": FONT_SIZES["small"],
                },
            ),
        ],
        style=row_style(
            divider=not is_last,
            accent=overdue,
            display="flex",
            alignItems="center",
            justifyContent="space-between",
            gap=SPACE["lg"],
        ),
    )
