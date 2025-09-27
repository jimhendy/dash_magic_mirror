from dash import Input, Output, dcc, html, no_update
from loguru import logger

from components.base import BaseComponent, PreloadedFullScreenMixin
from utils.data_repository import ComponentPayload, get_repository

from .data import async_process_sports_data
from .full_screen import render_sports_fullscreen
from .summary import render_sports_summary


class Sports(PreloadedFullScreenMixin, BaseComponent):
    """Sports component for the Magic Mirror application.

    Displays upcoming sports fixtures for configured teams.

    Summary view: Shows next 3 fixtures within 7 days
    Full screen view: Shows all fixtures with detailed information including competition and channel

    Configuration is done in data.py SPORTS list.
    """

    def __init__(self, fetch_minutes: int = 360, **kwargs):
        # Enable preloaded full screen path
        super().__init__(name="sports", preloaded_full_screen=True, **kwargs)
        self.fetch_minutes = fetch_minutes
        self._repository = get_repository()
        self._data_key = self.name
        self._refresh_seconds = max(int(self.fetch_minutes * 60), 60)
        try:
            self._repository.register_component(
                self._data_key,
                refresh_coro=self._build_payload,
                interval_seconds=self._refresh_seconds,
                jitter_seconds=30,
            )
            self._initial_payload = self._repository.refresh_now_sync(self._data_key)
        except ValueError:
            # Already registered (e.g., hot reload); reuse existing snapshot
            self._initial_payload = self._repository.get_payload_snapshot(
                self._data_key,
            )

    async def _build_payload(self) -> ComponentPayload | None:
        """Fetch, process, and render the sports payload."""
        data = await async_process_sports_data()
        try:
            summary_children = render_sports_summary(data, self.component_id)
            content = render_sports_fullscreen(data, self.component_id)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering sports payload")
            return ComponentPayload(
                summary=self._build_placeholder("Sports unavailable"),
            )

        title = html.Div(
            "Sports Fixtures",
            className="text-m",
            **{"data-component-name": self.name},
        )
        return ComponentPayload(
            summary=summary_children,
            fullscreen_title=title,
            fullscreen_content=content,
            raw=data,
        )

    def _build_placeholder(self, message: str) -> html.Div:
        return html.Div(
            message,
            style={
                "color": "#FF6B6B",
                "textAlign": "center",
                "padding": "1rem",
                "fontSize": "1.1rem",
            },
        )

    def _latest_payload(self) -> ComponentPayload | None:
        return (
            self._repository.get_payload_snapshot(self._data_key)
            or self._initial_payload
        )

    def _summary_layout(self):
        """Returns the layout of the Sports component."""
        payload = self._latest_payload()
        summary_children = (
            payload.summary
            if payload and payload.summary is not None
            else self._build_placeholder("Loading sports...")
        )
        stores = self.preload_fullscreen_stores(
            title=payload.fullscreen_title if payload else None,
            content=payload.fullscreen_content if payload else None,
        )
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval-fetch",
                    interval=self._refresh_seconds * 1000,
                    n_intervals=0,
                ),
                *stores,
                html.Div(
                    id=f"{self.component_id}-content",
                    children=summary_children,
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "stretch",
                        "gap": "8px",
                        "width": "100%",
                        "color": "#FFFFFF",
                    },
                ),
            ],
        )

    def _add_callbacks(self, app):
        """Add callbacks for the Sports component."""
        repo = self._repository
        data_key = self._data_key

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
            prevent_initial_call=False,
        )
        async def hydrate_sports(_n):
            payload = await repo.get_payload_async(data_key)
            if payload is not None:
                self._initial_payload = payload
            else:
                payload = self._latest_payload()

            if payload is None:
                placeholder = self._build_placeholder("Sports unavailable")
                return placeholder, no_update, no_update

            return (
                payload.summary,
                payload.fullscreen_title,
                payload.fullscreen_content,
            )

        # Client-side filtering of fixture cards (hide/show) based on selected sport
        app.clientside_callback(
            "function(value){\n  try {\n    const wrapper = document.getElementById('"
            f"{self.component_id}-fixtures-wrapper"
            "');\n    if(!wrapper){return window.dash_clientside.no_update;}\n    const cards = wrapper.querySelectorAll('[data-sport]');\n    if(!cards.length){return window.dash_clientside.no_update;}\n    const sel = (value || 'all').toLowerCase();\n    cards.forEach(c=>{\n      const sport = (c.getAttribute('data-sport') || '').toLowerCase();\n      if(sel==='all' || sport===sel){\n        c.style.display = 'block';\n      } else {\n        c.style.display = 'none';\n      }\n    });\n  } catch(e){ console.warn('sport filter failed', e); }\n  return '';\n}",
            Output(f"{self.component_id}-sport-filter", "title"),  # dummy no-op output
            Input(f"{self.component_id}-sport-filter", "value"),
            prevent_initial_call=False,
        )
