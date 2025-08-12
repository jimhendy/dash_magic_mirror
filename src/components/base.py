import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from dash import Dash
from dash.development.base_component import Component


class BaseComponent(ABC):
    """Base class for all components in the Magic Mirror application.
    Provides a common interface for rendering and updating components.
    """

    def __init__(
        self,
        name: str,
        v_center: bool = False,
        h_center: bool = False,
        **kwargs,
    ):
        self.name = name
        self._id = uuid.uuid4().hex

        self.css_position = {
            "position": "absolute",
            **kwargs,
        }

        transforms = []
        if v_center:
            self.css_position["top"] = "50%"
            transforms.append("translateY(-50%)")
        if h_center:
            self.css_position["left"] = "50%"
            transforms.append("translateX(-50%)")

        if transforms:
            self.css_position["transform"] = " ".join(transforms)

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

    @abstractmethod
    def layout(self) -> Component: ...

    @abstractmethod
    def add_callbacks(self, app: Dash) -> None:
        """Adds callbacks to the component. This method should be implemented by subclasses
        to define how the component interacts with the Dash app.

        :param app: The Dash application instance.
        """
        ...
