// Progressive enhancement only: the site works without this file.

(function () {
  var root = document.documentElement;

  // theme toggle (the saved choice is applied by the inline script in <head>, before paint)
  var toggle = document.querySelector('.theme-toggle');
  var themeColor = document.querySelector('meta[name="theme-color"]');

  function syncTheme() {
    var light = root.dataset.theme === 'light';
    if (toggle) toggle.setAttribute('aria-label', light ? 'Switch to dark theme' : 'Switch to light theme');
    if (themeColor) themeColor.setAttribute('content', getComputedStyle(root).getPropertyValue('--bg').trim());
  }

  if (toggle) {
    syncTheme();
    document.addEventListener('prerenderingchange', syncTheme);
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
    function apply(next) {
      root.dataset.theme = next;
      try { localStorage.setItem('theme', next); } catch (e) {}
      syncTheme();
    }
    toggle.addEventListener('click', function () {
      var next = root.dataset.theme === 'light' ? 'dark' : 'light';
      // only where view transitions are mature (Chrome, Edge, Safari); Firefox's still flashes a blank frame here
      var smooth = document.startViewTransition && 'onpagereveal' in window && !reduce.matches;
      if (!smooth) { apply(next); return; }
      // the new theme spreads as a circle from the button
      var r = toggle.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      var radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      root.classList.add('theme-vt');
      var t = document.startViewTransition(function () { apply(next); });
      t.ready.then(function () {
        root.animate(
          { clipPath: ['circle(0px at ' + x + 'px ' + y + 'px)', 'circle(' + radius + 'px at ' + x + 'px ' + y + 'px)'] },
          { duration: 450, easing: 'cubic-bezier(.2, .7, .2, 1)', pseudoElement: '::view-transition-new(root)' }
        );
      });
      t.finished.finally(function () { root.classList.remove('theme-vt'); });
    });
  }

  // mobile menu
  var button = document.querySelector('.menu-btn');
  var nav = document.getElementById('site-nav');
  if (!button || !nav) return;

  button.addEventListener('click', function () {
    var open = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', String(!open));
    nav.classList.toggle('open', !open);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && nav.classList.contains('open')) {
      button.setAttribute('aria-expanded', 'false');
      nav.classList.remove('open');
      button.focus();
    }
  });
})();

// hero highlights: one phrase at a time, paused when the tab is hidden; static with reduced motion
(function () {
  var rotator = document.querySelector('[data-rotator]');
  if (!rotator || !matchMedia('(prefers-reduced-motion: no-preference)').matches) return;
  var items = rotator.children;
  if (items.length < 2) return;
  for (var j = 0; j < items.length; j++) items[j].hidden = false; // every phrase sizes the slot, so nothing shifts
  var i = 0;

  setInterval(function () {
    if (document.hidden || document.documentElement.classList.contains('motion-paused')) return;
    var prev = items[i];
    prev.classList.replace('on', 'out');
    i = (i + 1) % items.length;
    items[i].classList.add('on');
    setTimeout(function () { prev.classList.remove('out'); }, 420);
  }, 3000);
})();

// articles: a copy button on code blocks, and the "On this page" entry for the section being read
(function () {
  var article = document.querySelector('[data-article]');
  if (!article) return;

  if (navigator.clipboard) {
    article.querySelectorAll('.highlight').forEach(function (block) {
      var wrap = document.createElement('div');
      wrap.className = 'code-wrap';
      block.parentNode.insertBefore(wrap, block);
      wrap.appendChild(block);
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'copy';
      button.textContent = 'Copy';
      button.setAttribute('aria-label', 'Copy code');
      wrap.appendChild(button);
      button.addEventListener('click', function () {
        navigator.clipboard.writeText(block.innerText.replace(/\n$/, '')).then(function () {
          button.textContent = 'Copied';
          button.classList.add('done');
          setTimeout(function () { button.textContent = 'Copy'; button.classList.remove('done'); }, 1600);
        });
      });
    });
  }

  var links = document.querySelectorAll('.toc a');
  if (!links.length) return;
  var byId = {};
  links.forEach(function (link) { byId[decodeURIComponent(link.hash.slice(1))] = link; });
  var headings = article.querySelectorAll('h2[id], h3[id]');
  var active = null, queued = false;
  function mark() {
    queued = false;
    // the current section is the last heading that has scrolled above the upper third of the screen
    var current = null;
    headings.forEach(function (h) { if (h.getBoundingClientRect().top < window.innerHeight / 3) current = h; });
    var link = current && byId[current.id];
    if (link === active) return;
    if (active) active.removeAttribute('aria-current');
    if (link) link.setAttribute('aria-current', 'true');
    active = link;
  }
  window.addEventListener('scroll', function () {
    if (!queued) { queued = true; requestAnimationFrame(mark); }
  }, { passive: true });
  mark();
})();

// share: the phone's own share menu where there is one, otherwise "Copy link"
(function () {
  var box = document.querySelector('[data-share]');
  if (!box) return;
  var native = navigator.share && matchMedia('(hover: none)').matches;
  if (!native && !navigator.clipboard) return;
  var item = document.createElement('li');
  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'link link-button';
  button.textContent = native ? 'Share via…' : 'Copy link';
  item.appendChild(button);
  box.querySelector('ul').appendChild(item);
  button.addEventListener('click', function () {
    if (native) {
      navigator.share({ title: box.dataset.title, url: box.dataset.url }).catch(function () {});
      return;
    }
    navigator.clipboard.writeText(box.dataset.url).then(function () {
      button.textContent = 'Link copied';
      setTimeout(function () { button.textContent = 'Copy link'; }, 1600);
    });
  });
})();

// contact form: after a failed submit, put focus on the first field that needs fixing
(function () {
  var invalid = document.querySelector('[data-form] [aria-invalid="true"]');
  if (invalid) invalid.focus();
})();

// search panel: Ctrl/Cmd+K or "/" opens it; the header icon opens it too (without JS it links to /search/)
(function () {
  var dialog = document.querySelector('.search-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  var input = dialog.querySelector('input');
  var results = dialog.querySelector('.search-results');
  var start = results.innerHTML;          // the "Go to" links shown before typing
  var cache = {}, timer = null, pending = null;

  function open() {
    if (dialog.open) return;
    dialog.showModal();
    input.select();
  }

  function show(html) { results.innerHTML = html; }

  function search() {
    var q = input.value.trim();
    if (pending) pending.abort();
    if (q.length < 2) { show(start); return; }
    if (cache[q] !== undefined) { show(cache[q]); return; }
    pending = new AbortController();
    fetch(results.dataset.url + '?panel=1&q=' + encodeURIComponent(q), { signal: pending.signal })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(function (html) { cache[q] = html; show(html); })
      .catch(function (error) {
        if (error.name !== 'AbortError') show('<p class="search-empty">Search is unavailable right now.</p>');
      });
  }

  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(search, 200);
  });

  document.querySelectorAll('.search-btn').forEach(function (link) {
    link.addEventListener('click', function (event) { event.preventDefault(); open(); });
  });

  document.addEventListener('keydown', function (event) {
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName) || event.target.isContentEditable;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      dialog.open ? dialog.close() : open();
    } else if (event.key === '/' && !typing && !dialog.open) {
      event.preventDefault();
      open();
    }
  });

  // arrow keys move between the search box and the results; Enter follows the link
  dialog.addEventListener('keydown', function (event) {
    // one Esc always closes (a search box would otherwise use the first one to clear itself)
    if (event.key === 'Escape') { event.preventDefault(); dialog.close(); return; }
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    var items = [input].concat(Array.prototype.slice.call(results.querySelectorAll('a')));
    var i = items.indexOf(document.activeElement);
    if (i === -1) return;
    event.preventDefault();
    var next = items[Math.max(0, Math.min(items.length - 1, i + (event.key === 'ArrowDown' ? 1 : -1)))];
    next.focus();
  });

  // Enter in the box opens the first result, or the full results page when there are none yet
  dialog.querySelector('form').addEventListener('submit', function (event) {
    var first = results.querySelector('a');
    if (first && input.value.trim().length >= 2) { event.preventDefault(); first.click(); }
  });

  // a click on the dimmed backdrop closes the panel
  dialog.addEventListener('click', function (event) {
    if (event.target === dialog) dialog.close();
  });
})();
