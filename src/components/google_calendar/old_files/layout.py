"""Layout utilities for Google Calendar component.

Provides layout helpers and component structure for the calendar component
without the core modal functionality (which is handled by the app core).
"""

from dash import dcc, html

from utils.styles import COLORS


class GoogleCalendarLayoutMixin:
    """Mixin class providing layout utilities for Google Calendar component.

    This mixin provides methods for creating the component's front-page layout
    and managing component-specific UI elements. The core modal functionality
    is handled by the app's core modal system.
    """

    def get_summary_layout(self) -> html.Div:
        """Get the summary (front page) layout for the calendar component.

        This creates the clickable summary view that users see on the main page.
        When clicked, it will trigger the core modal to open with detailed content.

        Returns:
            html.Div: The summary layout component

        """
        return html.Div(
            [
                # Component-specific state storage
                dcc.Store(id=f"{self.component_id}-view-mode", data="summary"),
                # Summary view content
                html.Div(
                    id=f"{self.component_id}-summary-view",
                    children=[
                        html.Div(
                            id=f"{self.component_id}-main-content",
                            style={
                                "display": "flex",
                                "flexDirection": "column",
                                "alignItems": "stretch",
                                "gap": "8px",
                                "width": "100%",
                                "color": COLORS["white"],
                                "fontFamily": "'Inter', 'Roboto', 'Segoe UI', 'Helvetica Neue', sans-serif",
                                "cursor": "pointer",
                            },
                        ),
                    ],
                ),
            ],
            style={
                "color": COLORS["white"],
                "fontFamily": "'Inter', 'Roboto', 'Segoe UI', 'Helvetica Neue', sans-serif",
            },
        )

    def get_modal_timeout_seconds(self) -> int:
        """Get the countdown time in seconds for the modal auto-close.

        Returns:
            int: Number of seconds before modal auto-closes

        """
        return 30  # Default 30 seconds, can be overridden by subclasses
