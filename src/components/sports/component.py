from dash import Dash, Input, Output, html
from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload
from utils.styles import SPACE

from .data import async_process_sports_data
from .full_screen import render_sports_fullscreen
from .summary import render_sports_summary


class Sports(DataDrivenComponent):
    """Sports component for the Magic Mirror application.

    Displays upcoming sports fixtures for configured teams.

    Summary view: Shows next 3 fixtures within 7 days
    Full screen view: Shows all fixtures with detailed information including competition and channel

    Configuration is done in data.py SPORTS list.
    """

    jitter_seconds = 30
    placeholder_error = "Sports unavailable"
    placeholder_loading = "Loading sports..."

    def __init__(self, fetch_minutes: int = 360, **kwargs):
        self.refresh_seconds = max(int(fetch_minutes * 60), 60)
        super().__init__(name="sports", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        """Fetch, process, and render the sports payload."""
        data = await async_process_sports_data()
        try:
            summary_children = render_sports_summary(data, self.component_id)
            content = render_sports_fullscreen(data, self.component_id)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering sports payload")
            return ComponentPayload(
                summary=self._build_placeholder(self.placeholder_error),
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

    def _content_style(self) -> dict:
        return {
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "stretch",
            "gap": SPACE["sm"],
            "width": "100%",
        }

    def _add_callbacks(self, app: Dash) -> None:
        super()._add_callbacks(app)

        # Client-side filtering of fixture cards (hide/show) based on selected sport
        app.clientside_callback(
            "function(value){\n  try {\n    const wrapper = document.getElementById('"
            f"{self.component_id}-fixtures-wrapper"
            "');\n    if(!wrapper){return window.dash_clientside.no_update;}\n    const cards = wrapper.querySelectorAll('[data-sport]');\n    if(!cards.length){return window.dash_clientside.no_update;}\n    const sel = (value || 'all').toLowerCase();\n    cards.forEach(c=>{\n      const sport = (c.getAttribute('data-sport') || '').toLowerCase();\n      if(sel==='all' || sport===sel){\n        c.style.display = 'flex';\n      } else {\n        c.style.display = 'none';\n      }\n    });\n  } catch(e){ console.warn('sport filter failed', e); }\n  return '';\n}",
            Output(f"{self.component_id}-sport-filter", "title"),  # dummy no-op output
            Input(f"{self.component_id}-sport-filter", "value"),
            prevent_initial_call=False,
        )
