from dash import html
from dash.development.base_component import Component

from app.config import COMPONENTS
from utils.constants import PANEL_TIMEOUT_SECONDS


def core_layout() -> Component:
    """The whole page: the dashboard grid of tiles, plus every component's
    detail panel mounted (hidden) in one overlay container.

    Used as a layout *function* (see `app/main.py`), so every page load is
    rendered from the latest cached data rather than whatever was cached
    when the server started.
    """
    tiles = [component.tile_layout() for component in COMPONENTS]
    panels = [
        component.panel_layout() for component in COMPONENTS if component.full_screen
    ]
    return html.Div(
        [
            html.Main(tiles, id="dashboard", className="dashboard"),
            html.Div(
                panels,
                id="panels",
                className="panels",
                **{"data-timeout": str(PANEL_TIMEOUT_SECONDS)},
            ),
        ],
        id="app-root",
    )
