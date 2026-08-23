"""Design tokens and style-building helpers shared by every component.

Visual language: an editorial, quiet-luxury dashboard, not a UI-kit template.
Concretely that means:

- Individual data rows (a calendar event, a bus arrival, a fixture) are NOT
  boxed in bordered/shadowed cards. They're plain text on the dark
  background, separated by whitespace and - where genuinely useful - a
  single thin left accent bar. Boxing every row is the single biggest
  "generated from a component library" tell, so `row_style()` is
  deliberately borderless/background-less by default.
- Each section opens with a small muted uppercase "kicker" label
  (`kicker_style()`), the way a printed page or a well-art-directed
  dashboard identifies a section - not with a glowing divider line.
- One accent color is used sparingly, for the single most current/live
  thing in a section - never as a background fill on every list item.
- Typography carries the hierarchy: very light large numerals for hero
  data (the clock, the current temperature) against small bold tracked
  labels for meta text, rather than relying on boxes/color to separate
  levels of importance.
- No `backdrop-filter` blur and minimal box-shadow, so this stays cheap to
  composite on the Pi 4 / an old tablet GPU.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
COLORS: dict[str, str] = {
    "bg": "#040509",
    "bg_gradient": "linear-gradient(165deg, #050609 0%, #0a0d13 55%, #040509 100%)",
    # Reserved for the rare true container (modal chrome, sticky filter bar).
    "surface": "rgba(255, 255, 255, 0.035)",
    "surface_raised": "rgba(255, 255, 255, 0.06)",
    # Hairlines only - never a full box border.
    "hairline": "rgba(255, 255, 255, 0.07)",
    "hairline_strong": "rgba(255, 255, 255, 0.13)",
    # Text
    "text": "#F5F6F8",
    "text_secondary": "#8A93A1",
    "text_muted": "#4B5361",
    # The one accent: "now / today / live / current".
    "accent": "#5EEAD4",
    "accent_dim": "rgba(94, 234, 212, 0.5)",
    # Reserved for genuinely time-critical states only (imminent arrival,
    # disruption, error) - never used decoratively.
    "urgent": "#FF6B6B",
    # Rare warm accent (birthdays, high temperature) - used sparingly.
    "gold": "#F2B950",
    # Aliases for spots that need a plain black/white literal.
    "black": "#040509",
    "white": "#F5F6F8",
}

# ---------------------------------------------------------------------------
# Spacing / radius scale
# ---------------------------------------------------------------------------
SPACE: dict[str, str] = {
    "xs": "0.25rem",
    "sm": "0.5rem",
    "md": "0.75rem",
    "lg": "1.1rem",
    "xl": "1.75rem",
    "xxl": "2.5rem",
}

RADIUS: dict[str, str] = {
    "sm": "0.4rem",
    "md": "0.7rem",
    "pill": "999px",
}

# ---------------------------------------------------------------------------
# Typography scale (rem-based, tuned for a ~1-1.2m viewing distance)
# ---------------------------------------------------------------------------
FONT_FAMILY = "'Inter', -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

FONT_SIZES: dict[str, str] = {
    "display": "5.75rem",  # clock / hero numerals
    "heading": "1.7rem",  # a section's single most important line
    "primary": "1.55rem",  # main row content (times, team names, temps)
    "secondary": "1.35rem",  # secondary row content
    "meta": "1.1rem",  # subtext / meta info
    "small": "0.95rem",  # rare very small annotations
    "kicker": "0.95rem",  # section label
}

WEIGHT: dict[str, str] = {
    "hero": "250",
    "bold": "700",
    "semibold": "600",
    "regular": "450",
    "light": "350",
}

LINE_HEIGHT_DEFAULT = "1.25"

TEXT_STYLES: dict[str, dict[str, Any]] = {
    "heading": {
        "fontSize": FONT_SIZES["heading"],
        "fontWeight": WEIGHT["semibold"],
        "color": COLORS["text"],
        "letterSpacing": "-0.01em",
    },
    "primary": {
        "fontSize": FONT_SIZES["primary"],
        "fontWeight": WEIGHT["regular"],
        "color": COLORS["text"],
    },
    "secondary": {
        "fontSize": FONT_SIZES["secondary"],
        "fontWeight": WEIGHT["regular"],
        "color": COLORS["text_secondary"],
    },
    "meta": {
        "fontSize": FONT_SIZES["meta"],
        "fontWeight": WEIGHT["regular"],
        "color": COLORS["text_secondary"],
    },
    "small": {
        "fontSize": FONT_SIZES["small"],
        "fontWeight": WEIGHT["regular"],
        "color": COLORS["text_muted"],
    },
}


def merge_styles(*styles: dict[str, Any] | None) -> dict[str, Any]:
    """Shallow-merge any number of style dicts, later ones winning. `None` is ignored."""
    result: dict[str, Any] = {}
    for style in styles:
        if style:
            result.update(style)
    return result


def text_style(scale: str, **overrides: Any) -> dict[str, Any]:
    """A typography style from the scale, with optional overrides."""
    return merge_styles(TEXT_STYLES.get(scale, {}), overrides)


def kicker_style(**overrides: Any) -> dict[str, Any]:
    """Small muted uppercase section label - identifies a section instead of a
    boxed header or a glowing divider line.
    """
    base = {
        "fontSize": FONT_SIZES["kicker"],
        "fontWeight": WEIGHT["bold"],
        "textTransform": "uppercase",
        "letterSpacing": "0.12em",
        "color": COLORS["text_muted"],
    }
    return merge_styles(base, overrides)


def hero_style(size: str = FONT_SIZES["display"], **overrides: Any) -> dict[str, Any]:
    """Big, light-weight numeral/text display (clock, current temperature).

    `tabular-nums` keeps every digit the same width, so a value that
    updates in place (the clock, a countdown) doesn't visibly shift as its
    digits change.
    """
    base = {
        "fontSize": size,
        "fontWeight": WEIGHT["hero"],
        "color": COLORS["text"],
        "lineHeight": "1",
        "letterSpacing": "-0.02em",
        "fontVariantNumeric": "tabular-nums",
    }
    return merge_styles(base, overrides)


def row_style(
    *, divider: bool = False, accent: bool = False, **overrides: Any,
) -> dict[str, Any]:
    """The default treatment for a repeated list item (a calendar event, an
    arrival, a fixture, a headline): no border, no background box, no
    shadow - just padding and, optionally, a hairline bottom divider. Pass
    `accent=True` for a "now/today/live" row - it gets a thin accent bar on
    the left edge instead of a filled background.
    """
    base: dict[str, Any] = {
        "padding": f"{SPACE['md']} 0",
        "borderBottom": f"1px solid {COLORS['hairline']}" if divider else "none",
        "borderLeft": f"2px solid {COLORS['accent']}"
        if accent
        else "2px solid transparent",
        "paddingLeft": SPACE["md"],
    }
    return merge_styles(base, overrides)


def panel_style(*, radius: str = RADIUS["md"], **overrides: Any) -> dict[str, Any]:
    """The rare true container: modal chrome, a sticky filter bar. Faint fill,
    hairline border, no shadow. Not for individual list rows.
    """
    base = {
        "background": COLORS["surface"],
        "border": f"1px solid {COLORS['hairline']}",
        "borderRadius": radius,
    }
    return merge_styles(base, overrides)


def chip_style(*, color: str = COLORS["accent"], **overrides: Any) -> dict[str, Any]:
    """A small pill control - reserved for interactive controls (filter
    buttons), not for decorating data rows.
    """
    base = {
        "display": "inline-flex",
        "alignItems": "center",
        "gap": SPACE["xs"],
        "padding": f"{SPACE['xs']} {SPACE['sm']}",
        "borderRadius": RADIUS["pill"],
        "border": f"1px solid {color}",
        "color": COLORS["text"],
        "fontSize": FONT_SIZES["small"],
        "fontWeight": WEIGHT["semibold"],
    }
    return merge_styles(base, overrides)


def section_gap() -> str:
    """Minimum vertical rhythm between top-level components on the main strip.

    This is a floor, not the actual spacing: `app/core_layout.py` uses
    `justify-content: space-evenly` so any leftover viewport height is
    auto-distributed as *extra* gap on top of this, rather than left
    stranded below the last component or forcing every layout decision to
    assume a cramped screen.
    """
    return SPACE["lg"]


# ---------------------------------------------------------------------------
# Backwards-compatible aggregate (kept small; prefer the helpers above)
# ---------------------------------------------------------------------------
COMPACT_STYLES = {
    "base_container": {
        "background": COLORS["bg"],
        "lineHeight": LINE_HEIGHT_DEFAULT,
        "width": "100vw",
        "height": "100vh",
        "position": "relative",
        "left": "0",
        "top": "0",
    },
}
