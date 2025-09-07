import dash_mantine_components as dmc
from dash import dcc, html
from dash.development.base_component import Component
from dash_iconify import DashIconify

from utils.styles import COLORS


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
            "height": "100vh",
            "overflow": "hidden",
            "margin": "0",
            "padding": "0",
            "background": COLORS["black"],
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
                            html.Div(
                                children=[
                                    dmc.Button(
                                        "Back",
                                        id="full-screen-modal-back-btn",
                                        variant="outline",
                                        n_clicks=0,
                                        style={"marginRight": "10px"},
                                    ),
                                    dmc.Button(
                                        DashIconify(icon="mdi:trash-can"),
                                        id="full-screen-modal-clear-cache-btn",
                                        variant="outline",
                                        color="yellow",
                                        size="sm",
                                        n_clicks=0,
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                            html.Div(id="full-screen-modal-title"),
                            dmc.Text(id="full-screen-modal-timer", size="sm"),
                        ],
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "height": "50px",
                        },
                    ),
                    html.Div(
                        id="full-screen-modal-content",
                        children=[],
                        style={"height": "calc(100vh - 50px)"},
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
            "height": "100vh",
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
                        "height": "100vh",
                        "background": COLORS["black"],
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "space-between",
                    },
                ),
            ],
        ),
    )
