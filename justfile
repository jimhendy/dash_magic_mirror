_default:
    # Default target to show available commands
    @just --list
    

# Run the Magic Mirror app
run:
    cd src && uv run python -m app.main

# Install dependencies
install:
    uv sync

# Run tests
test:
    uv run pytest


_format:
    uv run ruff format

_lint:
    @-uv run ruff check --fix --select ALL > /dev/null 2>&1
    uv run ruff check --fix

# Make code pretty
ruff: _format _lint

# Run static type checks with Astral ty
types:
    uvx ty check