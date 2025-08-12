import datetime

import httpx
from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.file_cache import cache_json


class TFL(BaseComponent):
    """TFL component for the Magic Mirror application.
    Displays the next train times for a given station.


    StopPoints can be found using:
    https://api.tfl.gov.uk/StopPoint/Search/<search_term>
    E.g. https://api.tfl.gov.uk/StopPoint/Search/Waterloo
    """

    API_URL = "https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"

    def __init__(self, stops, *args, justify_right=False, **kwargs):
        super().__init__(name="tfl", *args, **kwargs)
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
                html.Div(
                    id=f"{self.component_id}-arrivals",
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "center",
                    },
                ),
            ],
            style={"color": "#FFFFFF"},
        )

    @cache_json(valid_lifetime=datetime.timedelta(seconds=30))
    def fetch(self) -> dict:
        """Fetch the latest TFL data and update the component."""
        data = {}
        for stop in self.stops:
            data[stop] = []
            try:
                response = httpx.get(self.API_URL.format(stop_id=stop))
            except httpx.RequestError as e:
                logger.error(f"Error fetching data for stop {stop}: {e}")
                continue
            if response.is_success:
                arrivals = response.json()
                if arrivals:
                    # Sort the arrivals by expected arrival time
                    arrivals.sort(key=lambda x: x.get("expectedArrival", ""))
                    # Assume the first arrival is soonest
                    data[stop] = arrivals[:5]  # Limit to 5 arrivals
            else:
                logger.error(
                    f"Failed to fetch data for stop {stop}: {response.status_code} - {response.text}",
                )
        logger.info(f"Fetched data for {len(data)} stops.")
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
                    
                    // Create stop header using stationName from first arrival
                    const stopHeader = document.createElement('div');

                    const stopTitle = document.createElement('h3');
                    let stationName = stopName.replace(/ Rail Station$/, '');
                    if (arrivals.length > 0 && arrivals[0].stationName) {{
                        stationName = arrivals[0].stationName;
                    }}
                    stopTitle.textContent = stationName.replace(/ Rail Station/, '');
                    stopTitle.style.cssText = `
                        color: #FFFFFF;
                        width: 100%;
                        font-size: 1.8rem;
                        font-weight: 300;
                        margin: 0 0 8px 0;
                        letter-spacing: 0.5px;
                        text-align: center;
                        justifyContent: ${{self.justify_right ? 'flex-end' : 'center'}};
                    `;

                    const hr = document.createElement('hr');
                    hr.style.cssText = `
                        border: none;
                        height: 0.0625rem;
                        background: linear-gradient(90deg, transparent, #4A90E2, transparent);
                        margin: 0 0 5px 0;
                        width: 80%;
                        margin-left: auto;
                        margin-right: auto;
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
                        const baseOpacity = 1 - (i * 0.05);
                        const timeOpacity = Math.max(0.6, Math.min(1, (30 * 60 - timeDiff) / (25 * 60)));
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
                            display: flex;
                            align-items: center;
                        `;
                        
                        // Store arrival time as data attribute for real-time updates
                        arrivalCard.setAttribute('data-arrival-time', arrival.expectedArrival);
                        arrivalCard.classList.add('{self.component_id}-arrival-card');
                        
                        // Line name
                        const lineSpan = document.createElement('span');
                        lineSpan.textContent = arrival.lineName || 'Unknown';
                        lineSpan.style.cssText = `
                            color: #4A90E2;
                            font-weight: 500;
                            font-size: 1rem;
                            margin-right: 5px;
                            display: inline-block;
                        `;
                        
                        // Destination
                        const destSpan = document.createElement('span');
                        // Remove the suffix " Rail Station" if it exists
                        destSpan.textContent = (arrival.destinationName || 'Unknown Destination').replace(/ Rail Station$/, '');
                        destSpan.style.cssText = `
                            color: #FFFFFF;
                            font-size: 1rem;
                            font-weight: 300;
                            flex: 1;
                            margin-right: 5px;
                        `;
                        
                        // Time (with class for easy updating)
                        const timeSpan = document.createElement('span');
                        timeSpan.textContent = minutes > 0 ? `${{minutes}}m` : `${{seconds}}s`;
                        timeSpan.classList.add('arrival-time');
                        timeSpan.style.cssText = `
                            color: ${{timeColor}};
                            font-size: 1.4rem;
                            font-weight: ${{timeWeight}};
                            text-align: right;
                        `;
                        
                        arrivalCard.appendChild(lineSpan);
                        arrivalCard.appendChild(destSpan);
                        arrivalCard.appendChild(timeSpan);
                        container.appendChild(arrivalCard);
                    }}
                    
                    // Add spacing between stops
                    if (Object.keys(data).indexOf(stopName) < Object.keys(data).length - 1) {{
                        const spacer = document.createElement('div');
                        spacer.style.height = '1.5rem';
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
                        timeSpan.textContent = minutes > 0 ? `${{minutes}}m` : `${{seconds}}s`;
                        
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
                        card.style.opacity = '0.5';
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
