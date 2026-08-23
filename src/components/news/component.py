"""News headlines component for the Magic Mirror application.

Sourced from an RSS feed (default: BBC News) - no API key required, so there
is nothing to rate-limit beyond the usual `cache_json` fetch cadence.
"""

from dash import Dash, Input, Output, dcc, html
from dash.development.base_component import Component

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload

from .constants import DEFAULT_RSS_URL, ITEM_LIMIT, ROTATE_INTERVAL_MS
from .data import async_fetch_news_items
from .full_screen import render_news_fullscreen
from .summary import render_news_summary


class News(DataDrivenComponent):
    """Rotating news headlines, sourced from an RSS feed."""

    refresh_seconds = 20 * 60
    jitter_seconds = 60
    placeholder_error = "News unavailable"
    placeholder_loading = "Loading news..."

    def __init__(
        self,
        rss_url: str = DEFAULT_RSS_URL,
        item_limit: int = ITEM_LIMIT,
        **kwargs,
    ):
        self.rss_url = rss_url
        self.item_limit = item_limit
        super().__init__(name="news", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        items = await async_fetch_news_items(self.rss_url, limit=self.item_limit)
        summary_children = render_news_summary(items, self.component_id)
        fullscreen_result = render_news_fullscreen(items, self.component_id)

        title = html.Div(
            "Headlines",
            className="text-m",
            **{"data-component-name": self.name},
        )
        return ComponentPayload(
            summary=summary_children,
            fullscreen_title=title,
            fullscreen_content=fullscreen_result.content,
            raw={"items": items},
        )

    def _summary_layout(self) -> Component:
        layout = super()._summary_layout()
        # Extra client-only interval that drives headline rotation - separate
        # from the fetch interval above, which controls how often we re-fetch.
        layout.children.append(
            dcc.Interval(
                id=f"{self.component_id}-rotate-interval",
                interval=ROTATE_INTERVAL_MS,
                n_intervals=0,
            ),
        )
        layout.children.append(
            html.Div(id=f"{self.component_id}-rotator", style={"display": "none"}),
        )
        return layout

    def _add_callbacks(self, app: Dash) -> None:
        super()._add_callbacks(app)

        # Client-side rotation through headlines - no server round-trip.
        app.clientside_callback(
            "function(n){\n"
            "  try {\n"
            f"    const wrapper = document.getElementById('{self.component_id}-headlines-wrapper');\n"
            "    if(!wrapper){return window.dash_clientside.no_update;}\n"
            "    const rows = wrapper.querySelectorAll('[data-headline-index]');\n"
            "    if(!rows.length){return window.dash_clientside.no_update;}\n"
            "    const idx = (n || 0) % rows.length;\n"
            "    rows.forEach((r, i) => { r.style.display = (i === idx) ? 'flex' : 'none'; });\n"
            "  } catch(e){ console.warn('news rotation failed', e); }\n"
            "  return '';\n"
            "}",
            Output(f"{self.component_id}-rotator", "title"),  # dummy no-op output
            Input(f"{self.component_id}-rotate-interval", "n_intervals"),
            prevent_initial_call=False,
        )
