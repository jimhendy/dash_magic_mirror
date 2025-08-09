# Magic Mirror Dashboard

A customizable magic mirror dashboard built with Dash and Python, featuring real-time London Transport (TFL) arrivals, clock, and rotating compliments/jokes.

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure your locations:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and update the TFL stop IDs with your local transport stops. You can find stop IDs using the [TFL API](https://api.tfl.gov.uk/).

3. **Run the application:**
   ```bash
   just run
   ```
   
   Or directly with:
   ```bash
   uv run src/app/main.py
   ```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

- **TFL Stops**: Configure up to 2 stops for left side and 2 stops for right side
- **Component Positioning**: Fine-tune component positions and sizes
- **Layout**: Adjust positioning using fractional coordinates (0.0 to 1.0)

## TFL Stop IDs

To find your local transport stops:
1. Visit https://api.tfl.gov.uk/StopPoint/Search/{your-area}
2. Find your stop and note the `id` field
3. Update your `.env` file with the stop ID and a display name

## Features

- **Real-time TFL arrivals** with countdown timers
- **Live clock** with date display  
- **Rotating compliments and jokes** with 1000+ items
- **Flexible positioning** system with fractional coordinates
- **Responsive design** optimized for magic mirror displays
