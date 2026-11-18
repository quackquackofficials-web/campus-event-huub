/* ==================================================================
   CAMPUS EVENT HUB - ANIMATIONS
   Uses: AOS, GSAP, ScrollTrigger, ScrollSmoother, SplitText,
         Draggable, Flip (all loaded in base.html)

   Mapping to the animation codes:
   - SCROLL 1  : ScrollTrigger scrub timeline  -> events section
   - SCROLL 2  : data-speed (ScrollSmoother)   -> hero + home page
   - TEXT 1    : SplitText chars / words / lines -> hero + headings
   - TEXT 2    : SplitText chars + combo        -> hero title + about heading
   - DRAGGABLE : drag category cards over the title to recolour it
   - FLIP      : Fest Spotlight gallery (click a tile to swap)
   - FLIP FROM AOS : data-aos="flip-left" on event cards
   ================================================================== */

(function () {
    "use strict";

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isHome = document.body.dataset.page === "home";

    /* ---------- FLIP FROM AOS : data-aos="flip-left" ---------- */
    if (window.AOS) {
        AOS.init({
            duration: 900,
            once: true,
            offset: 80,
            disable: reduceMotion
        });
    }

    // Everything below needs GSAP (and the user not asking for reduced motion)
    if (!window.gsap || reduceMotion) return;

    const plugins = [
        window.ScrollTrigger,
        window.ScrollSmoother,
        window.SplitText,
        window.Draggable,
        window.Flip
    ].filter(Boolean);
    gsap.registerPlugin(...plugins);
    gsap.config({ nullTargetWarn: false });

    /* ---------- SCROLL 2 : data-speed (ScrollSmoother) ----------
       <div data-speed="0.8"></div>  <div data-speed="2.0"></div> ...
       Only on the home page, where the data-speed attributes are used. */
    let smoother = null;

    if (isHome && window.ScrollSmoother && window.ScrollTrigger) {
        smoother = ScrollSmoother.create({
            wrapper: "#smooth-wrapper",
            content: "#smooth-content",
            smooth: 1,
            effects: true            // enables data-speed / data-lag
        });
        document.documentElement.classList.add("has-smoother");

        // Anchor links (#events, /#fests ...) scroll through the smoother
        document.querySelectorAll('a[href*="#"]').forEach((link) => {
            link.addEventListener("click", (event) => {
                const url = new URL(link.href, window.location.href);
                if (url.pathname !== window.location.pathname || !url.hash) return;

                const target = document.querySelector(url.hash);
                if (!target) return;

                event.preventDefault();
                smoother.scrollTo(target, true, "top top");
                history.replaceState(null, "", url.hash);
            });
        });

        window.addEventListener("load", () => {
            if (window.location.hash) {
                const target = document.querySelector(window.location.hash);
                if (target) smoother.scrollTo(target, false, "top top");
            }
        });
    }

    /* ---------- SCROLL 1 : ScrollTrigger scrub timeline ---------- */
    if (window.ScrollTrigger && document.querySelector(".scroll-trigger-ready__worm-wrap")) {
        const scrollTimeline = gsap.timeline({
            scrollTrigger: {
                scrub: 1,
                trigger: ".scroll-trigger-ready__worm-wrap",
                start: "top 90%",
                end: "bottom 30%",
            },
        });

        scrollTimeline
            .fromTo(".events-section .section-heading",
                { y: 80, opacity: 0.2 },
                { y: 0, opacity: 1, ease: "none" }, 0)
            .fromTo(".events-section .event-subheading",
                { x: -60, opacity: 0.2 },
                { x: 0, opacity: 1, ease: "none", stagger: 0.3 }, 0.1);
    }

    /* ---------- TEXT 1 + TEXT 2 : SplitText ---------- */
    if (window.SplitText) {

        // Effects from TEXT 1 (chars / words / lines) and TEXT 2 (combo)
        const effects = {
            chars: (split) => gsap.from(split.chars, {
                x: 150, opacity: 0, duration: 0.7, ease: "power4", stagger: 0.04
            }),

            words: (split) => gsap.from(split.words, {
                y: -100, opacity: 0, rotation: "random(-80, 80)",
                duration: 0.7, ease: "back", stagger: 0.15
            }),

            lines: (split) => gsap.from(split.lines, {
                rotationX: -100, transformOrigin: "50% 50% -160px",
                opacity: 0, duration: 0.8, ease: "power3", stagger: 0.25
            }),

            // TEXT 2 "chars words and lines" (the final fade-out of the
            // lines is left out so the text stays on the page)
            combo: (split, scrollTrigger) => gsap.timeline({ scrollTrigger })
                .from(split.chars, {
                    duration: 0.6, autoAlpha: 0, scale: 3, force3D: true, stagger: 0.02
                }, 0.5)
                .to(split.words, {
                    duration: 0.2, color: "#ffd34f", scale: 0.9, stagger: 0.1
                }, "words")
                .to(split.words, {
                    duration: 0.4, color: "white", scale: 1, stagger: 0.1
                }, "words+=0.1")
        };

        /* ----- Hero ----- */
        const heroTitle = document.querySelector(".hero h1");
        const heroTag = document.querySelector(".hero-tag");
        const heroSubtitle = document.querySelector(".hero-subtitle");
        const heroDescription = document.querySelector(".hero-description");

        let heroSplit = null;
        let heroReady = false;
        let heroAnimation = null;

        if (heroTitle) {
            gsap.set(heroTitle, { perspective: 400 });

            // TEXT 2 chars effect plays on load
            SplitText.create(heroTitle, {
                type: "chars,words,lines",
                autoSplit: true,
                onSplit(self) {
                    heroSplit = self;
                    return gsap.from(self.chars, {
                        duration: 1, scale: 4, autoAlpha: 0, rotationX: -180,
                        transformOrigin: "100% 50%", ease: "back", stagger: 0.02,
                        onComplete: () => { heroReady = true; }
                    });
                }
            });

            // TEXT 1 buttons -> click the title to cycle chars / words / lines / combo
            const order = ["chars", "words", "lines", "combo"];
            let step = 0;
            heroTitle.style.cursor = "pointer";
            heroTitle.title = "Click for another text effect";

            heroTitle.addEventListener("click", () => {
                if (!heroReady || !heroSplit) return;

                heroAnimation && heroAnimation.revert();
                heroAnimation = effects[order[step % order.length]](heroSplit);
                step++;
            });
        }

        if (heroTag) {
            SplitText.create(heroTag, {
                type: "chars",
                autoSplit: true,
                onSplit: (self) => gsap.from(self.chars, {
                    x: 150, opacity: 0, duration: 0.7, ease: "power4",
                    stagger: 0.04, delay: 0.2
                })
            });
        }

        if (heroSubtitle) {
            SplitText.create(heroSubtitle, {
                type: "words",
                autoSplit: true,
                onSplit: (self) => gsap.from(self.words, {
                    y: -100, opacity: 0, rotation: "random(-80, 80)",
                    duration: 0.7, ease: "back", stagger: 0.15, delay: 0.8
                })
            });
        }

        if (heroDescription) {
            gsap.set(heroDescription, { perspective: 500 });
            SplitText.create(heroDescription, {
                type: "lines",
                autoSplit: true,
                onSplit: (self) => gsap.from(self.lines, {
                    rotationX: -100, transformOrigin: "50% 50% -160px",
                    opacity: 0, duration: 0.8, ease: "power3",
                    stagger: 0.25, delay: 1.3
                })
            });
        }

        /* ----- Section headings: characters fly in on scroll ----- */
        document.querySelectorAll(".section-heading h2").forEach((heading) => {
            SplitText.create(heading, {
                type: "chars",
                autoSplit: true,
                onSplit: (self) => gsap.from(self.chars, {
                    x: 150, opacity: 0, duration: 0.7, ease: "power4", stagger: 0.04,
                    scrollTrigger: { trigger: heading, start: "top 88%" }
                })
            });
        });

        /* ----- About heading: TEXT 2 combo on scroll ----- */
        const aboutHeading = document.querySelector(".about-section h2");
        if (aboutHeading) {
            SplitText.create(aboutHeading, {
                type: "chars,words,lines",
                autoSplit: true,
                onSplit: (self) => effects.combo(self, {
                    trigger: aboutHeading, start: "top 80%"
                })
            });
        }
    }

    /* ---------- DRAGGABLE : drag a category over the title ---------- */
    const dragTarget = document.querySelector(".drag-target");
    const categoryCards = gsap.utils.toArray(".category-card");
    const hasMouse = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

    if (window.Draggable && dragTarget && categoryCards.length && hasMouse) {
        const colors = ["#f52baf", "#00d9ff", "#ffd34f", "#8bffcf", "#c58bff", "#ff8709"];

        categoryCards.forEach((card, i) => {
            const itemColor = colors[i % colors.length];
            card.classList.add("is-draggable");

            Draggable.create(card, {
                onPress: () => {   // bring the item forward on press
                    gsap.to(card, { duration: 0.1, scale: 1.2, rotate: "random(-9,9)", zIndex: 100 });
                    gsap.to(categoryCards, { duration: 0.1, opacity: (n, t) => (t === card) ? 1 : 0.3 });
                },
                onRelease: () => { // return the item on release
                    gsap.to(card, { duration: 0.4, x: 0, y: 0, rotate: 0, scale: 1, ease: "elastic.out(.45)" });
                    gsap.to(categoryCards, { duration: 0.2, opacity: 1, zIndex: 0 });
                },
                onDrag: () => {
                    // prevent overlapping colour changes
                    if (!gsap.isTweening(dragTarget)) {
                        if (Draggable.hitTest(card, dragTarget, 12)) {
                            gsap.to(dragTarget, { duration: 0.3, color: itemColor });
                        }
                    }
                }
            });
        });
    }

    /* ---------- FLIP : Fest Spotlight gallery ---------- */
    const festTiles = gsap.utils.toArray(".fest-tile");

    if (window.Flip && festTiles.length) {
        let active = festTiles[0];

        function changeGrid(el) {
            if (el === active) return;

            const state = Flip.getState(festTiles);

            active.dataset.grid = el.dataset.grid;
            el.dataset.grid = "main";
            active = el;

            Flip.from(state, {
                duration: 0.3,
                absolute: true,
                ease: "power1.inOut"
            });
        }

        festTiles.forEach((el) => {
            el.setAttribute("tabindex", "0");
            el.setAttribute("role", "button");

            el.addEventListener("click", (event) => {
                if (event.target.closest("a")) return;   // let the link work
                changeGrid(el);
            });
            el.addEventListener("keydown", (event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    changeGrid(el);
                }
            });
        });
    }

    /* ---------- Refresh once images / fonts have settled ---------- */
    window.addEventListener("load", () => {
        if (window.ScrollTrigger) ScrollTrigger.refresh();
        if (window.AOS) AOS.refresh();
    });
})();