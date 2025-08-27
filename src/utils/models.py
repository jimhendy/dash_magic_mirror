from dataclasses import dataclass

from dash.development.base_component import Component


@dataclass
class FullScreenResult:
    content: Component
    title: str
