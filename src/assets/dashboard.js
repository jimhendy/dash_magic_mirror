// Client-side behaviour for the dashboard. Plain DOM code on purpose: none of
// this goes through Dash callbacks, so it responds instantly even while the
// Dash renderer is busy applying a background refresh on a slow tablet.
//
//  - Tap a tile ([data-open]) -> show its pre-mounted detail panel.
//  - [data-close] / inactivity countdown -> back to the dashboard.
//  - Clock ticking ([data-clock]).
//  - Filter chips ([data-filter-group] / [data-filter-key]).
//  - Headline rotation ([data-rotate]).
//
// Written in conservative ES5-ish JS (no optional chaining etc.) so it runs
// on older Android WebViews.
(function () {
    "use strict";

    var TAP_SLOP_PX = 24;
    var openPanelName = null;
    var remaining = 0;
    var lastActivity = Date.now();
    var suppressClicksUntil = 0;
    var filters = {}; // group -> selected value

    function timeoutSeconds() {
        var panels = document.getElementById("panels");
        var value = panels ? parseInt(panels.getAttribute("data-timeout"), 10) : NaN;
        return isNaN(value) ? 45 : value;
    }

    function closest(el, selector) {
        while (el && el.nodeType === 1) {
            if (el.matches ? el.matches(selector) : el.webkitMatchesSelector(selector)) {
                return el;
            }
            el = el.parentElement;
        }
        return null;
    }

    // ------------------------------------------------------------------
    // Panels
    // ------------------------------------------------------------------
    function openPanel(name) {
        var panel = document.querySelector('.panel[data-panel="' + name + '"]');
        if (!panel) {
            return;
        }
        var open = document.querySelectorAll(".panel.is-open");
        for (var i = 0; i < open.length; i++) {
            open[i].classList.remove("is-open");
        }
        panel.classList.add("is-open");
        document.documentElement.classList.add("has-panel");
        openPanelName = name;
        remaining = timeoutSeconds();
        lastActivity = Date.now();
        var body = panel.querySelector(".panel__body");
        if (body) {
            body.scrollTop = 0;
        }
        renderTimer();
        // The tap that opened the panel is followed by a synthetic click at
        // the same spot - which would otherwise land on whatever button now
        // sits there inside the panel.
        suppressClicksUntil = Date.now() + 450;
        // Plotly graphs mounted while hidden measured 0x0; make them re-fit.
        setTimeout(fireResize, 30);
        setTimeout(fireResize, 320);
    }

    function closePanel() {
        var open = document.querySelectorAll(".panel.is-open");
        for (var i = 0; i < open.length; i++) {
            open[i].classList.remove("is-open");
        }
        document.documentElement.classList.remove("has-panel");
        openPanelName = null;
        if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
        }
    }

    function fireResize() {
        try {
            window.dispatchEvent(new Event("resize"));
        } catch (e) {
            var evt = document.createEvent("UIEvents");
            evt.initUIEvent("resize", true, false, window, 0);
            window.dispatchEvent(evt);
        }
    }

    function renderTimer() {
        if (!openPanelName) {
            return;
        }
        var panel = document.querySelector('.panel[data-panel="' + openPanelName + '"]');
        var timer = panel && panel.querySelector("[data-timer]");
        if (!timer) {
            return;
        }
        var total = timeoutSeconds();
        timer.setAttribute("data-seconds", String(remaining));
        timer.style.setProperty("--progress", String(Math.max(0, remaining) / total));
    }

    // Tile taps: tracked with pointer down/up on the *tile frame* rather than a
    // click on whatever child was under the finger, so a background refresh
    // replacing the tile's contents mid-tap can't swallow the tap.
    var press = null;

    function onPressStart(x, y, target) {
        var tile = closest(target, "[data-open]");
        if (!tile || openPanelName) {
            press = null;
            return;
        }
        press = { el: tile, x: x, y: y };
        tile.classList.add("is-pressed");
    }

    function onPressEnd(x, y) {
        if (!press) {
            return;
        }
        var p = press;
        press = null;
        p.el.classList.remove("is-pressed");
        var dx = x - p.x;
        var dy = y - p.y;
        if (dx * dx + dy * dy <= TAP_SLOP_PX * TAP_SLOP_PX) {
            openPanel(p.el.getAttribute("data-open"));
        }
    }

    function onPressCancel() {
        if (press) {
            press.el.classList.remove("is-pressed");
            press = null;
        }
    }

    if (window.PointerEvent) {
        document.addEventListener("pointerdown", function (e) {
            if (e.isPrimary === false) {
                return;
            }
            onPressStart(e.clientX, e.clientY, e.target);
        }, { passive: true });
        document.addEventListener("pointerup", function (e) {
            onPressEnd(e.clientX, e.clientY);
        }, { passive: true });
        document.addEventListener("pointercancel", onPressCancel, { passive: true });
    } else {
        document.addEventListener("touchstart", function (e) {
            var t = e.touches[0];
            onPressStart(t.clientX, t.clientY, e.target);
        }, { passive: true });
        document.addEventListener("touchend", function (e) {
            var t = e.changedTouches[0];
            onPressEnd(t.clientX, t.clientY);
        }, { passive: true });
        document.addEventListener("touchcancel", onPressCancel, { passive: true });
        document.addEventListener("mousedown", function (e) {
            onPressStart(e.clientX, e.clientY, e.target);
        });
        document.addEventListener("mouseup", function (e) {
            onPressEnd(e.clientX, e.clientY);
        });
    }

    // Capture phase on window: runs before React's own listeners.
    window.addEventListener("click", function (e) {
        if (Date.now() < suppressClicksUntil) {
            e.stopPropagation();
            e.preventDefault();
            return;
        }
        if (closest(e.target, "[data-close]")) {
            closePanel();
            return;
        }
        var chip = closest(e.target, "[data-filter-value]");
        if (chip) {
            var group = closest(chip, "[data-filter-group]");
            if (group) {
                filters[group.getAttribute("data-filter-group")] = chip.getAttribute("data-filter-value");
                applyFilters();
            }
        }
    }, true);

    function markActivity() {
        lastActivity = Date.now();
    }

    ["pointerdown", "touchstart", "keydown", "wheel", "scroll"].forEach(function (type) {
        document.addEventListener(type, markActivity, { passive: true, capture: true });
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && openPanelName) {
            closePanel();
        }
    });

    // ------------------------------------------------------------------
    // Filters - re-applied after Dash re-renders a panel's contents.
    // ------------------------------------------------------------------
    function applyFilters() {
        var groups = document.querySelectorAll("[data-filter-group]");
        for (var g = 0; g < groups.length; g++) {
            var group = groups[g];
            var name = group.getAttribute("data-filter-group");
            var value = filters[name] || "all";
            var chips = group.querySelectorAll("[data-filter-value]");
            var known = false;
            for (var c = 0; c < chips.length; c++) {
                var isActive = chips[c].getAttribute("data-filter-value") === value;
                known = known || isActive;
                chips[c].classList.toggle("is-active", isActive);
            }
            if (!known) {
                value = "all";
                if (chips[0]) {
                    chips[0].classList.add("is-active");
                }
            }
            var scope = closest(group, ".panel") || document;
            var items = scope.querySelectorAll("[data-filter-key]");
            for (var i = 0; i < items.length; i++) {
                var show = value === "all" || items[i].getAttribute("data-filter-key") === value;
                items[i].classList.toggle("is-filtered-out", !show);
            }
            var scopes = scope.querySelectorAll("[data-filter-scope]");
            for (var s = 0; s < scopes.length; s++) {
                var anyVisible = scopes[s].querySelector("[data-filter-key]:not(.is-filtered-out)");
                scopes[s].classList.toggle("is-filtered-out", !anyVisible);
            }
        }
    }

    var filterQueued = false;

    function queueFilters() {
        if (filterQueued) {
            return;
        }
        filterQueued = true;
        (window.requestAnimationFrame || setTimeout)(function () {
            filterQueued = false;
            applyFilters();
        });
    }

    function watchPanels() {
        var panels = document.getElementById("panels");
        if (!panels || !window.MutationObserver) {
            setTimeout(watchPanels, 500);
            return;
        }
        new MutationObserver(queueFilters).observe(panels, { childList: true, subtree: true });
    }

    // ------------------------------------------------------------------
    // Clock + once-a-second housekeeping
    // ------------------------------------------------------------------
    var DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
    var MONTHS = ["January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December"];

    function pad(n) {
        return n < 10 ? "0" + n : String(n);
    }

    function setText(selector, text) {
        var els = document.querySelectorAll(selector);
        for (var i = 0; i < els.length; i++) {
            if (els[i].textContent !== text) {
                els[i].textContent = text;
            }
        }
    }

    function tick() {
        var now = new Date();
        setText('[data-clock="time"]', pad(now.getHours()) + ":" + pad(now.getMinutes()));
        setText('[data-clock="seconds"]', pad(now.getSeconds()));
        setText('[data-clock="date"]', DAYS[now.getDay()] + " " + now.getDate() + " " + MONTHS[now.getMonth()]);

        if (openPanelName) {
            if (Date.now() - lastActivity < 1500) {
                remaining = timeoutSeconds();
            } else {
                remaining -= 1;
            }
            if (remaining <= 0) {
                closePanel();
            } else {
                renderTimer();
            }
        }
    }

    // ------------------------------------------------------------------
    // Headline rotation
    // ------------------------------------------------------------------
    var rotateIndex = 0;

    function rotate() {
        var rotators = document.querySelectorAll("[data-rotate]");
        rotateIndex += 1;
        for (var r = 0; r < rotators.length; r++) {
            var items = rotators[r].children;
            if (!items.length) {
                continue;
            }
            var idx = rotateIndex % items.length;
            for (var i = 0; i < items.length; i++) {
                items[i].classList.toggle("is-active", i === idx);
            }
        }
    }

    function start() {
        tick();
        setInterval(tick, 1000);
        setInterval(rotate, 8000);
        watchPanels();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
