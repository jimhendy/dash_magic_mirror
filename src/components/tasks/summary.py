from dash import html

from utils.styles import COLORS, FONT_SIZES, SPACE, WEIGHT, kicker_style, row_style

from .data import TaskSnapshot, summary_rows


def render_tasks_summary(snapshot: TaskSnapshot) -> html.Div:
    rows = summary_rows(snapshot)
    if not rows:
        return html.Div(
            [
                html.Div("Tasks", style=kicker_style()),
                html.Div(
                    "No people yet",
                    style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["meta"]},
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": SPACE["xs"]},
        )

    return html.Div(
        [
            html.Div("Tasks", style=kicker_style()),
            html.Div(
                [_summary_row(row, index == len(rows) - 1) for index, row in enumerate(rows)],
                style={"display": "flex", "flexDirection": "column"},
            ),
        ],
        style={"display": "flex", "flexDirection": "column", "gap": SPACE["xs"]},
    )


def _summary_row(row, is_last: bool) -> html.Div:
    if row.overdue_count:
        status = f"{row.overdue_count} overdue"
        color = COLORS["urgent"]
        weight = WEIGHT["bold"]
    elif row.open_count:
        status = "No overdue tasks"
        color = COLORS["text_secondary"]
        weight = WEIGHT["regular"]
    else:
        status = "No tasks"
        color = COLORS["text_muted"]
        weight = WEIGHT["regular"]

    return html.Div(
        [
            html.Span(
                row.person.name,
                style={"fontSize": FONT_SIZES["meta"], "color": COLORS["text"]},
            ),
            html.Span(
                status,
                style={"fontSize": FONT_SIZES["small"], "color": color, "fontWeight": weight},
            ),
        ],
        style=row_style(
            divider=not is_last,
            display="flex",
            justifyContent="space-between",
            alignItems="center",
            gap=SPACE["md"],
        ),
    )
