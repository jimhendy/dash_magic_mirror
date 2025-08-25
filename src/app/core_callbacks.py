from dash import Input, Output, State, get_app


def add_callbacks() -> None:
    app = get_app()

    # Add global mouse movement tracking
    app.clientside_callback(
        r"""
        function() {
            // Set up mouse movement tracking once
            if (!window.mouseTrackingInitialized) {
                document.addEventListener('mousemove', function() {
                    window.lastMouseMove = Date.now();
                });
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
        r"""
        function(interval, countdown_text, current_style) {
            console.log("Timer callback - Interval:", interval, "Countdown:", countdown_text, "Style:", current_style);
            
            const is_opened = current_style && current_style.display === "block";
            
            // If modal is not open, do nothing
            if (!is_opened) {
                return [window.dash_clientside.no_update, window.dash_clientside.no_update];
            }
            
            // Handle timer countdown
            if (!countdown_text || countdown_text === "Close in 0") {
                let new_style = { ...current_style, display: "none" };
                return [new_style, null];
            }
            
            const match = countdown_text.match(/Close in (\d+)/);
            const current = match ? parseInt(match[1]) : 30;
            
            // Check if mouse moved recently (within last 2 seconds) and reset timer
            const lastMouseMove = window.lastMouseMove || 0;
            const now = Date.now();
            if (now - lastMouseMove < 2000 && current <= 25) {
                // Reset to 30 if mouse moved and timer is below 25
                return [window.dash_clientside.no_update, "Close in 30"];
            }
            
            return [window.dash_clientside.no_update, "Close in " + Math.max(0, current - 1)];
        }
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
        """
        function(style) {
            const opened = style && style.display === "block";
            if (opened) {
                return "Close in 30";
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("full-screen-modal-timer", "children", allow_duplicate=True),
        Input("full-screen-modal", "style"),
        prevent_initial_call=True,
    )

    app.clientside_callback(
        """
        function(n_clicks, current_style) {
            return { ...current_style, display: "none" };
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
