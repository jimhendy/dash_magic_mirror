"""Callback functions for Google Calendar component.

Contains all Dash callback registration and event handling logic,
now integrated with the core modal system for better separation of concerns.
"""

import datetime
from typing import Any

from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate

from utils.dates import (
    datetime_from_str,
    format_datetime,
    is_today,
    is_tomorrow,
)
from utils.styles import COLORS

from .utils import get_corrected_end_date, is_multi_day


class GoogleCalendarCallbacks:
    """Manages all Dash callbacks for the Google Calendar component.

    This class handles component-specific callbacks while integrating with
    the core modal system for shared modal functionality.
    """

    def __init__(self, component_id: str, fetch_function: callable):
        """Initialize callback manager.

        Args:
            component_id: Unique component identifier
            fetch_function: Function to fetch calendar events

        """
        self.component_id = component_id
        self.fetch_function = fetch_function

    def register_callbacks(self, app) -> None:
        """Register all component-specific callbacks with the Dash app.

        Args:
            app: Dash application instance

        """
        self._register_view_toggle_callback(app)
        self._register_summary_render_callback(app)
        self._register_detailed_render_callback(app)
        self._register_modal_content_callback(app)
        self._register_modal_close_callback(app)

    def _register_view_toggle_callback(self, app) -> None:
        """Register callback to handle clicks and toggle to detailed view via core modal."""

        @app.callback(
            [
                Output("full-screen-modal", "opened", allow_duplicate=True),
                Output(f"{self.component_id}-view-mode", "data"),
            ],
            [
                Input(f"{self.component_id}-main-content", "n_clicks"),
            ],
            [
                State("full-screen-modal", "opened"),
                State(f"{self.component_id}-view-mode", "data"),
            ],
            prevent_initial_call=True,
        )
        def handle_click_to_detailed_view(
            main_content_clicks: int | None,
            modal_opened: bool,
            current_view_mode: str,
        ) -> tuple[bool, str]:
            """Handle clicks on main content to open detailed view in core modal.

            Args:
                main_content_clicks: Number of clicks on main content
                modal_opened: Whether the modal is currently opened
                current_view_mode: Current view mode for this component

            Returns:
                Tuple of (modal_opened, new_view_mode)

            """
            if current_view_mode == "summary" and main_content_clicks:
                # Open modal for this component
                return True, "detailed"

            return modal_opened, current_view_mode

    def _register_summary_render_callback(self, app) -> None:
        """Register callback to render summary view content."""

        @app.callback(
            Output(f"{self.component_id}-main-content", "children"),
            [
                Input(f"{self.component_id}-store", "data"),
                Input(f"{self.component_id}-view-mode", "data"),
            ],
        )
        def render_summary_events(
            data: list[dict] | None,
            view_mode: str,
        ) -> list[Any]:
            """Render events for summary view (today/tomorrow only).

            Args:
                data: List of event dictionaries
                view_mode: Current view mode

            Returns:
                List of Dash components for summary view

            """
            if view_mode != "summary" or not data or len(data) == 0:
                if view_mode == "summary":
                    return [
                        html.Div(
                            "No upcoming events",
                            style={
                                "fontSize": "1.2rem",
                                "color": COLORS["soft_gray"],
                                "textAlign": "center",
                                "padding": "2rem",
                            },
                        ),
                    ]
                return []

            # Filter for today and tomorrow only
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            filtered_events = []

            for event in data:
                start_dict = event.get("start", {})
                is_all_day = "dateTime" not in start_dict
                start_datetime_str = start_dict.get("dateTime", start_dict.get("date"))
                start_datetime = datetime_from_str(
                    start_datetime_str,
                    is_all_day=is_all_day,
                )

                if start_datetime.date() in [today, tomorrow]:
                    filtered_events.append(event)

            if not filtered_events:
                return [
                    html.Div(
                        "No events today or tomorrow",
                        style={
                            "fontSize": "1.1rem",
                            "color": COLORS["soft_gray"],
                            "textAlign": "center",
                            "padding": "1rem",
                        },
                    ),
                    html.Div(
                        "Click to view full calendar",
                        style={
                            "fontSize": "0.9rem",
                            "color": COLORS["gray"],
                            "textAlign": "center",
                            "fontStyle": "italic",
                            "cursor": "pointer",
                        },
                    ),
                ]

            return self._render_event_cards(filtered_events, include_click_hint=True)

    def _register_detailed_render_callback(self, app) -> None:
        """Register callback to render detailed calendar in core modal."""

        @app.callback(
            Output("core-modal-body", "children", allow_duplicate=True),
            [
                Input("core-modal-state", "data"),
                Input(f"{self.component_id}-store", "data"),
            ],
            prevent_initial_call=True,
        )
        def render_detailed_calendar_in_modal(
            modal_state: dict,
            data: list[dict] | None,
        ) -> list[Any]:
            """Render detailed calendar view in the core modal when this component is active.

            Args:
                modal_state: Current state of the core modal
                data: List of event dictionaries

            Returns:
                List of Dash components for detailed view or empty list

            """
            # Only render if modal is active for this component
            if modal_state.get("active_component") != self.component_id or not data:
                raise PreventUpdate

            # Import here to avoid circular imports
            from .rendering import GoogleCalendarRenderer

            # Generate comprehensive calendar showing all relevant events
            today = datetime.date.today()
            current_month = today.month
            current_year = today.year

            renderer = GoogleCalendarRenderer(self.component_id)
            return [renderer.render_calendar_month(current_year, current_month, data)]

    def _render_event_cards(
        self,
        events: list[dict],
        include_click_hint: bool = False,
    ) -> list[html.Div]:
        """Render event cards for summary view.

        Args:
            events: List of event dictionaries
            include_click_hint: Whether to include click hint text

        Returns:
            List of event card components

        """
        # Calendar colors for different calendars
        calendar_colors = [
            COLORS["blue"],
            COLORS["orange"],
            COLORS["green"],
            COLORS["gold"],
            COLORS["soft_gray"],
            COLORS["gray"],
        ]

        # Build calendar ID order for consistent coloring
        calendar_id_order = []
        for event in events:
            calendar_id = event.get("calendarId", "")
            if calendar_id and calendar_id not in calendar_id_order:
                calendar_id_order.append(calendar_id)

        event_cards = []

        for event in events:
            start_dict = event.get("start", {})
            end_dict = event.get("end", {})
            summary = event.get("summary", "No Title")
            calendar_id = event.get("calendarId", "")

            is_all_day = "dateTime" not in start_dict
            is_birthday = "birthday" in summary.lower()

            start_datetime_str = start_dict.get("dateTime", start_dict.get("date"))
            start_datetime = datetime_from_str(
                start_datetime_str,
                is_all_day=is_all_day,
            )
            opacity = self._opacity_from_days_away(start_datetime)

            end_datetime_str = end_dict.get("dateTime", end_dict.get("date"))
            raw_end_datetime = datetime_from_str(
                end_datetime_str,
                is_all_day=is_all_day,
            )
            end_datetime = get_corrected_end_date(
                raw_end_datetime,
                is_all_day=is_all_day,
            )

            event_is_today = is_today(start_datetime)
            event_is_tomorrow = is_tomorrow(start_datetime)

            # Get calendar color
            color_idx = (
                calendar_id_order.index(calendar_id)
                if calendar_id in calendar_id_order
                else 0
            )
            dot_color = calendar_colors[color_idx % len(calendar_colors)]

            # Format date display
            date_text = format_datetime(start_datetime, is_all_day=is_all_day)

            # Add end date for multi-day events
            if is_multi_day(start_datetime, end_datetime):
                end_text = format_datetime(end_datetime, is_all_day=is_all_day)
                date_text += f" → {end_text}"

            # Card styling - clean and minimal with subtle gradient
            border_color = (
                COLORS["gold"]
                if event_is_today
                else (COLORS["gray"] if event_is_tomorrow else "rgba(255,255,255,0.08)")
            )
            card_style = {
                "border": f"1px solid {border_color}",
                "borderRadius": "8px",
                "padding": "12px 14px",
                "marginBottom": "0",
                "backdropFilter": "blur(10px)",
                "opacity": opacity,
                "cursor": "pointer" if include_click_hint else "default",
                "background": "linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
            }

            # Create event card content
            from dash_iconify import DashIconify

            event_card = html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                style={
                                    "width": "10px",
                                    "height": "10px",
                                    "borderRadius": "50%",
                                    "background": dot_color,
                                    "marginRight": "10px",
                                    "flexShrink": "0",
                                    "opacity": "0.8",
                                },
                                title=calendar_id,
                            ),
                            *(
                                [
                                    DashIconify(
                                        icon="mdi:cake-variant",
                                        style={
                                            "marginRight": "6px",
                                            "color": COLORS["orange"],
                                        },
                                    ),
                                ]
                                if is_birthday
                                else []
                            ),
                            html.Span(
                                summary,
                                style={
                                    "fontWeight": "bold" if event_is_today else "500",
                                    "fontSize": "1.1rem",
                                    "color": COLORS["white"],
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "whiteSpace": "nowrap",
                                    "flex": "1",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "overflow": "hidden",
                            "flex": "1",
                        },
                    ),
                    html.Div(
                        date_text,
                        style={
                            "color": COLORS["orange"],
                            "fontWeight": "500",
                            "fontSize": "1.1rem",
                            "marginLeft": "16px",
                            "whiteSpace": "nowrap",
                            "textAlign": "right",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "width": "100%",
                    "gap": "8px",
                },
            )

            event_cards.append(html.Div(event_card, style=card_style))

        if include_click_hint and event_cards:
            event_cards.append(
                html.Div(
                    "Click for full calendar view",
                    style={
                        "fontSize": "0.9rem",
                        "color": COLORS["gray"],
                        "textAlign": "center",
                        "fontStyle": "italic",
                        "marginTop": "8px",
                        "cursor": "pointer",
                    },
                ),
            )

        return event_cards

    def _register_modal_content_callback(self, app) -> None:
        """Register callback to populate modal content when in detailed view."""

        @app.callback(
            Output("full-screen-modal-content", "children"),
            [
                Input(f"{self.component_id}-view-mode", "data"),
                Input("full-screen-modal", "opened"),
            ],
            [
                State(f"{self.component_id}-store", "data"),
            ],
        )
        def update_modal_content(
            view_mode: str,
            modal_opened: bool,
            data: list[dict] | None,
        ) -> list[Any]:
            """Update the modal content when this component is in detailed view.

            Args:
                view_mode: Current view mode for this component
                modal_opened: Whether the modal is opened
                data: Calendar event data

            Returns:
                List of components for modal content

            """
            if not modal_opened or view_mode != "detailed":
                return []

            if not data:
                return [
                    html.Div(
                        "No calendar data available",
                        style={
                            "fontSize": "1.5rem",
                            "color": COLORS["soft_gray"],
                            "textAlign": "center",
                            "padding": "2rem",
                        },
                    ),
                ]

            # Use the renderer to create the detailed calendar view
            from .rendering import GoogleCalendarRenderer

            current_date = datetime.datetime.now()
            current_year = current_date.year
            current_month = current_date.month

            renderer = GoogleCalendarRenderer(self.component_id)
            return [renderer.render_calendar_month(current_year, current_month, data)]

    def _register_modal_close_callback(self, app) -> None:
        """Register callback to handle modal close and reset view mode."""

        @app.callback(
            [
                Output("full-screen-modal", "opened", allow_duplicate=True),
                Output(f"{self.component_id}-view-mode", "data", allow_duplicate=True),
            ],
            [
                Input("full-screen-modal-back-btn", "n_clicks"),
            ],
            [
                State("full-screen-modal", "opened"),
                State(f"{self.component_id}-view-mode", "data"),
            ],
            prevent_initial_call=True,
        )
        def handle_modal_close(
            back_clicks: int | None,
            modal_opened: bool,
            current_view_mode: str,
        ) -> tuple[bool, str]:
            """Handle back button clicks to close modal and reset view mode.

            Args:
                back_clicks: Number of clicks on back button
                modal_opened: Whether modal is currently opened
                current_view_mode: Current view mode

            Returns:
                Tuple of (modal_opened, view_mode)

            """
            if back_clicks and modal_opened and current_view_mode == "detailed":
                return False, "summary"

            return modal_opened, current_view_mode

        # Also reset view mode when modal is closed by other means (timeout)
        @app.callback(
            Output(f"{self.component_id}-view-mode", "data", allow_duplicate=True),
            [
                Input("full-screen-modal", "opened"),
            ],
            [
                State(f"{self.component_id}-view-mode", "data"),
            ],
            prevent_initial_call=True,
        )
        def reset_view_mode_on_modal_close(
            modal_opened: bool,
            current_view_mode: str,
        ) -> str:
            """Reset view mode to summary when modal is closed.

            Args:
                modal_opened: Whether modal is opened
                current_view_mode: Current view mode

            Returns:
                New view mode

            """
            if not modal_opened and current_view_mode == "detailed":
                return "summary"

            return current_view_mode

    def _opacity_from_days_away(self, date_obj: datetime.datetime) -> float:
        """Calculate opacity based on how far away the event is.

        Args:
            date_obj: Event datetime

        Returns:
            Opacity value between 0.6 and 1.0

        """
        days_away = (date_obj.date() - datetime.date.today()).days
        if days_away <= 1:
            return 1.0
        if days_away <= 7:
            return 0.8
        return 0.6
