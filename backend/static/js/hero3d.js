import * as THREE from './vendor/three.module.min.js';

(function () {
    var wrapper = document.getElementById('showcase-wrapper');
    var mount = document.getElementById('showcase-canvas');
    if (!wrapper || !mount) return;

    var steps = Array.prototype.slice.call(wrapper.querySelectorAll('.showcase-step'));
    if (!steps.length) return;

    var waypoints = steps.map(function (el) {
        return {
            x: parseFloat(el.getAttribute('data-obj-x')) || 0,
            y: parseFloat(el.getAttribute('data-obj-y')) || 0,
            tilt: parseFloat(el.getAttribute('data-obj-tilt')) || 0,
            scale: parseFloat(el.getAttribute('data-obj-scale')) || 1
        };
    });

    var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    mount.appendChild(renderer.domElement);

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 0, 6);

    var keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
    keyLight.position.set(3, 4, 5);
    scene.add(keyLight);

    var fillLight = new THREE.DirectionalLight(0x0ffcbe, 1.4);
    fillLight.position.set(-4, -1, 3);
    scene.add(fillLight);

    var rimLight = new THREE.PointLight(0x106ebe, 3.5, 20);
    rimLight.position.set(-2, 2, -4);
    scene.add(rimLight);

    scene.add(new THREE.HemisphereLight(0x8fb8ff, 0x0a1830, 0.6));

    var geometry = new THREE.TorusKnotGeometry(1.1, 0.34, 220, 40);
    var material = new THREE.MeshPhysicalMaterial({
        color: 0x2f6fb0,
        metalness: 0.9,
        roughness: 0.2,
        clearcoat: 1,
        clearcoatRoughness: 0.15,
        reflectivity: 0.6,
        emissive: 0x0b3a52,
        emissiveIntensity: 0.25
    });
    var mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    var current = { x: waypoints[0].x, y: waypoints[0].y, tilt: waypoints[0].tilt, scale: waypoints[0].scale };
    var target = waypoints[0];
    var spin = 0;

    function resize() {
        var w = mount.clientWidth || window.innerWidth;
        var h = mount.clientHeight || window.innerHeight;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }
    window.addEventListener('resize', resize);
    resize();

    var activeIndex = 0;
    var stepObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting && entry.intersectionRatio > 0.5) {
                var idx = steps.indexOf(entry.target);
                if (idx !== -1) {
                    activeIndex = idx;
                    target = waypoints[idx];
                }
            }
        });
    }, { threshold: [0.5] });
    steps.forEach(function (el) { stepObserver.observe(el); });

    var isActive = false;
    var wrapperObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            isActive = entry.isIntersecting;
            mount.style.opacity = isActive ? '1' : '0';
        });
    }, { threshold: 0, rootMargin: '0px' });
    wrapperObserver.observe(wrapper);

    var lastTime = performance.now();
    function animate(now) {
        requestAnimationFrame(animate);
        var dt = Math.min((now - lastTime) / 1000, 0.1);
        lastTime = now;
        if (!isActive) return;

        var damp = 1 - Math.pow(0.0015, dt);
        current.x += (target.x - current.x) * damp;
        current.y += (target.y - current.y) * damp;
        current.tilt += (target.tilt - current.tilt) * damp;
        current.scale += (target.scale - current.scale) * damp;

        spin += dt * 0.35;
        mesh.position.set(current.x, current.y, 0);
        mesh.rotation.set(current.tilt, spin, spin * 0.4);
        mesh.scale.setScalar(current.scale);

        renderer.render(scene, camera);
    }
    requestAnimationFrame(animate);
})();
