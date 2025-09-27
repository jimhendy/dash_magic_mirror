from dash import Input, Output, dcc, html, no_update
from loguru import logger

from components.base import BaseComponent, PreloadedFullScreenMixin
from utils.data_repository import ComponentPayload, get_repository

from .data import (
    async_fetch_weather_data,
    process_detailed_weather_data,
    process_weather_data,
)
from .full_screen import render_weather_fullscreen
from .summary import render_weather_summary


class Weather(PreloadedFullScreenMixin, BaseComponent):
    """Weather component for the Magic Mirror application.
    Displays current weather, chance of rain, and 3-day forecast for a given UK postcode.

    Uses WeatherAPI.com for weather data.
    Requires a free API key from https://www.weatherapi.com/signup.aspx
    """

    icon_size = "7rem"

    def __init__(self, postcode: str, api_key: str, **kwargs):
        # Disable preloaded_full_screen because Dash components cannot be placed inside dcc.Store
        super().__init__(name="weather", preloaded_full_screen=False, **kwargs)
        self.postcode = postcode.upper().replace(" ", "")
        self.api_key = api_key

        if not self.api_key:
            msg = "Please set the WEATHER_API_KEY environment variable with your WeatherAPI.com key."
            raise ValueError(msg)

        self._repository = get_repository()
        self._data_key = self.name
        self._refresh_seconds = 15 * 60
        try:
            self._repository.register_component(
                self._data_key,
                refresh_coro=self._build_payload,
                interval_seconds=self._refresh_seconds,
                jitter_seconds=60,
            )
            self._initial_payload = self._repository.refresh_now_sync(self._data_key)
        except ValueError:
            self._initial_payload = self._repository.get_payload_snapshot(
                self._data_key,
            )

    async def _build_payload(self) -> ComponentPayload | None:
        raw = await async_fetch_weather_data(self.api_key, self.postcode)
        if not raw:
            logger.warning("Weather API returned no data for %s", self.postcode)
            return ComponentPayload(
                summary=self._build_placeholder("Weather unavailable"),
            )

        try:
            summary_data = process_weather_data(raw, self.postcode)
            detailed_data = process_detailed_weather_data(raw, self.postcode)
            summary_children = render_weather_summary(
                summary_data,
                self.component_id,
                self.icon_size,
            )
            content = render_weather_fullscreen(detailed_data, self.component_id)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering weather payload")
            return ComponentPayload(
                summary=self._build_placeholder("Weather unavailable"),
            )

        title_text = summary_data.get("current", {}).get("condition", "Weather")
        title = html.Div(
            title_text,
            className="text-m",
            **{"data-component-name": self.name},
        )

        return ComponentPayload(
            summary=summary_children,
            fullscreen_title=title,
            fullscreen_content=content,
            raw={
                "summary": summary_data,
                "detailed": detailed_data,
            },
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
        """Returns the layout of the Weather component."""
        payload = self._latest_payload()
        summary_children = (
            payload.summary
            if payload and payload.summary is not None
            else self._build_placeholder("Loading weather...")
        )
        stores = self.preload_fullscreen_stores(
            title=payload.fullscreen_title if payload else None,
            content=payload.fullscreen_content if payload else None,
        )
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=self._refresh_seconds * 1000,
                    n_intervals=0,
                ),
                *stores,
                html.Div(
                    id=f"{self.component_id}-content",
                    children=summary_children,
                    style={
                        "color": "#FFFFFF",
                        "fontSize": "14px",
                        "textAlign": "center",
                    },
                ),
            ],
        )

    def _add_callbacks(self, app):
        """Add callbacks for the Weather component."""
        repo = self._repository
        data_key = self._data_key

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval", "n_intervals"),
            prevent_initial_call=False,
        )
        async def hydrate_weather(_n):
            payload = await repo.get_payload_async(data_key)
            if payload is not None:
                self._initial_payload = payload
            else:
                payload = self._latest_payload()

            if payload is None:
                placeholder = self._build_placeholder("Weather unavailable")
                return placeholder, no_update, no_update

            return (
                payload.summary,
                payload.fullscreen_title,
                payload.fullscreen_content,
            )
