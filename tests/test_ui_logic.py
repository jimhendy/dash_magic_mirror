import datetime
from zoneinfo import ZoneInfo

from components.tfl_arrivals.summary import (
    PRIMARY_ROWS,
    group_departures,
    render_tfl_summary,
)
from components.weather.data import first_rain_hour, upcoming_hours
from utils.dates import datetime_from_str


def _arrival(line_id, destination, minutes, *, mode="bus"):
    return {
        "line_id": line_id,
        "line_name": line_id.title(),
        "destination": destination,
        "minutes": minutes,
        "mode": mode,
        "line_color": "#EE3124",
    }


def test_group_departures_collapses_by_line_and_destination():
    groups = group_departures(
        [
            _arrival("38", "Clapton Pond", 9),
            _arrival("38", "Clapton Pond", 2),
            _arrival("55", "Walthamstow", 5),
        ],
    )
    assert [g["first"]["line_id"] for g in groups] == ["38", "55"]
    assert groups[0]["minutes"] == [2, 9]


def test_priority_line_always_in_visible_portrait_rows():
    arrivals = [_arrival(str(n), f"Dest {n}", n) for n in range(1, 9)]
    arrivals.append(_arrival("weaver", "Chingford", 25, mode="overground"))

    board = render_tfl_summary(arrivals, priority_line_ids=["weaver"])
    visible = board.children[:PRIMARY_ROWS]
    names = [row.children[0].children[1].children for row in visible]
    assert "Weaver" in names


def test_upcoming_hours_and_rain_heads_up():
    tz = ZoneInfo("Europe/London")
    now = datetime.datetime(2026, 10, 25, 14, 20, tzinfo=tz)
    hourly = [
        {"time": f"2026-10-25 {h:02d}:00", "rain_chance": 70 if h == 17 else 10}
        for h in range(24)
    ]
    hours = upcoming_hours(hourly, 6, now=now)
    assert [h["dt"].hour for h in hours] == [14, 15, 16, 17, 18, 19]
    assert first_rain_hour(hours)["dt"].hour == 17


def test_timed_events_are_shown_in_local_time(monkeypatch):
    monkeypatch.setenv("APP_TIMEZONE", "Europe/London")
    dt = datetime_from_str("2026-07-01T23:30:00Z", is_all_day=False)
    assert (dt.date(), dt.hour) == (datetime.date(2026, 7, 2), 0)


def test_market_day_change_uses_previous_session_not_chart_start():
    from components.markets.constants import MARKET_INDICES
    from components.markets.data import process_market_data

    day = 86_400
    raw = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 99.0,
                        "chartPreviousClose": 50.0,
                        "regularMarketTime": 2 * day,
                    },
                    "timestamp": [0, day, 2 * day],
                    "indicators": {"quote": [{"close": [80.0, 100.0, 99.0]}]},
                },
            ],
        },
    }
    market = process_market_data(raw, MARKET_INDICES[0])
    assert round(market["day_change_pct"], 2) == -1.0


def test_coming_up_lists_new_events_once_and_skips_ongoing(monkeypatch):
    import components.google_calendar.summary as cal
    from components.google_calendar.data import CalendarEvent

    tz = ZoneInfo("Europe/London")
    today = datetime.date(2026, 10, 25)
    monkeypatch.setattr(
        cal,
        "local_now",
        lambda: datetime.datetime(2026, 10, 25, 9, 0, tzinfo=tz),
    )

    def event(eid, start, days):
        begin = datetime.datetime.combine(
            today + datetime.timedelta(days=start), datetime.time(), tz
        )
        return CalendarEvent(
            id=eid,
            title=eid,
            start_datetime=begin,
            end_datetime=begin + datetime.timedelta(days=days),
            is_all_day=True,
            is_multi_day=days > 1,
            starts_before_today=start < 0,
            ends_after_tomorrow=start + days > 2,
            calendar_id="c",
        )

    column = cal._upcoming_column(
        today + datetime.timedelta(days=1),
        [event("half term", -1, 6), event("trip", 3, 3)],
        {},
    )
    titles = [row.children[2].children for row in column.children[1].children]
    assert titles == ["trip"]


def test_disrupted_priority_line_gets_banner_and_good_service_a_tick():
    from components.tfl_arrivals.summary import render_tfl_badge

    def status(color, text):
        return {
            "weaver": {
                "line_name": "Weaver",
                "status_text": text,
                "status_color": color,
                "reason": "WEAVER LINE: Severe delays due to a signal failure.",
            },
        }

    bad = status("red", "Severe Delays")
    board = render_tfl_summary(
        [_arrival("weaver", "Chingford", 3, mode="overground")],
        priority_line_ids=["weaver"],
        line_status=bad,
    )
    title, reason = board.children[0].children[1].children
    assert title.children == "Weaver: Severe Delays"
    assert reason.children == "Severe delays due to a signal failure."
    assert render_tfl_badge(bad, {}, ["weaver"]) is None

    good = status("green", "Good Service")
    board = render_tfl_summary(
        [_arrival("weaver", "Chingford", 3, mode="overground")],
        priority_line_ids=["weaver"],
        line_status=good,
    )
    assert board.children[0].className == "board__row"
    assert render_tfl_badge(good, {}, ["weaver"]).className == "status-ok"
