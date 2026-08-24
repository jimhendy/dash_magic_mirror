import datetime
from typing import Any

from dash import html
from dash_iconify import DashIconify

from utils.dates import local_today
from utils.styles import COLORS, FONT_SIZES, WEIGHT

# Same "everything positioned inside an explicitly-sized box" geometry
# approach as the TFL arrivals timeline (src/components/tfl_arrivals/summary.py) -
# a badge tier, a line, and two label tiers (to dodge same-day collisions).
_BADGE_SIZE = "3.8rem"  # 200% of the original 1.9rem
_BADGE_SIZE_REM = 3.8
_BADGE_LANE_GAP_REM = 0.4
# Badges get two vertical lanes of their own (independent of the label
# tiers below) so two fixtures landing close together on the timeline never
# visually overlap - a close badge alternates into the lower lane instead
# of stacking directly on top of the previous one.
_BADGE_LANE_1_TOP = "0"
_BADGE_LANE_2_TOP = f"{_BADGE_SIZE_REM + _BADGE_LANE_GAP_REM}rem"
_BADGE_MIN_GAP_PCT = 16.0
_LINE_TOP = f"{2 * _BADGE_SIZE_REM + _BADGE_LANE_GAP_REM + 0.3}rem"
_LABEL_TIER_1_TOP = f"{2 * _BADGE_SIZE_REM + _BADGE_LANE_GAP_REM + 0.6}rem"
_LABEL_TIER_2_TOP = f"{2 * _BADGE_SIZE_REM + _BADGE_LANE_GAP_REM + 1.8}rem"
_TIMELINE_HEIGHT = f"{2 * _BADGE_SIZE_REM + _BADGE_LANE_GAP_REM + 2.3}rem"

WINDOW_DAYS = 7


def render_sports_summary(data: dict[str, Any], component_id: str) -> html.Div:
    """Render the sports summary as a single 7-day timeline, mirroring the
    TFL arrivals timeline, instead of one full-width row per fixture - a
    crest/icon badge per fixture is a far more compact way to show "who's
    playing and when" than a text row; tapping the card still opens the
    full-screen view for the rest of the details (competition, channel,
    per-sport filtering).
    """
    from .data import get_summary_fixtures

    fixtures = get_summary_fixtures(data, limit=8, days_ahead=WINDOW_DAYS)

    if not fixtures:
        return html.Div(
            "No upcoming fixtures",
            style={
                "color": COLORS["text_muted"],
                "fontSize": FONT_SIZES["primary"],
                "padding": "0.4rem 0",
            },
        )

    return _timeline(fixtures, days_ahead=WINDOW_DAYS)


def _fixture_label(fx: dict[str, Any], date_obj: datetime.date, is_today: bool) -> str:
    day_part = "TODAY" if is_today else date_obj.strftime("%a")
    time_part = fx.get("time", "")
    return f"{day_part} {time_part}".strip()


def _badge_style(fx: dict[str, Any], pct: float, ring: str, lane_top: str) -> dict:
    has_crest = bool(fx.get("crest"))
    return {
        "position": "absolute",
        "left": f"{pct}%",
        "top": lane_top,
        "transform": "translate(-50%, 0)",
        "width": _BADGE_SIZE,
        "height": _BADGE_SIZE,
        "borderRadius": "50%",
        "background": "#ffffff"
        if has_crest
        else fx.get("sport_icon_color", COLORS["text_secondary"]),
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "boxSizing": "border-box",
        "padding": "0.2rem",
        "boxShadow": ring,
        "flexShrink": 0,
    }


def _timeline(fixtures: list[dict[str, Any]], days_ahead: int) -> html.Div:
    """A single horizontal line spanning "today" to `days_ahead` from now.
    Each fixture is a badge on the line - the followed team's crest where
    known, otherwise a colored sport icon - positioned by date (and, where
    a kickoff time is known, time of day) with a day/time label below.

    As with the TFL timeline, labels alternate between two vertical tiers
    so two fixtures landing close together don't overlap illegibly. Badges
    get their own, independent two-lane alternation for the same reason -
    at 200% size two same-day (or unknown-kickoff-time, which both default
    to midday) fixtures would otherwise sit directly on top of each other.
    """
    today = local_today()
    label_min_gap_pct = 8.0
    last_label_tier_1_pct: float | None = None
    last_badge_lane_1_pct: float | None = None
    last_badge_lane_2_pct: float | None = None

    positioned: list[tuple[dict[str, Any], datetime.date, bool, float]] = []
    for fx in fixtures:
        if not fx.get("parsed_date"):
            continue
        try:
            date_obj = datetime.date.fromisoformat(fx["parsed_date"])
        except ValueError:
            continue

        days_away = (date_obj - today).days
        time_str = fx.get("time", "")
        try:
            hour_str, minute_str = time_str.split(":", 1)
            time_frac = (int(hour_str) + int(minute_str) / 60) / 24
        except (ValueError, AttributeError):
            time_frac = 0.5  # unknown kickoff time - place mid-day

        pct = max(0.0, min(100.0, ((days_away + time_frac) / days_ahead) * 100))
        positioned.append((fx, date_obj, days_away == 0, pct))

    # Badge-lane assignment needs fixtures in left-to-right (time) order to
    # correctly detect "close together", regardless of the original
    # per-sport selection order they arrived in.
    positioned.sort(key=lambda p: p[3])

    markers: list[html.Div] = []
    for fx, date_obj, is_today, pct in positioned:
        has_crest = bool(fx.get("crest"))

        if (
            last_badge_lane_1_pct is None
            or pct - last_badge_lane_1_pct >= _BADGE_MIN_GAP_PCT
        ):
            badge_lane_top = _BADGE_LANE_1_TOP
            last_badge_lane_1_pct = pct
        elif (
            last_badge_lane_2_pct is None
            or pct - last_badge_lane_2_pct >= _BADGE_MIN_GAP_PCT
        ):
            badge_lane_top = _BADGE_LANE_2_TOP
            last_badge_lane_2_pct = pct
        else:
            # Both lanes are crowded (3+ fixtures within the same tight
            # window) - fall back to whichever lane's last badge is
            # furthest away, which is the best achievable separation.
            if pct - last_badge_lane_1_pct >= pct - last_badge_lane_2_pct:
                badge_lane_top = _BADGE_LANE_1_TOP
                last_badge_lane_1_pct = pct
            else:
                badge_lane_top = _BADGE_LANE_2_TOP
                last_badge_lane_2_pct = pct

        if (
            last_label_tier_1_pct is None
            or pct - last_label_tier_1_pct >= label_min_gap_pct
        ):
            label_top = _LABEL_TIER_1_TOP
            last_label_tier_1_pct = pct
        else:
            label_top = _LABEL_TIER_2_TOP

        ring = (
            f"0 0 0 3px {COLORS['bg']}, 0 0 0 6px {COLORS['accent']}"
            if is_today
            else f"0 0 0 3px {COLORS['bg']}"
        )

        markers.append(
            html.Div(
                [
                    html.Img(
                        src=fx.get("crest"),
                        style={
                            "width": "100%",
                            "height": "100%",
                            "objectFit": "contain",
                            "display": "block" if has_crest else "none",
                        },
                    ),
                    DashIconify(
                        icon=fx.get("sport_icon", "mdi:help-circle"),
                        style={
                            "color": "#0a0a0a",
                            "fontSize": "2rem",
                            "display": "none" if has_crest else "block",
                        },
                    ),
                ],
                style=_badge_style(fx, pct, ring, badge_lane_top),
            ),
        )
        markers.append(
            html.Div(
                _fixture_label(fx, date_obj, is_today),
                style={
                    "position": "absolute",
                    "left": f"{pct}%",
                    "top": label_top,
                    "transform": "translateX(-50%)",
                    "fontSize": FONT_SIZES["small"],
                    "fontWeight": WEIGHT["semibold"] if is_today else WEIGHT["regular"],
                    "color": COLORS["accent"] if is_today else COLORS["text_secondary"],
                    "whiteSpace": "nowrap",
                },
            ),
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        "Today",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["text_muted"],
                        },
                    ),
                    html.Span(
                        f"+{days_ahead}d",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["text_muted"],
                        },
                    ),
                ],
                style={"display": "flex", "justifyContent": "space-between"},
            ),
            html.Div(
                [
                    html.Div(
                        style={
                            "position": "absolute",
                            "left": "0",
                            "right": "0",
                            "top": _LINE_TOP,
                            "height": "2px",
                            "background": COLORS["hairline_strong"],
                        },
                    ),
                    *markers,
                ],
                style={
                    "position": "relative",
                    "height": _TIMELINE_HEIGHT,
                    "margin": "0.3rem 0.4rem 0 0.4rem",
                },
            ),
        ],
    )
