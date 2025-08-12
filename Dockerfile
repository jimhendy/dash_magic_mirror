FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app    
COPY . /app

RUN uv sync

WORKDIR /app/src

# Expose port 8050 for the Dash application
EXPOSE 8050

ENTRYPOINT ["uv", "run", "python",  "-m", "app.main"]
