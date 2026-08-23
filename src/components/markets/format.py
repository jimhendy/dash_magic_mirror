"""Small display-formatting helpers shared by markets summary/full-screen."""

from __future__ import annotations

_CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "JPY": "¥"}


def format_price(value: float | None, currency: str) -> str:
    if value is None:
        return "?"
    symbol = _CURRENCY_SYMBOLS.get(currency, f"{currency} " if currency else "")
    return f"{symbol}{value:,.2f}"


def format_volume(value: float | None) -> str:
    if not value:
        return "-"
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if value >= threshold:
            return f"{value / threshold:.1f}{suffix}"
    return str(int(value))
