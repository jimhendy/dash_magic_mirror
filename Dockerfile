FROM ghcr.io/astral-sh/uv:python3.13-alpine

# curl is needed for docker-compose's healthcheck; not present on alpine by default.
RUN apk add --no-cache curl

WORKDIR /app
COPY pyproject.toml uv.lock README.md /app/
RUN uv sync

COPY . /app
WORKDIR /app/src

# Expose port 8050 for the Dash application
EXPOSE 8050

ENTRYPOINT ["uv", "run", "python",  "-m", "app.main"]
