from dash import Input, Output, State, get_app, html
from dash.dependencies import Component

from app.config import COMPONENTS
from utils.constants import MODAL_CLOSE_PREFIX, MODAL_COUNTDOWN_START
from utils.data_repository import get_repository
from utils.file_cache import clear_component_cache


def _horizontal_separator() -> Component:
    """Create a horizontal separator with optional icon and title."""
    return html.Div(
        "\u00a0",  # Non-breaking space to give the div content
        style={
            "border": "none",
            "height": "3px",
            "background": "linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent)",
        },
    )


def add_callbacks() -> None:
    app = get_app()

    # Add global mouse movement tracking
    app.clientside_callback(
        r"""
        function() {
            // Set up mouse movement & activity tracking once
            if (!window.mouseTrackingInitialized) {
                const setNow = () => { window.lastActivityTs = Date.now(); };
                document.addEventListener('mousemove', () => { window.lastMouseMove = Date.now(); setNow(); });
                document.addEventListener('keydown', setNow);
                document.addEventListener('touchstart', setNow, {passive: true});
                document.addEventListener('click', setNow, {passive: true});
                // initialize timestamps
                window.lastMouseMove = Date.now();
                window.lastActivityTs = Date.now();
                window.mouseTrackingInitialized = true;
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("mouse-movement-tracker", "children"),
        Input("mouse-movement-tracker", "id"),
        prevent_initial_call=False,
    )

    # Main timer callback - handles countdown and mouse movement reset
    app.clientside_callback(
        rf"""
        function(interval, countdown_text, current_style) {{
            const prefix = '{MODAL_CLOSE_PREFIX}';
            const is_opened = current_style && current_style.display === "block";
            if (!is_opened) {{
                return [window.dash_clientside.no_update, window.dash_clientside.no_update];
            }}
            if (!countdown_text || countdown_text === prefix + '0') {{
                let new_style = {{ ...current_style, display: "none" }};
                return [new_style, null];
            }}
            const match = countdown_text.startsWith(prefix) ? countdown_text.slice(prefix.length) : '{MODAL_COUNTDOWN_START}';
            let current = parseInt(match) || {MODAL_COUNTDOWN_START};
            const lastMouseMove = window.lastMouseMove || 0;
            const now = Date.now();
            if (now - lastMouseMove < 2000 && current <= {MODAL_COUNTDOWN_START - 5}) {{
                return [window.dash_clientside.no_update, prefix + '{MODAL_COUNTDOWN_START}'];
            }}
            return [window.dash_clientside.no_update, prefix + Math.max(0, current - 1)];
        }}
        """,
        [
            Output("full-screen-modal", "style", allow_duplicate=True),
            Output("full-screen-modal-timer", "children", allow_duplicate=True),
        ],
        Input("one-second-timer", "n_intervals"),
        [
            State("full-screen-modal-timer", "children"),
            State("full-screen-modal", "style"),
        ],
        prevent_initial_call=True,
    )

    # Separate callback to handle modal opening and set initial timer
    app.clientside_callback(
        f"""
        function(style) {{
            const opened = style && style.display === "block";
            if (opened) {{
                return '{MODAL_CLOSE_PREFIX}{MODAL_COUNTDOWN_START}';
            }}
            return window.dash_clientside.no_update;
        }}
        """,
        Output("full-screen-modal-timer", "children", allow_duplicate=True),
        Input("full-screen-modal", "style"),
        prevent_initial_call=True,
    )

    app.clientside_callback(
        """
        function(n_clicks, current_style) {
            if (n_clicks) {
                return { ...current_style, display: "none" };
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("full-screen-modal", "style", allow_duplicate=True),
        Input("full-screen-modal-back-btn", "n_clicks"),
        State("full-screen-modal", "style"),
        prevent_initial_call=True,
    )

    # As soon as the full screen modal is closed, clear the content to a basic loading message
    app.clientside_callback(
        """
        function(style) {
            const closed = style && style.display === "none";
            if (closed) {
                return "Loading...";
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("full-screen-modal-content", "children", allow_duplicate=True),
        Input("full-screen-modal", "style"),
        prevent_initial_call=True,
    )

    # Handle cache clearing for the current component
    @app.callback(
        [
            Output("global-refresh-trigger", "data", allow_duplicate=True),
            Output("full-screen-modal", "style", allow_duplicate=True),
        ],
        Input("full-screen-modal-clear-cache-btn", "n_clicks"),
        State("full-screen-modal-title", "children"),
        State("global-refresh-trigger", "data"),
        State("full-screen-modal", "style"),
        prevent_initial_call=True,
    )
    def clear_component_cache_callback(
        n_clicks,
        current_title,
        current_refresh_count,
        current_modal_style,
    ):
        """Clear the cache for the current component, trigger global refresh, and close modal."""
        if n_clicks and current_title:
            component_name = None
            if isinstance(current_title, dict):
                props = current_title.get("props", {})
                component_name = props.get("data-component-name")
            if component_name:
                clear_component_cache(component_name)
                repo = get_repository()
                try:
                    repo.refresh_now_sync(component_name)
                except KeyError:
                    pass
                new_refresh_count = (current_refresh_count or 0) + 1
                closed_modal_style = {**(current_modal_style or {}), "display": "none"}
                return new_refresh_count, closed_modal_style
        return current_refresh_count, current_modal_style

    # Centralized app refresh callback - re-renders all components when cache is cleared
    @app.callback(
        Output("app-div", "children"),
        Input("global-refresh-trigger", "data"),
        prevent_initial_call=False,
    )
    def refresh_all_components(refresh_trigger):
        """Re-render all components when global refresh is triggered."""
        component_layouts = []
        for i, component in enumerate(COMPONENTS):
            if i and component.separator:
                component_layouts.append(_horizontal_separator())
            component_layouts.append(component.summary_layout())
        return component_layouts
