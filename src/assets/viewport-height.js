// `vh`/`dvh` CSS units are handled inconsistently across mobile WebViews -
// this was seen to work in desktop Chrome but not in Fully Kiosk Browser
// (Android WebView, GrapheneOS). Rather than guessing at more CSS unit
// workarounds we can't test on that device, measure the real viewport
// height directly and pin it as an exact pixel value via a CSS custom
// property. `main.css` uses `var(--vh, 100dvh)` - the `vh`/`dvh` fallback
// chain there only matters for the brief instant before this script runs.
(function () {
    function setViewportHeight() {
        var height = (window.visualViewport && window.visualViewport.height) || window.innerHeight;
        document.documentElement.style.setProperty("--vh", height + "px");
    }

    setViewportHeight();
    window.addEventListener("resize", setViewportHeight);
    window.addEventListener("orientationchange", setViewportHeight);
    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", setViewportHeight);
    }
})();
