import dash_mantine_components as dmc
from dash import dcc, html
from dash.development.base_component import Component
from dash_iconify import DashIconify

from utils.styles import COLORS, SPACE, section_gap


def _full_screen_modal() -> Component:
    """Get the core modal overlay layout that all components can use.

    This should be included once in the main app layout and provides:
    - Full-screen modal overlay
    - Auto-countdown timer functionality
    - Navigation controls (back button)
    - Shared across all components

    Returns:
        html.Div: The core modal layout component

    """
    return html.Div(
        id="full-screen-modal",
        style={
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100vw",
            "height": "var(--vh, 100vh)",
            "margin": "0",
            "padding": "0",
            "background": COLORS["bg"],
            "zIndex": 9999,
            "display": "none",
        },
        children=[
            dcc.Loading(
                id="full-screen-modal-loading",
                children=[
                    html.Div(
                        id="full-screen-modal-nav-bar",
                        children=[
                            # Left group (Back)
                            html.Div(
                                [
                                    dmc.Button(
                                        "Back",
                                        id="full-screen-modal-back-btn",
                                        variant="outline",
                                        color=COLORS["accent"],
                                        n_clicks=0,
                                        style={"marginRight": SPACE["sm"]},
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "minWidth": "7.5rem",
                                },
                            ),
                            # Center title (flex grow)
                            html.Div(
                                id="full-screen-modal-title",
                                style={
                                    "flex": 1,
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "textAlign": "center",
                                    "padding": f"0 {SPACE['sm']}",
                                    "color": COLORS["text"],
                                },
                            ),
                            # Right group (timer + refresh)
                            html.Div(
                                [
                                    dmc.Text(
                                        id="full-screen-modal-timer",
                                        size="sm",
                                        style={
                                            "marginRight": SPACE["md"],
                                            "color": COLORS["text_muted"],
                                            "minWidth": "4.4rem",
                                            "textAlign": "right",
                                        },
                                    ),
                                    dmc.Button(
                                        DashIconify(icon="mdi:trash-can"),
                                        id="full-screen-modal-clear-cache-btn",
                                        variant="outline",
                                        color="yellow",
                                        size="sm",
                                        n_clicks=0,
                                        style={
                                            "borderColor": COLORS["hairline_strong"],
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "flex-end",
                                    "gap": SPACE["xs"],
                                    "minWidth": "10rem",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                            "height": "3.5rem",
                            "padding": f"0 {SPACE['lg']}",
                            "borderBottom": f"1px solid {COLORS['hairline_strong']}",
                            "background": "transparent",
                        },
                    ),
                    html.Div(
                        id="full-screen-modal-content",
                        children=[],
                        style={
                            "height": "calc(var(--vh, 100vh) - 3.5rem)",
                            "overflow": "auto",
                        },
                    ),
                ],
            ),
        ],
    )


def _one_second_timer() -> Component:
    """Get a one-second timer component.

    Returns:
        Component: The one-second timer component

    """
    return dcc.Interval(
        id="one-second-timer",
        interval=1_000,  # 1 second
    )


def _mouse_movement_tracker() -> Component:
    """Get a mouse movement tracker component.

    This invisible component tracks mouse movements to reset modal timers.

    Returns:
        Component: The mouse movement tracker component

    """
    return html.Div(
        id="mouse-movement-tracker",
        style={
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100vw",
            "height": "var(--vh, 100vh)",
            "pointerEvents": "none",  # Don't interfere with other interactions
            "zIndex": -1,  # Behind everything else
        },
    )


def _empty_plotly_graph() -> Component:
    """Get an empty Plotly graph component.
    This aids in preloading the plotly display code from CDN

    Returns:
        Component: The empty Plotly graph component

    """
    return html.Div(
        dcc.Graph(
            id="dummy-preload",
            figure={
                "data": [
                    {
                        "x": [0],
                        "y": [0],
                        "type": "scatter",
                        "mode": "markers",
                    },
                ],
            },
            style={"display": "none"},  # hidden from view
        ),
    )


def core_layout() -> Component:
    """Get the core layout component for the app.

    Returns:
        Component: The core layout component

    """
    return dmc.MantineProvider(
        html.Div(
            id="core-layout",
            children=[
                _empty_plotly_graph(),
                _full_screen_modal(),
                _one_second_timer(),
                _mouse_movement_tracker(),
                dcc.Store(
                    id="global-refresh-trigger",
                    data=0,
                ),  # Global refresh counter
                html.Div(
                    id="app-div",
                    children=None,
                    style={
                        "width": "100vw",
                        # Height is set in main.css (#app-div), not here -
                        # it needs a vh->dvh CSS fallback for older
                        # browsers, and an inline style would always beat
                        # that fallback and break it.
                        "background": COLORS["black"],
                        "display": "flex",
                        "flexDirection": "column",
                        # Auto-distribute any leftover vertical space as
                        # extra breathing room *between* sections, instead
                        # of leaving it stranded below the last one. `gap`
                        # is still a floor under that (never less than
                        # `section_gap()`, even if content nearly fills the
                        # screen). `overflow: hidden` + each component's
                        # own `minHeight: 0` (see components/base.py) is
                        # what guarantees this never scrolls even if
                        # content ever exceeds the viewport: components
                        # shrink to fit instead.
                        "justifyContent": "space-evenly",
                        "gap": section_gap(),
                        "padding": f"{SPACE['lg']} {SPACE['xl']}",
                        "overflow": "hidden",
                        "boxSizing": "border-box",
                    },
                ),
            ],
        ),
    )
