(function () {
    var track = document.getElementById('journey-track');
    var svg = document.getElementById('journey-svg');
    var progressPath = document.getElementById('journey-progress-path');
    var basePath = document.getElementById('journey-base-path');
    var items = track ? Array.prototype.slice.call(track.querySelectorAll('.journey-item')) : [];
    var nodes = track ? Array.prototype.slice.call(track.querySelectorAll('.journey-node')) : [];
    if (!track || !svg || !progressPath || !items.length) return;

    var trackHeight = 0;
    var totalLength = 0;
    var thresholds = [];

    function layout() {
        trackHeight = track.offsetHeight;
        var width = track.offsetWidth;
        var isMobile = width < 768;
        var cx = isMobile ? 24 : width / 2;
        svg.setAttribute('viewBox', '0 0 ' + width + ' ' + trackHeight);
        var d = 'M' + cx + ',0 L' + cx + ',' + trackHeight;
        basePath.setAttribute('d', d);
        progressPath.setAttribute('d', d);
        totalLength = progressPath.getTotalLength();
        progressPath.style.strokeDasharray = String(totalLength);
        progressPath.style.strokeDashoffset = String(totalLength);

        thresholds = items.map(function (item, i) {
            var centerY = item.offsetTop + item.offsetHeight / 2;
            if (nodes[i]) {
                nodes[i].style.top = centerY + 'px';
                nodes[i].style.left = cx + 'px';
            }
            return centerY / trackHeight;
        });
    }

    function clamp(v, min, max) {
        return Math.max(min, Math.min(max, v));
    }

    function onScroll() {
        var rect = track.getBoundingClientRect();
        var total = rect.height + window.innerHeight;
        var progress = clamp((window.innerHeight - rect.top) / total, 0, 1);

        progressPath.style.strokeDashoffset = String(totalLength * (1 - progress));

        nodes.forEach(function (node, i) {
            var isActive = progress >= (thresholds[i] - 0.015);
            node.classList.toggle('is-active', isActive);
        });
    }

    var ticking = false;
    function requestTick() {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(function () {
            onScroll();
            ticking = false;
        });
    }

    layout();
    onScroll();
    window.addEventListener('scroll', requestTick, { passive: true });
    window.addEventListener('resize', function () {
        layout();
        onScroll();
    });
    window.addEventListener('load', function () {
        layout();
        onScroll();
    });
})();
