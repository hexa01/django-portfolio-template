// 404 robot: looks at the pointer, blinks now and then, and when poked.
(function () {
  var svg = document.querySelector('.mascot');
  if (!svg || !matchMedia('(prefers-reduced-motion: no-preference)').matches) return;

  var head = svg.querySelector('.mascot-head');
  var pupils = svg.querySelectorAll('.mascot-pupil');
  var target = null;
  var queued = false;

  function look() {
    queued = false;
    var box = svg.getBoundingClientRect();
    var scale = box.width / 160;
    var cx = box.left + 80 * scale, cy = box.top + 63 * scale;
    var dx = target.x - cx, dy = target.y - cy;
    var dist = Math.hypot(dx, dy) || 1;
    var reach = Math.min(dist / 120, 1) * 3.2;
    pupils.forEach(function (p) {
      p.setAttribute('transform', 'translate(' + (dx / dist * reach).toFixed(2) + ' ' + (dy / dist * reach).toFixed(2) + ')');
    });
    var tilt = Math.max(-6, Math.min(6, dx / 60));
    head.setAttribute('transform', 'rotate(' + tilt.toFixed(2) + ' 80 96)');
  }

  document.addEventListener('pointermove', function (e) {
    target = { x: e.clientX, y: e.clientY };
    if (!queued) { queued = true; requestAnimationFrame(look); }
  });

  function blink() {
    svg.classList.add('blink');
    setTimeout(function () { svg.classList.remove('blink'); }, 140);
  }

  (function idle() {
    setTimeout(function () { if (!document.hidden) blink(); idle(); }, 3000 + Math.random() * 4000);
  })();

  svg.addEventListener('click', function () {
    blink();
    svg.classList.remove('poked');
    void svg.getBoundingClientRect();
    svg.classList.add('poked');
  });
})();
