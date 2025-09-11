from abc import ABC, abstractmethod
from pathlib import Path

from dash import Dash, Input, Output, State, html
from dash.development.base_component import Component

from utils.models import FullScreenResult

_COMPONENT_COUNT = 0


class PreloadedFullScreenMixin:
    """Mixin to provide preloaded full screen store IDs and helper layout fragments."""

    def fullscreen_title_store_id(self) -> str:
        return f"{self.component_id}-fullscreen-title-store"

    def fullscreen_content_store_id(self) -> str:
        return f"{self.component_id}-fullscreen-content-store"

    def preload_fullscreen_stores(
        self,
    ) -> list[Component]:  # to embed in summary layout
        from dash import dcc

        return [
            dcc.Store(id=self.fullscreen_title_store_id(), data=None),
            dcc.Store(id=self.fullscreen_content_store_id(), data=None),
        ]


class BaseComponent(ABC):
    """Base class for all components in the Magic Mirror application.
    Provides a common interface for rendering and updating components.
    """

    def __init__(
        self,
        name: str,
        *,
        separator: bool = False,
        full_screen: bool = True,
        preloaded_full_screen: bool = False,  # New flag
        **kwargs,
    ):
        global _COMPONENT_COUNT
        self.name = name
        self._id = _COMPONENT_COUNT
        _COMPONENT_COUNT += 1
        self.separator = separator
        self.full_screen = full_screen
        self.preloaded_full_screen = (
            preloaded_full_screen  # Track if using pre-populated stores
        )

        self.css_position = {
            **kwargs,
        }

    @property
    def component_id(self) -> str:
        """Returns the unique ID for the component, used in Dash callbacks."""
        return f"{self.name}-{self._id}"

    @staticmethod
    def credentials_dir() -> Path:
        """Returns the directory where component credentials are stored."""
        dir = Path(__file__).parents[2] / "credentials"
        if not dir.exists():
            dir.mkdir(parents=True, exist_ok=True)
        return dir

    def summary_layout(self) -> Component:
        return html.Div(
            id=self.component_id,
            children=self._summary_layout(),
            style=self.css_position,
            n_clicks=0,
        )

    @abstractmethod
    def _summary_layout(self) -> Component:
        """Returns the summary layout for the component."""
        ...

    def full_screen_content(
        self,
    ) -> FullScreenResult:  # kept for backward compatibility if needed
        msg = "Full screen content now provided via preloaded stores."
        return FullScreenResult(content=html.Div(msg), title=self.name)

    def add_callbacks(self, app: Dash) -> None:
        """Adds callbacks to the component. This method should be implemented by subclasses
        to define how the component interacts with the Dash app.

        :param app: The Dash application instance.
        """
        self._add_callbacks(app)

        if self.full_screen:
            # Modal open (style)
            app.clientside_callback(
                """
                function(n_clicks, current_style) {
                    if (!n_clicks || n_clicks === 0) {
                        return window.dash_clientside.no_update;
                    }
                    return { ...current_style, display: "block" };
                }
                """,
                Output("full-screen-modal", "style", allow_duplicate=True),
                Input(self.component_id, "n_clicks"),
                State("full-screen-modal", "style"),
                prevent_initial_call=True,
            )

            # Preloaded content path only (all components must preload)
            app.clientside_callback(
                """
                function(n_clicks, titleStore, contentStore) {
                    if (!n_clicks || n_clicks === 0) {
                        return [window.dash_clientside.no_update, window.dash_clientside.no_update];
                    }
                    if (!titleStore || !contentStore) { return ["Loading...", "Loading..."]; }
                    return [titleStore, contentStore];
                }
                """,
                Output("full-screen-modal-title", "children", allow_duplicate=True),
                Output("full-screen-modal-content", "children", allow_duplicate=True),
                Input(self.component_id, "n_clicks"),
                State(f"{self.component_id}-fullscreen-title-store", "data"),
                State(f"{self.component_id}-fullscreen-content-store", "data"),
                prevent_initial_call=True,
            )

    @abstractmethod
    def _add_callbacks(self, app: Dash) -> None:
        """Adds callbacks to the component. This method should be implemented by subclasses
        to define how the component interacts with the Dash app.

        :param app: The Dash application instance.
        """
        ...
