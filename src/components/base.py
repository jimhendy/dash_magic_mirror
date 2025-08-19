import datetime
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
        separator: bool = False,
        **kwargs,
    ):
        self.name = name
        self._id = uuid.uuid4().hex
        self.separator = separator

        self.css_position = {
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

    @staticmethod
    def _opacity_from_days_away(
        date_obj: datetime.datetime | datetime.date | None,
    ) -> float:
        if not date_obj:
            return 0.5

        now = datetime.datetime.now(tz=datetime.UTC)

        if isinstance(date_obj, datetime.date) and not isinstance(
            date_obj, datetime.datetime,
        ):
            now = now.date()
        elif not hasattr(date_obj, "tzinfo") or date_obj.tzinfo is None:
            date_obj = date_obj.replace(tzinfo=now.tzinfo)

        days_away = (date_obj - now).days

        if days_away <= 1:
            return 1
        if days_away < 3:
            return 0.9
        if days_away < 7:
            return 0.8
        if days_away < 14:
            return 0.6
        return 0.5
