import os

from dash import Dash

from app.config import COMPONENTS
from app.core_layout import core_layout
from utils.data_repository import get_repository

# Get the path to the assets directory
assets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder=assets_path,
    # Wall-mounted touch display: lock the zoom level so a quick double tap
    # is never interpreted as a zoom gesture (and the browser never has to
    # wait to find out whether it was one).
    meta_tags=[
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover",
        },
        {"name": "theme-color", "content": "#0A0C10"},
        {"name": "mobile-web-app-capable", "content": "yes"},
    ],
)
app.title = "Home"

# Inter is the UI typeface (see assets/main.css). `display=swap` avoids
# blocking first paint while the font downloads.
app.index_string = """<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link
            href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
            rel="stylesheet"
        >
        {%css%}
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

# A function, not a component tree: re-evaluated on every page load.
app.layout = core_layout

for component in COMPONENTS:
    component.add_callbacks(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, threaded=True)
