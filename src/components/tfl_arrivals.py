from dataclasses import dataclass

import httpx
from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent


@dataclass
class StopPoint:
    """Dataclass representing a TFL StopPoint."""

    id: str
    name: str
    filter: dict | None = None  # Applied to arrivals data


class TFL(BaseComponent):
    """TFL component for the Magic Mirror application.
    Displays the next train times for a given station.


    StopPoints can be found using:
    https://api.tfl.gov.uk/StopPoint/Search/<search_term>
    E.g. https://api.tfl.gov.uk/StopPoint/Search/Waterloo
    """

    API_URL = "https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"

    def __init__(
        self,
        stops: list[StopPoint],
        top: float | None = None,
        v_middle: float | None = None,
        bottom: float | None = None,
        left: float | None = None,
        h_middle: float | None = None,
        right: float | None = None,
        width: float = 0.25,
        height: float = 0.4,
        *,
        justify_right: bool = False,
    ):
        super().__init__(
            name="tfl",
            top=top,
            v_middle=v_middle,
            bottom=bottom,
            left=left,
            h_middle=h_middle,
            right=right,
            width=width,
            height=height,
        )
        self.stops = stops
        self.justify_right = justify_right

    def layout(self):
        """Returns the layout of the TFL component."""
        return html.Div(
            [
                # Real-time countdown update (every second)
                dcc.Interval(
                    id=f"{self.component_id}-interval-countdown",
                    interval=1_000,  # Update every second for real-time countdown
                ),
                dcc.Store(
                    id=f"{self.component_id}-store",
                    data=None,  # Store the fetched data
                ),
                # Interval for fetching new data
                dcc.Interval(
                    id=f"{self.component_id}-interval-fetch",
                    interval=90_000,  # Fetch new data every minute
                ),
                # DashSocketIO(
                #     id=f"{self.component_id}-socketio",
                # ),
                html.Div(
                    id=f"{self.component_id}-arrivals",
                    style={"display": "flex", "flexDirection": "column"},
                ),
            ],
            style={"color": "#FFFFFF"},
        )

    def fetch(self) -> dict:
        """Fetch the latest TFL data and update the component."""
        data = {}
        for stop in self.stops:
            data[stop.name] = []
            try:
                response = httpx.get(self.API_URL.format(stop_id=stop.id))
            except httpx.RequestError as e:
                logger.error(f"Error fetching data for stop {stop.name}: {e}")
                continue
            if response.is_success:
                arrivals = response.json()
                if arrivals:
                    # Sort the arrivals by expected arrival time
                    arrivals.sort(key=lambda x: x.get("expectedArrival", ""))
                    # Assume the first arrival is soonest
                    data[stop.name] = arrivals[:5]  # Limit to 5 arrivals
            else:
                logger.error(
                    f"Failed to fetch data for stop {stop.name}: {response.status_code} - {response.text}",
                )
        logger.info(f"Fetched data for {len(data)} stops.")
        logger.debug(f"Data: {data}")
        return data

    def add_callbacks(self, app):
        @app.callback(
            Output(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
        )
        def fetch_data(n_intervals):
            """Fetches the latest TFL data and stores it in the dcc.Store."""
            return self.fetch()

        app.clientside_callback(
            f"""
            function(data, n_intervals) {{
                if (!data) {{
                    console.warn('No data available');
                    return window.dash_clientside.no_update;
                }}
                
                const container = document.getElementById('{self.component_id}-arrivals');
                if (!container) {{
                    return window.dash_clientside.no_update;
                }}
                
                // Clear existing content
                container.innerHTML = '';
                
                const now = new Date();
                
                for (const [stopName, arrivals] of Object.entries(data)) {{
                    if (!Array.isArray(arrivals) || arrivals.length === 0) {{
                        continue;
                    }}
                    
                    // Create stop header
                    const stopHeader = document.createElement('div');
                    stopHeader.style.marginBottom = '25px';
                    
                    const stopTitle = document.createElement('h3');
                    stopTitle.textContent = stopName;
                    stopTitle.style.cssText = `
                        color: #FFFFFF;
                        fontSize: 1.8rem;
                        fontWeight: 300;
                        margin: 0 0 8px 0;
                        letterSpacing: 0.5px;
                        textAlign: center;
                        justifyContent: ${{self.justify_right ? 'flex-end' : 'center'}};
                        display: flex;
                    `;
                    
                    const hr = document.createElement('hr');
                    hr.style.cssText = `
                        border: none;
                        height: 1px;
                        background: linear-gradient(90deg, transparent, #4A90E2, transparent);
                        margin: 0 0 20px 0;
                        width: 80%;
                        marginLeft: auto;
                        marginRight: auto;
                    `;
                    
                    stopHeader.appendChild(stopTitle);
                    stopHeader.appendChild(hr);
                    container.appendChild(stopHeader);
                    
                    // Process arrivals
                    const maxArrivals = Math.min(arrivals.length, 5);
                    for (let i = 0; i < maxArrivals; i++) {{
                        const arrival = arrivals[i];
                        const expectedArrival = new Date(arrival.expectedArrival);
                        const timeDiff = Math.max(
                            Math.round((expectedArrival - now) / 1000),
                            0
                        );
                        const minutes = Math.floor(timeDiff / 60);
                        const seconds = timeDiff % 60;
                        
                        // Calculate opacity
                        const baseOpacity = 1 - (i * 0.15);
                        const timeOpacity = Math.max(0.3, Math.min(1, (30 * 60 - timeDiff) / (25 * 60)));
                        const finalOpacity = Math.max(0.2, baseOpacity * timeOpacity);
                        
                        // Time urgency styling
                        let timeColor = '#FFFFFF';
                        let timeWeight = '300';
                        if (minutes <= 2) {{
                            timeColor = '#FF6B6B';
                            timeWeight = '500';
                        }} else if (minutes <= 5) {{
                            timeColor = '#FFD93D';
                            timeWeight = '400';
                        }} else if (minutes <= 10) {{
                            timeColor = '#6BCF7F';
                        }}
                        
                        // Create arrival card
                        const arrivalCard = document.createElement('div');
                        arrivalCard.style.cssText = `
                            opacity: ${{finalOpacity}};
                            padding: 12px 20px;
                            marginBottom: 8px;
                            background: rgba(255, 255, 255, 0.05);
                            borderRadius: 8px;
                            border: 1px solid rgba(74, 144, 226, 0.2);
                            backdropFilter: blur(10px);
                            transition: all 0.3s ease;
                            minWidth: 400px;
                            maxWidth: 600px;
                            display: flex;
                            alignItems: center;
                            justifyContent: space-between;
                        `;
                        
                        // Store arrival time as data attribute for real-time updates
                        arrivalCard.setAttribute('data-arrival-time', arrival.expectedArrival);
                        arrivalCard.classList.add('{self.component_id}-arrival-card');
                        
                        // Line name
                        const lineSpan = document.createElement('span');
                        lineSpan.textContent = arrival.lineName || 'Unknown';
                        lineSpan.style.cssText = `
                            color: #4A90E2;
                            fontWeight: 500;
                            fontSize: 1.1rem;
                            marginRight: 12px;
                            minWidth: 60px;
                            display: inline-block;
                        `;
                        
                        // Destination
                        const destSpan = document.createElement('span');
                        destSpan.textContent = arrival.destinationName || 'Unknown Destination';
                        destSpan.style.cssText = `
                            color: #FFFFFF;
                            fontSize: 1rem;
                            fontWeight: 300;
                            flex: 1;
                            marginRight: 16px;
                        `;
                        
                        // Time (with class for easy updating)
                        const timeSpan = document.createElement('span');
                        timeSpan.textContent = minutes > 0 ? `${{minutes}}m ${{seconds}}s` : `${{seconds}}s`;
                        timeSpan.classList.add('arrival-time');
                        timeSpan.style.cssText = `
                            color: ${{timeColor}};
                            fontSize: 1rem;
                            fontWeight: ${{timeWeight}};
                            minWidth: 70px;
                            textAlign: right;
                        `;
                        
                        arrivalCard.appendChild(lineSpan);
                        arrivalCard.appendChild(destSpan);
                        arrivalCard.appendChild(timeSpan);
                        container.appendChild(arrivalCard);
                    }}
                    
                    // Add spacing between stops
                    if (Object.keys(data).indexOf(stopName) < Object.keys(data).length - 1) {{
                        const spacer = document.createElement('div');
                        spacer.style.height = '40px';
                        container.appendChild(spacer);
                    }}
                }}
                
                return window.dash_clientside.no_update;
            }}
            """,
            Output(f"{self.component_id}-arrivals", "children"),
            Input(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
            prevent_initial_call=True,
        )

        # Lightweight real-time countdown updater
        app.clientside_callback(
            f"""
            function(n_intervals) {{
                const cards = document.querySelectorAll('.{self.component_id}-arrival-card');
                if (!cards.length) {{
                    return window.dash_clientside.no_update;
                }}
                
                const now = new Date();
                
                cards.forEach(card => {{
                    const arrivalTimeStr = card.getAttribute('data-arrival-time');
                    if (!arrivalTimeStr) return;
                    
                    const arrivalTime = new Date(arrivalTimeStr);
                    const timeDiff = Math.max(
                        Math.round((arrivalTime - now) / 1000),
                        0
                    );
                    
                    const minutes = Math.floor(timeDiff / 60);
                    const seconds = timeDiff % 60;
                    
                    // Update time display
                    const timeSpan = card.querySelector('.arrival-time');
                    if (timeSpan) {{
                        timeSpan.textContent = minutes > 0 ? `${{minutes}}m ${{seconds}}s` : `${{seconds}}s`;
                        
                        // Update color based on urgency
                        let timeColor = '#FFFFFF';
                        let timeWeight = '300';
                        if (minutes <= 2) {{
                            timeColor = '#FF6B6B';
                            timeWeight = '500';
                        }} else if (minutes <= 5) {{
                            timeColor = '#FFD93D';
                            timeWeight = '400';
                        }} else if (minutes <= 10) {{
                            timeColor = '#6BCF7F';
                        }}
                        
                        timeSpan.style.color = timeColor;
                        timeSpan.style.fontWeight = timeWeight;
                    }}
                    
                    // Hide arrivals that have passed (negative time)
                    if (timeDiff <= 0) {{
                        card.style.opacity = '0.1';
                        card.style.filter = 'grayscale(100%)';
                    }}
                }});
                
                return window.dash_clientside.no_update;
            }}
            """,
            Output(f"{self.component_id}-arrivals", "style"),
            Input(f"{self.component_id}-interval-countdown", "n_intervals"),
            prevent_initial_call=True,
        )
