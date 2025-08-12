import dash_mantine_components as dmc
from dash import Dash, html

from app.config import COMPONENTS
from utils.styles import COMPACT_STYLES

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Magic Mirror"

app.layout = dmc.MantineProvider(
    html.Div(
        id="magic-mirror-container",
        style=COMPACT_STYLES["base_container"],
        children=[
            html.Div(
                comp.layout(),
                style={**comp.css_position, "overflow": "hidden"},
            )
            for comp in COMPONENTS
        ],
    ),
)

# Register callbacks for all components
for component in COMPONENTS:
    component.add_callbacks(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
