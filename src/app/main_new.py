import dash_mantine_components as dmc
from dash import Dash, html

from components.clock import Clock
from components.compliments_jokes import ComplimentsJokes
from components.tfl_arrivals import TFL

# Create component instances
components = [
    Clock(),
    TFL(),
    ComplimentsJokes(),
]

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
