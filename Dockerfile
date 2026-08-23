# Playwright's headless Chromium (used for the bin-collection scrape) only
# ships binaries for glibc distros, not musl/Alpine, so this is Debian-based
# rather than the alpine image used previously.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# curl is needed for docker-compose's healthcheck; not present by default.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock README.md /app/
RUN uv sync

# Chromium itself plus the OS libraries it needs - installed via Playwright's
# own CLI rather than hand-tracking its many transitive apt packages.
RUN uv run playwright install --with-deps chromium

COPY . /app
WORKDIR /app/src

# Expose port 8050 for the Dash application
EXPOSE 8050

ENTRYPOINT ["uv", "run", "python",  "-m", "app.main"]
