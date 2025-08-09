import uuid
from abc import ABC, abstractmethod

from dash import Dash
from dash.development.base_component import Component


class BaseComponent(ABC):
    """Base class for all components in the Magic Mirror application.
    Provides a common interface for rendering and updating components.
    """

    def __init__(
        self,
        name: str,
        top: float | None = None,
        v_middle: float | None = None,
        bottom: float | None = None,
        left: float | None = None,
        h_middle: float | None = None,
        right: float | None = None,
        width: float = 1.0,
        height: float = 1.0,
    ):
        """Initializes the component with flexible positioning and dimensions.

        :param name: The name of the component.
        :param top: Top position as fraction of screen height (0.0 to 1.0).
        :param v_middle: Vertical middle position as fraction of screen height (0.0 to 1.0).
        :param bottom: Bottom position as fraction of screen height (0.0 to 1.0).
        :param left: Left position as fraction of screen width (0.0 to 1.0).
        :param h_middle: Horizontal middle position as fraction of screen width (0.0 to 1.0).
        :param right: Right position as fraction of screen width (0.0 to 1.0).
        :param width: Width as fraction of screen width (0.0 to 1.0).
        :param height: Height as fraction of screen height (0.0 to 1.0).
        """
        self.name = name
        self.width = width
        self.height = height
        self._id = uuid.uuid4().hex

        # Calculate vertical position based on which attribute is provided
        vertical_attrs = [top, v_middle, bottom]
        provided_vertical = [attr for attr in vertical_attrs if attr is not None]

        if len(provided_vertical) > 1:
            raise ValueError(
                "Only one of 'top', 'v_middle', or 'bottom' can be specified",
            )
        if len(provided_vertical) == 0:
            self.top = 0.0  # Default to top edge at 0
        elif top is not None:
            self.top = top
        elif v_middle is not None:
            self.top = v_middle - (
                height / 2
            )  # Center the component at v_middle position
        elif bottom is not None:
            self.top = bottom - height  # Bottom edge at bottom position

        # Calculate horizontal position based on which attribute is provided
        horizontal_attrs = [left, h_middle, right]
        provided_horizontal = [attr for attr in horizontal_attrs if attr is not None]

        if len(provided_horizontal) > 1:
            raise ValueError(
                "Only one of 'left', 'h_middle', or 'right' can be specified",
            )
        if len(provided_horizontal) == 0:
            self.left = 0.0  # Default to left edge at 0
        elif left is not None:
            self.left = left
        elif h_middle is not None:
            self.left = h_middle - (
                width / 2
            )  # Center the component at h_middle position
        elif right is not None:
            self.left = right - width  # Right edge at right position

        # Ensure component doesn't go off screen
        self.top = max(0.0, min(1.0 - self.height, self.top))
        self.left = max(0.0, min(1.0 - self.width, self.left))

    @property
    def component_id(self) -> str:
        """Returns the unique ID for the component, used in Dash callbacks."""
        return f"{self.name}-{self._id}"

    @abstractmethod
    def layout(self) -> Component: ...

    @abstractmethod
    def add_callbacks(self, app: Dash) -> None:
        """Adds callbacks to the component. This method should be implemented by subclasses
        to define how the component interacts with the Dash app.

        :param app: The Dash application instance.
        """
        ...
