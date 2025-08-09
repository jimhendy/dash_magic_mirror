import dash_mantine_components as dmc
from dash import Input, Output, dcc, html

from components.base import BaseComponent


class Clock(BaseComponent):
    """Clock component for the Magic Mirror application.
    Displays the current time and updates every second.
    """

    def __init__(
        self,
        top: float | None = None,
        v_middle: float | None = None,
        bottom: float | None = None,
        left: float | None = None,
        h_middle: float | None = None,
        right: float | None = None,
        width: float = 0.4,
        height: float = 0.2,
    ):
        super().__init__(
            name="clock",
            top=top,
            v_middle=v_middle,
            bottom=bottom,
            left=left,
            h_middle=h_middle,
            right=right,
            width=width,
            height=height,
        )

    def layout(self):
        """Returns the layout of the clock component."""
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=1_000,  # Update every second
                ),
                dmc.Text(  # Slightly dimmed date text above the time
                    id=f"{self.component_id}-date",
                    c="dimmed",  # Dimmed color for the date
                    style={"fontSize": "1.2rem"},  # Smaller font size for date
                ),
                html.Div(
                    [
                        html.Div(
                            id=f"{self.component_id}-hour-minute",
                            style={
                                "fontSize": "6rem",
                                "color": "#FFFFFF",
                                "fontWeight": "bold",
                                "lineHeight": "1",
                            },
                        ),
                        dmc.Text(
                            id=f"{self.component_id}-seconds",
                            c="#999999",  # Dimmed color for timezone
                            style={
                                "fontSize": "1.2rem",
                            },  # Smaller font size for seconds
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

    def add_callbacks(self, app):
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
            Input(f"{self.component_id}-interval", "n_intervals"),
        )
