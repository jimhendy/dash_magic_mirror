import dash_mantine_components as dmc
from dash import Dash, html

from components.clock import Clock
from components.compliments_jokes import ComplimentsJokes
from components.tfl_arrivals import TFL, StopPoint
from app.config import TFLConfig, PositionConfig

# Create component instances with configuration from environment
components = [
    Clock(h_middle=0.5, top=PositionConfig.CLOCK_TOP, width=PositionConfig.CLOCK_WIDTH, height=PositionConfig.CLOCK_HEIGHT),
]

# Add left TFL component if stops are configured
if TFLConfig.LEFT_STOPS:
    left_stops = [StopPoint(id=stop["id"], name=stop["name"]) for stop in TFLConfig.LEFT_STOPS]
    components.append(
        TFL(
            stops=left_stops,
            left=PositionConfig.TFL_LEFT_LEFT,
            top=PositionConfig.TFL_LEFT_TOP,
            width=PositionConfig.TFL_LEFT_WIDTH,
            height=PositionConfig.TFL_LEFT_HEIGHT,
        )
    )

# Add right TFL component if stops are configured  
if TFLConfig.RIGHT_STOPS:
    right_stops = [StopPoint(id=stop["id"], name=stop["name"]) for stop in TFLConfig.RIGHT_STOPS]
    components.append(
        TFL(
            stops=right_stops,
            right=PositionConfig.TFL_RIGHT_RIGHT,
            top=PositionConfig.TFL_RIGHT_TOP,
            width=PositionConfig.TFL_RIGHT_WIDTH,
            height=PositionConfig.TFL_RIGHT_HEIGHT,
            justify_right=True,
        )
    )

# Add compliments component
components.append(
    ComplimentsJokes(h_middle=0.5, v_middle=0.5, width=PositionConfig.COMPLIMENTS_WIDTH, height=PositionConfig.COMPLIMENTS_HEIGHT)
)

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Magic Mirror"

app.layout = dmc.MantineProvider(
    html.Div(
        id="magic-mirror-container",
        style={
            "position": "relative",
            "width": "100vw",
            "height": "100vh",
            "backgroundColor": "#000000",
            "color": "#FFFFFF",
            "fontFamily": "Arial, sans-serif",
            "overflow": "hidden",
        },
        children=[
            html.Div(
                comp.layout(),
                style={
                    "position": "absolute",
                    "top": f"{comp.top * 100}%",
                    "left": f"{comp.left * 100}%",
                    "width": f"{comp.width * 100}%",
                    "height": f"{comp.height * 100}%",
                    "overflow": "hidden",
                },
            )
            for comp in components
        ],
    ),
)

# Register callbacks for all components
for component in components:
    component.add_callbacks(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
