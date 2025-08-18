import dash_mantine_components as dmc
from dash import Dash, html
from dash_iconify import DashIconify
import os

from app.config import COMPONENTS
from utils.styles import COMPACT_STYLES, COLORS

# Get the path to the assets directory
assets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')

app = Dash(__name__, suppress_callback_exceptions=True, assets_folder=assets_path)
app.title = "Magic Mirror"

def create_separator(icon: str = None, title: str = None):
    """Create a horizontal separator with optional icon and title."""
    if not icon and not title:
        return None
    
    return html.Div(
        [
            html.Div(
                style={
                    "border": "none",
                    "height": "1px",
                    "background": "linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)",
                    "flex": "1",
                }
            ),
            html.Div(
                [
                    *(
                        [DashIconify(
                            icon=icon,
                            style={
                                "fontSize": "1.2rem",
                                "color": COLORS["primary_blue"],
                                "marginRight": "8px" if title else "0",
                            }
                        )] if icon else []
                    ),
                    *(
                        [html.Span(
                            title,
                            style={
                                "color": COLORS["soft_gray"],
                                "fontSize": "0.9rem",
                                "fontWeight": "500",
                                "textTransform": "uppercase",
                                "letterSpacing": "1px",
                            }
                        )] if title else []
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "padding": "0 1rem",
                    "backgroundColor": COLORS["black"],
                }
            ),
            html.Div(
                style={
                    "border": "none",
                    "height": "1px",
                    "background": "line80ar-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)",
                    "flex": "1",
                }
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "margin": "1rem 0",
            "width": "100%",
        }
    )

# Build the layout with separators
layout_children = []
for i, comp in enumerate(COMPONENTS):
    # Add separator before each component (except the first)
    separator = []
    if i > 0 and (comp.separator):
        separator.append(
            # hR with fancy gradient black -> white -> black in cubic
            html.Div(
                "\u00A0",  # Non-breaking space to give the div content
                style={
                    "border": "none",
                    "height": "3px",
                    "background": "linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent)",
                }
            )
        )

    # Add the component
    layout_children.append(
        html.Div(
            [
                *separator,
                comp.layout(),
            ],
            style={
                "width": "100%",
                "marginBottom": "0.5rem",
                "overflow": "hidden",
                "display": "flex",
                "flexDirection": "column",
            } | comp.css_position
        )
    )

app.layout = dmc.MantineProvider(
    html.Div(
        id="magic-mirror-container",
        style={
            **COMPACT_STYLES["base_container"],
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "flex-start",
            "alignItems": "stretch",
            "padding": "1rem",
            "boxSizing": "border-box",
        },
        children=layout_children,
    ),
)

# Register callbacks for all components
for component in COMPONENTS:
    component.add_callbacks(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
