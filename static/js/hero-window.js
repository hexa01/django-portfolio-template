// Hero "systems" window: request traces, auto-switching, swipe/keys, design notes.
// Progressive enhancement: without JS the first diagram shows as a static picture.
(function () {
  var win = document.querySelector('[data-hw]');
  if (!win) return;

  // Each diagram plays one or more runs; each run is an ordered list of steps.
  // A step lists what happens at once: node ids light up, edge ids carry a packet
  // ("<id" means the packet travels the edge backwards, i.e. a reply).
  var RUNS = {
    web: [
      { req: 'GET /orders/42', out: 'cache hit',
        steps: [['lb'], ['lb-api', 'api'], ['api-redis', 'redis'], ['<api-redis'], ['<lb-api', 'lb']] },
      { req: 'GET /orders/42', out: 'cache miss',
        steps: [['lb'], ['lb-api', 'api'], ['api-redis', 'redis'], ['<api-redis'],
                ['api-pg', 'pg'], ['<api-pg'], ['api-redis'],                                   // read the primary, then fill the cache
                ['<lb-api', 'lb']] },
      { req: 'POST /orders', out: 'write',
        steps: [['lb'], ['lb-api', 'api'], ['api-pg', 'pg'], ['<api-pg', 'pg-replica', 'replica'], // replica syncs async
                ['api-redis', 'redis'],                                                         // invalidate the cached order
                ['api-queue', 'queue'], ['<lb-api', 'lb', 'queue-workers', 'workers']] }         // respond now, work runs in the background
    ],
    rag: [
      { req: 'ingest', out: 'docs changed',
        steps: [['docs'], ['docs-embed', 'embed'], ['embed-pg', 'pgvector']] },
      { req: 'POST /ask', out: 'cache miss',
        steps: [['user'], ['user-cache', 'cache'], ['cache-retrieve', 'retrieve'],
                ['retrieve-pg', 'pgvector'], ['<retrieve-pg'],
                ['retrieve-rerank', 'rerank'], ['rerank-llm', 'llm'], ['response', 'user']] },
      { req: 'POST /ask', out: 'cache hit',
        steps: [['user'], ['user-cache', 'cache'], ['hit', 'user']] }
    ],
    events: [
      { req: 'order.created #42', out: 'p1, processed',
        steps: [['producer'], ['prod-topic', 'topic', 'p1'], ['p1-c1', 'c1'], ['c1-pg', 'pg']] },
      { req: 'order.created #17', out: 'p2, processed',
        steps: [['producer'], ['prod-topic', 'topic', 'p2'], ['p2-c2', 'c2'], ['c2-pg', 'pg']] },
      { req: 'order.created #88', out: 'p0, fails, retried',
        steps: [['producer'], ['prod-topic', 'topic', 'p0'], ['p0-c0', 'c0'],
                ['group-dlq', 'dlq'], ['retry', 'topic', 'p0'], ['p0-c0', 'c0'], ['c0-pg', 'pg']] }
    ],
    code: [
      { req: 'POST /ask', out: 'cache miss',
        steps: [['l0', 'l1'], ['l2'], ['l4'], ['l5'], ['l6'], ['l7'], ['l8'], ['l9']] },
      { req: 'POST /ask', out: 'cache hit',
        steps: [['l0', 'l1'], ['l2'], ['l3']] }
    ]
  };

  var DRAW = 850, STEP = 600, CODE_STEP = 450, HOLD = 700, GAP = 500;
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var stage = win.querySelector('.hw-stage');
  var scenes = win.querySelectorAll('.hw-scene');
  var buttons = win.querySelectorAll('[data-go]');
  var address = win.querySelector('[data-hw-address]');
  var pauseBtn = win.querySelector('.hw-pause');
  var reqLine = win.querySelector('[data-hw-req]');
  var outLine = win.querySelector('[data-hw-out]');
  var infoName = win.querySelector('[data-hw-info-name]');
  var infoText = win.querySelector('[data-hw-info-text]');
  var hint = infoText.textContent;
  var current = 0, timer = null, paused = false, held = false, playId = 0;

  // solid edges get a normalised length so the draw-in covers any path length
  win.querySelectorAll('.edge:not(.dash)').forEach(function (p) { p.setAttribute('pathLength', '1'); });
  // static highlights only make sense without the live trace; with it they'd suggest a step that hasn't happened
  if (!reduce) win.querySelectorAll('.edge-hot, .node-hot').forEach(function (el) { el.classList.remove('edge-hot', 'node-hot'); });

  // only animate while someone can see it: not off-screen or in a background tab
  var onScreen = true, live = false;
  function visible() { return onScreen && !document.hidden; }
  function running() { return !reduce && !paused && !held && visible(); }
  // portrait phones draw the portrait version of each diagram (see hero-window.css)
  var small = window.matchMedia('(max-width: 519px)'); // keep in sync with hero-window.css
  function stepTime(scene) { return scene.dataset.key === 'code' ? CODE_STEP : STEP; }
  // Each view keeps its own place (which story, which step), so switching away and back
  // continues the flow instead of restarting it. The draw-in plays only the first time.
  var progress = {};
  // no draw-in when returning to the page in the same session (.intro is only set on the first view)
  var intro = document.documentElement.classList.contains('intro');
  scenes.forEach(function (sc) { progress[sc.dataset.key] = { run: 0, step: 0, drawn: !intro }; });

  // auto-switch after about 10s, but always at the end of a story so no request is cut off mid-flow
  var MIN_VIEW = 10000;
  function runTime(scene, run) { return run.steps.length * stepTime(scene) + HOLD + GAP; }
  function switchTime(scene) {
    var p = progress[scene.dataset.key], runs = RUNS[scene.dataset.key], st = stepTime(scene);
    var t = (p.drawn ? 0 : DRAW) + (runs[p.run % runs.length].steps.length - p.step) * st + HOLD + GAP;
    for (var r = p.run + 1; t < MIN_VIEW; r++) t += runTime(scene, runs[r % runs.length]);
    return t;
  }

  function show(i) {
    current = (i + scenes.length) % scenes.length;
    var scene = scenes[current], p = progress[scene.dataset.key];
    scenes.forEach(function (s, n) { s.classList.toggle('on', n === current); });
    if (!p.drawn && !reduce && visible()) {
      scene.classList.remove('play');
      void scene.offsetWidth; // start the draw-in
      scene.classList.add('play');
    }
    buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(Number(b.dataset.go) === current)); });
    address.textContent = scene.dataset.title;
    select(null);
    restart(); // uses this view's saved place, so compute before playback moves it
    play(scene);
  }

  // --- trace playback ---
  function clearTrace() {
    win.querySelectorAll('.lit, .current').forEach(function (el) { el.classList.remove('lit', 'current'); });
    win.querySelectorAll('.packet').forEach(function (el) { el.remove(); });
  }

  function play(scene) {
    var id = ++playId;
    clearTrace();
    reqLine.textContent = '';
    outLine.textContent = '';
    if (reduce || paused || !visible()) return;
    var key = scene.dataset.key, runs = RUNS[key], st = stepTime(scene), p = progress[key];
    var layout = scene.querySelector(small.matches ? '.d-tall' : '.d-wide') || scene;
    function find(k) { return layout.querySelector('[data-id="' + k + '"]'); }
    function each(step, fn) {
      step.forEach(function (k) {
        var back = k.charAt(0) === '<', el = find(back ? k.slice(1) : k);
        if (el) fn(el, back);
      });
    }

    function runFrom(delay) {
      if (id !== playId) return;
      var run = runs[p.run % runs.length], from = p.step;
      reqLine.textContent = run.req;
      outLine.textContent = run.out;
      // resuming mid-story: restore what was already lit, without replaying it
      for (var k = 0; k < from; k++) each(run.steps[k], function (el) { el.classList.add('lit'); });
      run.steps.slice(from).forEach(function (step, j) {
        setTimeout(function () {
          if (id !== playId) return;
          p.step = from + j + 1;
          scene.querySelectorAll('.current').forEach(function (el) { el.classList.remove('current'); });
          each(step, function (el, back) {
            if (el.tagName === 'path') travel(el, st - 80, id, back);
            else {
              el.classList.add('lit');
              if (el.classList.contains('hw-line')) el.classList.add('current');
            }
          });
        }, delay + j * st);
      });
      setTimeout(function () {
        if (id !== playId) return;
        clearTrace();
        p.run += 1;
        p.step = 0;
        setTimeout(function () { runFrom(0); }, GAP); // next story, looping
      }, delay + (run.steps.length - from) * st + HOLD);
    }
    var delay = p.drawn ? 0 : DRAW;
    p.drawn = true;
    runFrom(delay);
  }

  function travel(path, duration, id, back) {
    var svg = path.ownerSVGElement, length = path.getTotalLength();
    var dot = document.createElementNS(SVG_NS, 'circle');
    dot.setAttribute('r', '3');
    dot.setAttribute('class', 'packet');
    svg.appendChild(dot);
    path.classList.add('lit');
    var start = null;
    function frame(now) {
      if (id !== playId) { dot.remove(); return; }
      if (start === null) start = now;
      var k = Math.min((now - start) / duration, 1);
      var eased = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      var p = path.getPointAtLength((back ? 1 - eased : eased) * length);
      dot.setAttribute('cx', p.x);
      dot.setAttribute('cy', p.y);
      if (k < 1) requestAnimationFrame(frame); else dot.remove();
    }
    requestAnimationFrame(frame);
  }

  // --- auto-switch (see switchTime); pause, hover or focus keeps the current view ---
  function restart() {
    clearTimeout(timer);
    win.classList.remove('running'); void win.offsetWidth;
    if (!running()) return;
    var t = switchTime(scenes[current]);
    win.style.setProperty('--hw-cycle', t + 'ms');
    win.classList.add('running');
    timer = setTimeout(function () { show(current + 1); }, t);
  }

  buttons.forEach(function (b) { b.addEventListener('click', function () { show(Number(b.dataset.go)); }); });

  pauseBtn.addEventListener('click', function () {
    // pauses all hero motion: the trace, view switching and the highlights (site.js reads the class)
    paused = !paused;
    pauseBtn.setAttribute('aria-pressed', String(paused));
    pauseBtn.setAttribute('aria-label', paused ? 'Play animation' : 'Pause animation');
    document.documentElement.classList.toggle('motion-paused', paused);
    if (paused) { playId++; clearTrace(); clearTimeout(timer); win.classList.remove('running'); }
    else show(current);
  });

  function hold(h) { held = h; restart(); }
  win.addEventListener('mouseenter', function () { hold(true); });
  win.addEventListener('mouseleave', function () { hold(false); });
  win.addEventListener('focusin', function () { hold(true); });
  win.addEventListener('focusout', function (e) { if (!win.contains(e.relatedTarget)) hold(false); });

  // --- design notes ---
  win.querySelectorAll('[data-info]').forEach(function (el) {
    el.setAttribute('tabindex', '0');
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', el.dataset.name);
  });
  function select(el) {
    win.querySelectorAll('.sel').forEach(function (x) { x.classList.remove('sel'); });
    if (!el) { infoName.textContent = ''; infoText.textContent = hint; return; }
    el.classList.add('sel');
    infoName.textContent = el.dataset.name;
    infoText.textContent = el.dataset.info;
  }

  // --- swipe / drag, click to select ---
  var sx = 0, sy = 0, pid = null, swiped = false;
  stage.addEventListener('pointerdown', function (e) { pid = e.pointerId; sx = e.clientX; sy = e.clientY; swiped = false; });
  stage.addEventListener('pointerup', function (e) {
    if (e.pointerId !== pid) return;
    pid = null;
    var dx = e.clientX - sx, dy = e.clientY - sy;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.2) { swiped = true; show(current + (dx < 0 ? 1 : -1)); }
  });
  stage.addEventListener('pointercancel', function () { pid = null; });
  stage.addEventListener('click', function (e) {
    if (swiped) { swiped = false; return; }
    var el = e.target.closest('[data-info]');
    if (el) select(el);
  });

  // --- keyboard: arrows switch, Enter/Space selects ---
  win.addEventListener('keydown', function (e) {
    var el = e.target.closest && e.target.closest('[data-info]');
    if (el && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); select(el); return; }
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); show(current + 1); }
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); show(current - 1); }
  });

  function sync() {
    var now = visible();
    if (now === live) return;
    live = now;
    if (now) { show(current); return; }
    playId++; // stops the trace loop
    clearTrace();
    clearTimeout(timer);
    win.classList.remove('running');
  }
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) { onScreen = entries[0].isIntersecting; sync(); }).observe(win);
  }
  document.addEventListener('visibilitychange', sync);
  if (small.addEventListener) small.addEventListener('change', function () { show(current); });

  show(0);
  live = visible();
})();
