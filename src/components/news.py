import datetime
import re
import xml.etree.ElementTree as ET

import httpx
from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.file_cache import cache_json

FEEDS = {
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "WSJ World News": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
}

CLICKBAIT_PATTERNS = [
    r"\bwhat happened\b",
    r"\byou won'?t believe\b",
    r"\bcould change\b",
    r"\bshocking\b",
    r"\bamazing\b",
    r"\bthis is why\b",
    r"\bnumber \d+\b",
]


def is_informative(title):
    if not title:
        return False
    title_clean = title.strip().lower()
    if len(title_clean.split()) < 4:
        return False
    for pattern in CLICKBAIT_PATTERNS:
        if re.search(pattern, title_clean):
            return False
    return True


def fetch_rss_feed(name, url, limit=10):
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        items = []
        for item in root.findall("./channel/item")[:limit]:  # take only top N
            title = item.findtext("title")
            description = item.findtext("description") or ""
            pub_date = item.findtext("pubDate")

            if is_informative(title):
                items.append(
                    {
                        "source": name,
                        "title": title.strip(),
                        "link": item.findtext("link"),
                        "description": description.strip(),
                        "pubDate": pub_date,
                    },
                )
        return items
    except Exception as e:
        logger.error(f"Error fetching RSS feed {name} from {url}: {e}")
        return []


def fetch_all_news(limit_per_feed=10):
    all_items = []
    for name, url in FEEDS.items():
        all_items.extend(fetch_rss_feed(name, url, limit=limit_per_feed))
    return all_items


class NewsFeed(BaseComponent):
    def __init__(self, *args, limit_per_feed=10, **kwargs):
        super().__init__(name="news", *args, **kwargs)
        self.limit_per_feed = limit_per_feed

    def layout(self):
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval-fetch",
                    interval=600_000,  # 10 minutes
                ),
                dcc.Interval(
                    id=f"{self.component_id}-interval-headline",
                    interval=60_000,  # 60 seconds
                ),
                dcc.Store(
                    id=f"{self.component_id}-store",
                    data=None,
                ),
                dcc.Store(
                    id=f"{self.component_id}-headline-idx",
                    data=0,
                ),
                html.Div(
                    id=f"{self.component_id}-news",
                    style={"display": "flex", "flexDirection": "column"},
                ),
            ],
            style={"color": "#FFFFFF"},
        )

    @cache_json(valid_lifetime=datetime.timedelta(hours=60))
    def fetch(self):
        try:
            return fetch_all_news(limit_per_feed=self.limit_per_feed)
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    def add_callbacks(self, app):
        @app.callback(
            Output(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
        )
        def fetch_data(n_intervals):
            return self.fetch()

        # Update the headline index every 60 seconds
        @app.callback(
            Output(f"{self.component_id}-headline-idx", "data"),
            Input(f"{self.component_id}-interval-headline", "n_intervals"),
            Input(f"{self.component_id}-store", "data"),
            prevent_initial_call=True,
        )
        def update_headline_idx(n_intervals, data):
            import random

            if not data or not isinstance(data, list) or len(data) == 0:
                return 0
            return random.randint(0, len(data) - 1)

        # Only show one headline at a time
        app.clientside_callback(
            f"""
            function(data, idx) {{
                const container = document.getElementById('{self.component_id}-news');
                if (!container) return window.dash_clientside.no_update;
                container.innerHTML = '';
                if (!data || !Array.isArray(data) || data.length === 0) {{
                    const empty = document.createElement('div');
                    empty.textContent = 'No news available.';
                    empty.style.textAlign = 'center';
                    empty.style.opacity = 0.7;
                    container.appendChild(empty);
                    return window.dash_clientside.no_update;
                }}
                let i = idx;
                if (typeof i !== 'number' || i < 0 || i >= data.length) i = 0;
                const item = data[i];
                const newsDiv = document.createElement('div');
                newsDiv.style.cssText = `
                    padding: 10px 16px;
                    margin-bottom: 8px;
                    background: rgba(255,255,255,0.07);
                    font-size: 1.1rem;
                    display: flex;
                    flex-direction: row;
                    text-align: center;
                    justify-content: center;
                    align-items: center;
                `;
                const title = document.createElement('span');
                title.textContent = item.title || 'No Title';
                title.style.color = '#4A90E2';
                title.style.fontWeight = '500';
                title.style.marginBottom = '4px';
                newsDiv.appendChild(title);
                /*
                if (item.description) {{
                    const desc = document.createElement('span');
                    desc.textContent = item.description;
                    desc.style.color = '#FFFFFF';
                    desc.style.opacity = 0.8;
                    desc.style.fontSize = '0.95rem';
                    newsDiv.appendChild(desc);
                }}
                */
                if (item.source) {{
                    const source = document.createElement('span');
                    source.textContent = item.source;
                    source.style.color = '#FFD93D';
                    source.style.fontSize = '0.9rem';
                    source.style.marginLeft = '12px';
                    newsDiv.appendChild(source);
                }}
                container.appendChild(newsDiv);
                return window.dash_clientside.no_update;
            }}
            """,
            Output(f"{self.component_id}-news", "children"),
            Input(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-headline-idx", "data"),
            prevent_initial_call=True,
        )
