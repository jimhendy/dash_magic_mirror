import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from dash import Dash, Input, Output, State, html
from dash.development.base_component import Component


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
        **kwargs,
    ):
        self.name = name
        self._id = uuid.uuid4().hex
        self.separator = separator
        self.full_screen = full_screen

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

    def full_screen_layout(self) -> Component:
        msg = "Full screen layout not implemented"
        return html.Div(msg)

    def full_screen_title(self) -> str:
        """Returns the title for the full screen modal."""
        return self.name

    def add_callbacks(self, app: Dash) -> None:
        """Adds callbacks to the component. This method should be implemented by subclasses
        to define how the component interacts with the Dash app.

        :param app: The Dash application instance.
        """
        self._add_callbacks(app)

        if self.full_screen:

            @app.callback(
                Output("full-screen-modal", "style", allow_duplicate=True),
                Output("full-screen-modal-title", "children", allow_duplicate=True),
                Output("full-screen-modal-content", "children", allow_duplicate=True),
                Input(self.component_id, "n_clicks"),
                State("full-screen-modal", "style"),
                prevent_initial_call=True,
            )
            def open_full_screen_modal(n_clicks: int, current_style: dict[str, str]):
                return (
                    current_style | {"display": "block"},
                    self.full_screen_title(),
                    self.full_screen_layout(),
                )

    @abstractmethod
    def _add_callbacks(self, app: Dash) -> None:
        """Adds callbacks to the component. This method should be implemented by subclasses
        to define how the component interacts with the Dash app.

        :param app: The Dash application instance.
        """
        ...
