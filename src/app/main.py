import os

from dash import Dash

from app.config import COMPONENTS
from app.core_callbacks import add_callbacks
from app.core_layout import core_layout
from utils.data_repository import get_repository

# Get the path to the assets directory
assets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

app = Dash(__name__, suppress_callback_exceptions=True, assets_folder=assets_path)
app.title = "Magic Mirror"

# Load the Inter typeface used throughout the UI (utils.styles.FONT_FAMILY).
# `display=swap` avoids blocking first paint while the font downloads.
app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
            rel="stylesheet"
        >
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

repository = get_repository()
repository.ensure_started()

app.layout = core_layout()
add_callbacks()

# Register callbacks for all components
for component in COMPONENTS:
    component.add_callbacks(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, threaded=True)
