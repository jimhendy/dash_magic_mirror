import dash_mantine_components as dmc
from dash import Dash, html

from components.clock import Clock
from components.compliments_jokes import ComplimentsJokes
from components.tfl_arrivals import TFL

components = [
    Clock(),
    TFL(),
    ComplimentsJokes(),
]

# Create a mapping of position to components for easy lookup
components_by_position = {}
for comp in components:
    position_key = comp.position.value
    if position_key not in components_by_position:
        components_by_position[position_key] = []
    components_by_position[position_key].append(comp)

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Magic Mirror"


app.layout = dmc.MantineProvider(
    html.Div(
        id="magic-mirror-container",
        children=[
            # Create a 3x3 grid for positioning components
            html.Div(
                id="magic-mirror-grid",
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr 1fr",
                    "gridTemplateRows": "1fr 1fr 1fr",
                    "height": "100vh",
                    "width": "100vw",
                    "gap": "20px",
                    "padding": "20px",
                    "boxSizing": "border-box",
                },
                children=[
                    # Create containers for each position
                    html.Div(
                        id="top-left",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "top left",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("top_left", [])
                        ],
                        style={
                            "gridColumn": "1",
                            "gridRow": "1",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "flex-start",
                            "justifyContent": "flex-start",
                            "overflow": "hidden",
                        },
                    ),
                    html.Div(
                        id="top-center",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "top center",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("top_center", [])
                        ],
                        style={
                            "gridColumn": "2",
                            "gridRow": "1",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                            "justifyContent": "flex-start",
                            "overflow": "hidden",
                        },
                    ),
                    html.Div(
                        id="top-right",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "top right",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("top_right", [])
                        ],
                        style={
                            "gridColumn": "3",
                            "gridRow": "1",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "flex-end",
                            "justifyContent": "flex-start",
                            "overflow": "hidden",
                        },
                    ),
                    html.Div(
                        id="left-center",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "center left",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("left_center", [])
                        ],
                        style={
                            "gridColumn": "1",
                            "gridRow": "2",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "flex-start",
                            "justifyContent": "center",
                            "overflow": "hidden",
                        },
                    ),
                    html.Div(
                        id="center",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "center center",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("center", [])
                        ],
                        style={
                            "gridColumn": "2",
                            "gridRow": "2",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "overflow": "hidden",
                        },
                    ),
                    html.Div(
                        id="right-center",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "center right",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("right_center", [])
                        ],
                        style={
                            "gridColumn": "3",
                            "gridRow": "2",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "flex-end",
                            "justifyContent": "center",
                            "overflow": "hidden",
                        },
                    ),
                    html.Div(
                        id="bottom-left",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "bottom left",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("bottom_left", [])
                        ],
                        style={
                            "gridColumn": "1",
                            "gridRow": "3",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "flex-start",
                            "justifyContent": "flex-end",
                            "overflow": "hidden",
                        },
                    ),
                    html.Div(
                        id="bottom-center",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "bottom center",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("bottom_center", [])
                        ],
                        style={
                            "gridColumn": "2",
                            "gridRow": "3",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                            "justifyContent": "flex-end",
                            "overflow": "hidden",
                        },
                    ),
                    html.Div(
                        id="bottom-right",
                        className="grid-area",
                        children=[
                            html.Div(
                                comp.layout(),
                                style={
                                    "transform": f"scale({min(comp.width / 100, comp.height / 100, 1.0)})",
                                    "transformOrigin": "bottom right",
                                    "width": "100%",
                                    "height": "100%",
                                    "overflow": "visible",
                                },
                            )
                            for comp in components_by_position.get("bottom_right", [])
                        ],
                        style={
                            "gridColumn": "3",
                            "gridRow": "3",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "flex-end",
                            "justifyContent": "flex-end",
                            "overflow": "hidden",
                        },
                    ),
                ],
            ),
        ],
        style={
            "backgroundColor": "#000000",
            "color": "#FFFFFF",
            "fontFamily": "Arial, sans-serif",
            "height": "100vh",
            "width": "100vw",
            "overflow": "hidden",
        },
    ),
)

for component in components:
    component.add_callbacks(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
