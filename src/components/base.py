from abc import ABC, abstractmethod
from pathlib import Path

from dash import Dash, Input, Output, State, dcc, html, no_update
from dash.development.base_component import Component

from utils.data_repository import ComponentPayload, get_repository
from utils.styles import COLORS, SPACE, TEXT_STYLES, merge_styles

_COMPONENT_COUNT = 0


class PreloadedFullScreenMixin:
    """Mixin providing preloaded full-screen store IDs and a helper to build them."""

    def fullscreen_title_store_id(self) -> str:
        return f"{self.component_id}-fullscreen-title-store"

    def fullscreen_content_store_id(self) -> str:
        return f"{self.component_id}-fullscreen-content-store"

    def preload_fullscreen_stores(
        self,
        *,
        title: Component | None = None,
        content: Component | None = None,
    ) -> list[Component]:  # to embed in summary layout
        serialized_title = (
            title.to_plotly_json() if isinstance(title, Component) else title
        )
        serialized_content = (
            content.to_plotly_json() if isinstance(content, Component) else content
        )

        return [
            dcc.Store(id=self.fullscreen_title_store_id(), data=serialized_title),
            dcc.Store(id=self.fullscreen_content_store_id(), data=serialized_content),
        ]


class BaseComponent(ABC):
    """Base class for all components in the Magic Mirror application.
    Provides a common interface for rendering and updating components.
    """

    def __init__(
        self,
        name: str,
        *,
        full_screen: bool = True,
        **kwargs,
    ):
        global _COMPONENT_COUNT
        self.name = name
        self._id = _COMPONENT_COUNT
        _COMPONENT_COUNT += 1
        self.full_screen = full_screen
        self.css_position = {**kwargs}

    @property
    def component_id(self) -> str:
        """Returns the unique ID for the component, used in Dash callbacks."""
        return f"{self.name}-{self._id}"

    @staticmethod
    def credentials_dir() -> Path:
        """Returns the directory where component credentials are stored."""
        dir = Path(__file__).parents[2] / "credentials"
        if not dir.exists():
            dir.mkdir(parents=True, exist_ok=True)
        return dir

    def summary_layout(self) -> Component:
        # `minHeight: 0` + `overflow: hidden` is what actually lets a flex
        # child shrink below its content's natural size instead of forcing
        # the whole page to grow past the viewport - without it, flexbox's
        # default min-height:auto means a tall component (e.g. a busy
        # calendar day) can push the page into scrolling. `css_position`
        # can still override either if a component genuinely needs to.
        return html.Div(
            id=self.component_id,
            children=self._summary_layout(),
            style=merge_styles(
                {"minHeight": 0, "overflow": "hidden"}, self.css_position,
            ),
            n_clicks=0,
        )

    @abstractmethod
    def _summary_layout(self) -> Component:
        """Returns the summary layout for the component."""
        ...

    def add_callbacks(self, app: Dash) -> None:
        """Register this component's callbacks, plus the shared full-screen-modal
        open/populate wiring every component with `full_screen=True` gets for free.
        """
        self._add_callbacks(app)

        if self.full_screen:
            # Open the modal on click.
            app.clientside_callback(
                """
                function(n_clicks, current_style) {
                    if (!n_clicks || n_clicks === 0) {
                        return window.dash_clientside.no_update;
                    }
                    return { ...current_style, display: "block" };
                }
                """,
                Output("full-screen-modal", "style", allow_duplicate=True),
                Input(self.component_id, "n_clicks"),
                State("full-screen-modal", "style"),
                prevent_initial_call=True,
            )

            # Populate the modal from this component's preloaded stores.
            app.clientside_callback(
                """
                function(n_clicks, titleStore, contentStore) {
                    if (!n_clicks || n_clicks === 0) {
                        return [window.dash_clientside.no_update, window.dash_clientside.no_update];
                    }
                    if (!titleStore || !contentStore) { return ["Loading...", "Loading..."]; }
                    return [titleStore, contentStore];
                }
                """,
                Output("full-screen-modal-title", "children", allow_duplicate=True),
                Output("full-screen-modal-content", "children", allow_duplicate=True),
                Input(self.component_id, "n_clicks"),
                State(f"{self.component_id}-fullscreen-title-store", "data"),
                State(f"{self.component_id}-fullscreen-content-store", "data"),
                prevent_initial_call=True,
            )

    @abstractmethod
    def _add_callbacks(self, app: Dash) -> None:
        """Adds callbacks to the component. This method should be implemented by subclasses
        to define how the component interacts with the Dash app.

        :param app: The Dash application instance.
        """
        ...


class DataDrivenComponent(PreloadedFullScreenMixin, BaseComponent, ABC):
    """Base for components backed by the shared `DataRepository`.

    Handles the boilerplate every fetch-driven component needs: registering
    a background refresher (with warm sync fetch at startup so the first
    render isn't empty), reading the latest cached payload, the loading /
    error placeholder, and the summary hydrate callback. Subclasses only
    need to implement `_build_payload()` - the async fetch-and-render step -
    and set `refresh_seconds`.

    This is also the seam a future standalone caching API would slot into:
    everything here talks to `DataRepository` by key, never to a specific
    HTTP client or scraper directly, so swapping the repository's backing
    implementation (in-process background loop -> remote HTTP fetch) would
    not require touching any component or render code.
    """

    refresh_seconds: float = 300
    jitter_seconds: float = 0
    placeholder_loading = "Loading..."
    placeholder_error = "Unavailable"

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self._repository = get_repository()
        self._data_key = self.name
        try:
            self._repository.register_component(
                self._data_key,
                refresh_coro=self._build_payload,
                interval_seconds=self.refresh_seconds,
                jitter_seconds=self.jitter_seconds,
            )
            self._initial_payload = self._repository.refresh_now_sync(self._data_key)
        except ValueError:
            # Already registered (e.g. hot reload) - reuse the existing snapshot.
            self._initial_payload = self._repository.get_payload_snapshot(
                self._data_key,
            )

    @abstractmethod
    async def _build_payload(self) -> ComponentPayload | None:
        """Fetch data and render it into a `ComponentPayload`."""
        ...

    def _build_placeholder(self, message: str) -> html.Div:
        return html.Div(
            message,
            style={
                **TEXT_STYLES["secondary"],
                "color": COLORS["text_muted"],
                "textAlign": "center",
                "padding": SPACE["lg"],
            },
        )

    def _latest_payload(self) -> ComponentPayload | None:
        return (
            self._repository.get_payload_snapshot(self._data_key)
            or self._initial_payload
        )

    def _content_style(self) -> dict:
        """Style for the hydrated content wrapper div. Override for per-component tweaks."""
        return {"width": "100%", "color": COLORS["text"]}

    def _summary_layout(self):
        payload = self._latest_payload()
        summary_children = (
            payload.summary
            if payload and payload.summary is not None
            else self._build_placeholder(self.placeholder_loading)
        )
        stores = self.preload_fullscreen_stores(
            title=payload.fullscreen_title if payload else None,
            content=payload.fullscreen_content if payload else None,
        )
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=int(self.refresh_seconds * 1000),
                    n_intervals=0,
                ),
                *stores,
                html.Div(
                    id=f"{self.component_id}-content",
                    children=summary_children,
                    className="mm-fade-in",
                    style=self._content_style(),
                ),
            ],
        )

    def _add_callbacks(self, app: Dash) -> None:
        repo = self._repository
        data_key = self._data_key

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval", "n_intervals"),
            prevent_initial_call=False,
        )
        async def hydrate(_n):
            payload = await repo.get_payload_async(data_key)
            if payload is not None:
                self._initial_payload = payload
            else:
                payload = self._latest_payload()

            if payload is None:
                return (
                    self._build_placeholder(self.placeholder_error),
                    no_update,
                    no_update,
                )

            return payload.summary, payload.fullscreen_title, payload.fullscreen_content
