import os

from dash import Dash

from app.config import COMPONENTS
from app.core_callbacks import add_callbacks
from app.core_layout import core_layout

# Get the path to the assets directory
assets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

app = Dash(__name__, suppress_callback_exceptions=True, assets_folder=assets_path)
app.title = "Magic Mirror"

app.layout = core_layout()
add_callbacks()

# Register callbacks for all components
for component in COMPONENTS:
    component.add_callbacks(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
