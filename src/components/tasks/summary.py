from dash import html

from utils.styles import COLORS, FONT_SIZES, SPACE, WEIGHT, kicker_style, row_style

from .data import TaskDigestRow, TaskSnapshot, short_due_label, upcoming_task_rows

_SUMMARY_TASK_LIMIT = 5


def render_tasks_summary(snapshot: TaskSnapshot) -> html.Div:
    if not snapshot.people:
        return _wrapper([_note("No people yet")])

    rows, overflow = upcoming_task_rows(snapshot, limit=_SUMMARY_TASK_LIMIT)
    if not rows:
        return _wrapper([_note("All caught up")])

    children: list = [
        _task_row(row, is_last=index == len(rows) - 1 and overflow <= 0)
        for index, row in enumerate(rows)
    ]
    if overflow > 0:
        children.append(
            html.Div(
                f"+{overflow} more",
                style={
                    "fontSize": FONT_SIZES["small"],
                    "color": COLORS["text_muted"],
                    "paddingLeft": SPACE["md"],
                    "marginTop": SPACE["xs"],
                },
            ),
        )

    return _wrapper(
        [html.Div(children, style={"display": "flex", "flexDirection": "column"})],
    )


def _wrapper(children: list) -> html.Div:
    return html.Div(
        [html.Div("Tasks", style=kicker_style()), *children],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["xs"]},
    )


def _note(message: str) -> html.Div:
    return html.Div(
        message,
        style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["meta"]},
    )


_ELLIPSIS = {
    "overflow": "hidden",
    "textOverflow": "ellipsis",
    "whiteSpace": "nowrap",
}


def _task_row(row: TaskDigestRow, *, is_last: bool) -> html.Div:
    due_color = COLORS["urgent"] if row.overdue else COLORS["text_secondary"]
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        row.task.title,
                        style={
                            "fontSize": FONT_SIZES["meta"],
                            "color": COLORS["text"],
                            **_ELLIPSIS,
                        },
                    ),
                    html.Div(
                        row.person.name,
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["text_muted"],
                            **_ELLIPSIS,
                        },
                    ),
                ],
                style={"minWidth": 0, "flex": 1},
            ),
            html.Span(
                short_due_label(row.task),
                style={
                    "fontSize": FONT_SIZES["small"],
                    "color": due_color,
                    "fontWeight": WEIGHT["bold"] if row.overdue else WEIGHT["regular"],
                    "whiteSpace": "nowrap",
                },
            ),
        ],
        style=row_style(
            divider=not is_last,
            accent=row.overdue,
            display="flex",
            justifyContent="space-between",
            alignItems="baseline",
            gap=SPACE["md"],
        ),
    )
