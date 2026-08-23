"""Constants for Weather component."""

BASE_URL: str = "http://api.weatherapi.com/v1"
FORECAST_DAYS: int = 3
HTTP_TIMEOUT: int = 30
# Matches FORECAST_DAYS: the "next 48h" sparkline needs hourly data reaching
# 48h past *now*, which - depending on the time of day - can spill into the
# 3rd fetched day. The extra day costs nothing extra: it's already part of
# the same API response (FORECAST_DAYS=3), just previously left unextracted.
HOURLY_WINDOW_DAYS: int = 3
