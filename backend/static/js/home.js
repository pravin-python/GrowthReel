(function () {
    var hero = document.getElementById('hero');
    var parallaxEls = Array.prototype.slice.call(document.querySelectorAll('.icon-parallax'));
    if (hero && parallaxEls.length) {
        var mouseX = 0;
        var mouseY = 0;
        var scrollProgress = 0;

        function applyTransforms() {
            parallaxEls.forEach(function (el, i) {
                var depth = parseFloat(el.getAttribute('data-depth')) || 20;
                var liftPx = scrollProgress * (60 + depth * 1.4);
                var rotateX = scrollProgress * (10 + i * 4);
                var rotateY = (mouseX * depth) * 0.6;
                var scale = 1 - scrollProgress * 0.25;
                el.style.transform =
                    'translate3d(' + (mouseX * depth) + 'px, ' + (mouseY * depth - liftPx) + 'px, 0) ' +
                    'perspective(700px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg) ' +
                    'scale(' + scale + ')';
            });
        }

        hero.addEventListener('mousemove', function (e) {
            var rect = hero.getBoundingClientRect();
            mouseX = (e.clientX - rect.left) / rect.width - 0.5;
            mouseY = (e.clientY - rect.top) / rect.height - 0.5;
            applyTransforms();
        });
        hero.addEventListener('mouseleave', function () {
            mouseX = 0;
            mouseY = 0;
            applyTransforms();
        });

        var scrollTicking = false;
        function onHeroScroll() {
            var rect = hero.getBoundingClientRect();
            var progress = -rect.top / rect.height;
            scrollProgress = Math.max(0, Math.min(1, progress));
            applyTransforms();
            scrollTicking = false;
        }
        window.addEventListener('scroll', function () {
            if (scrollTicking) return;
            scrollTicking = true;
            requestAnimationFrame(onHeroScroll);
        }, { passive: true });
        onHeroScroll();
    }

    document.querySelectorAll('[data-tilt]').forEach(function (el) {
        el.addEventListener('mousemove', function (e) {
            var rect = el.getBoundingClientRect();
            var x = e.clientX - rect.left;
            var y = e.clientY - rect.top;
            var rotateX = ((y - rect.height / 2) / rect.height) * -10;
            var rotateY = ((x - rect.width / 2) / rect.width) * 10;
            el.style.transform = 'perspective(900px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg) translateZ(10px)';
        });
        el.addEventListener('mouseleave', function () {
            el.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
        });
    });

    var revealEls = document.querySelectorAll('.reveal');
    function isInViewport(el) {
        var rect = el.getBoundingClientRect();
        var viewHeight = window.innerHeight || document.documentElement.clientHeight;
        return rect.top < viewHeight && rect.bottom > 0;
    }
    function checkReveals() {
        revealEls.forEach(function (el) {
            if (!el.classList.contains('is-visible') && isInViewport(el)) {
                el.classList.add('is-visible');
            }
        });
    }
    var scrollTicking = false;
    function onScroll() {
        if (scrollTicking) return;
        scrollTicking = true;
        requestAnimationFrame(function () {
            checkReveals();
            scrollTicking = false;
        });
    }
    checkReveals();
    window.addEventListener('load', checkReveals);
    window.addEventListener('resize', checkReveals);
    window.addEventListener('scroll', onScroll, { passive: true });

    if ('IntersectionObserver' in window) {
        var revealObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15 });
        revealEls.forEach(function (el) {
            if (!el.classList.contains('is-visible')) revealObserver.observe(el);
        });
    } else {
        revealEls.forEach(function (el) { el.classList.add('is-visible'); });
    }

    var counters = document.querySelectorAll('[data-count-to]');
    function animateCount(el) {
        var target = parseFloat(el.getAttribute('data-count-to'));
        var suffix = el.getAttribute('data-suffix') || '';
        var duration = 1400;
        var start = null;
        function step(timestamp) {
            if (!start) start = timestamp;
            var progress = Math.min((timestamp - start) / duration, 1);
            el.textContent = Math.floor(progress * target) + suffix;
            if (progress < 1) requestAnimationFrame(step);
            else el.textContent = target + suffix;
        }
        requestAnimationFrame(step);
    }
    function maybeAnimateCounters() {
        counters.forEach(function (el) {
            if (!el.hasAttribute('data-counted') && isInViewport(el)) {
                el.setAttribute('data-counted', 'true');
                animateCount(el);
            }
        });
    }
    window.addEventListener('scroll', maybeAnimateCounters, { passive: true });
    window.addEventListener('load', maybeAnimateCounters);
    maybeAnimateCounters();

    if ('IntersectionObserver' in window && counters.length) {
        var countObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting && !entry.target.hasAttribute('data-counted')) {
                    entry.target.setAttribute('data-counted', 'true');
                    animateCount(entry.target);
                    countObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.4 });
        counters.forEach(function (el) {
            if (!el.hasAttribute('data-counted')) countObserver.observe(el);
        });
    } else {
        counters.forEach(function (el) { animateCount(el); });
    }
})();
