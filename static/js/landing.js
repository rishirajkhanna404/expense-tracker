// landing.js — hero "See how it works" modal
// Vanilla JS only. No frameworks, no YouTube IFrame API dependency.

(function () {
    "use strict";

    var VIDEO_ID = "dQw4w9WgXcQ"; // placeholder; replace via data-src on the iframe

    function init() {
        var modal = document.getElementById("howItWorksModal");
        if (!modal) return;

        var iframe = document.getElementById("howItWorksVideo");
        var openers = document.querySelectorAll(".landing-btn-secondary");
        var closers = modal.querySelectorAll("[data-modal-close]");
        var lastFocused = null;

        function getVideoSrc() {
            return iframe.getAttribute("data-src") || ("https://www.youtube.com/embed/" + VIDEO_ID);
        }

        function open(e) {
            if (e) e.preventDefault();
            lastFocused = document.activeElement;
            iframe.setAttribute("src", getVideoSrc());
            modal.classList.add("is-open");
            modal.setAttribute("aria-hidden", "false");
            document.body.style.overflow = "hidden";
            var closeBtn = modal.querySelector(".landing-modal-close");
            if (closeBtn) closeBtn.focus();
        }

        function close() {
            // Clearing the src is the only dependency-free way to stop a YouTube
            // embed from playing in the background. We restore the original via
            // a sentinel URL so the next open() can replay it.
            iframe.setAttribute("src", "about:blank");
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
            document.body.style.overflow = "";
            if (lastFocused && typeof lastFocused.focus === "function") {
                lastFocused.focus();
            }
        }

        for (var i = 0; i < openers.length; i++) {
            openers[i].addEventListener("click", open);
        }

        for (var j = 0; j < closers.length; j++) {
            closers[j].addEventListener("click", function (e) {
                e.preventDefault();
                close();
            });
        }

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && modal.classList.contains("is-open")) {
                close();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
