from dash import Input, Output, html

from components.base import BaseComponent
from utils.styles import COLORS


class Clock(BaseComponent):
    """Clock component for the Magic Mirror application.
    Displays the current time and updates every second.
    """

    def __init__(self, **kwargs):
        super().__init__(name="clock", full_screen=True, **kwargs)

    def _summary_layout(self):
        """Returns the layout of the clock component."""
        return html.Div(
            [
                html.Div(  # Slightly dimmed date text above the time
                    id=f"{self.component_id}-date",
                    style={
                        "fontSize": "1.4rem",
                        "color": COLORS["soft_gray"],
                        "textAlign": "center",
                        "marginBottom": "0.5rem",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            id=f"{self.component_id}-hour-minute",
                            style={
                                "fontSize": "6rem",
                                "fontWeight": "350",
                                "color": COLORS["white"],
                                "lineHeight": "1",
                            },
                        ),
                        html.Div(
                            id=f"{self.component_id}-seconds",
                            style={
                                "fontSize": "1.2rem",
                                "color": COLORS["gray"],
                                "marginLeft": "0.5rem",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "top",
                    },
                ),
            ],
            style={
                "alignItems": "center",  # Center content vertically
                "display": "flex",  # Use flexbox for centering
                "flexDirection": "column",  # Stack items vertically
                "justifyContent": "center",  # Center content horizontally
            },
        )

    def _add_callbacks(self, app):
        app.clientside_callback(
            """
            function(n_intervals) {
                const now = new Date();
                const date = now.toLocaleDateString('en-UK', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });
                const hours = now.getHours().toString().padStart(2, '0');
                const minutes = now.getMinutes().toString().padStart(2, '0');
                const hourMinute = `${hours}:${minutes}`;
                const seconds = now.getSeconds().toString().padStart(2, '0');

                return [date, hourMinute, seconds];
            }
            """,
            Output(f"{self.component_id}-date", "children"),
            Output(f"{self.component_id}-hour-minute", "children"),
            Output(f"{self.component_id}-seconds", "children"),
            Input("one-second-timer", "n_intervals"),
        )
