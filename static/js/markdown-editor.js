// Admin only: a toolbar and a preview for Markdown fields (textareas with data-markdown).
// It only inserts Markdown; what is saved is still the plain text.
(function () {
  var TOOLS = [
    ['H2', 'Section heading (## text)', function (ed) { ed.prefix('## '); }],
    ['H3', 'Sub-heading (### text)', function (ed) { ed.prefix('### '); }],
    ['B', 'Bold (Ctrl+B)', function (ed) { ed.wrap('**', '**', 'bold text'); }],
    ['I', 'Italic (Ctrl+I)', function (ed) { ed.wrap('*', '*', 'italic text'); }],
    ['Link', 'Link (Ctrl+K)', function (ed) { ed.wrap('[', '](https://)', 'link text', 'https://'); }],
    ['Code', 'Inline code', function (ed) { ed.wrap('`', '`', 'code'); }],
    ['Code block', 'Code block: replace "language" with python, php, bash…', function (ed) { ed.block('```language\n', '\n```', 'code', 'language'); }],
    ['List', 'Bulleted list', function (ed) { ed.prefix('- '); }],
    ['Numbered', 'Numbered list', function (ed) { ed.prefix('1. ', true); }],
    ['Quote', 'Quote', function (ed) { ed.prefix('> '); }],
    ['Image', 'Image: pick one from the library', function (ed) { pickImage(ed); }],
  ];

  function Editor(area) {
    this.area = area;
  }

  // the image picker: one native <dialog> per page, searching the library and inserting an image's Markdown
  var picker;
  function pickImage(ed) {
    var area = ed.area;
    if (!area.dataset.imagesUrl || !window.HTMLDialogElement) {
      ed.wrap('![', '](https://)', 'what the image shows', 'https://');
      return;
    }
    if (!picker) picker = buildPicker();
    picker.editor = ed;
    picker.addLink.href = area.dataset.imageAddUrl;
    picker.url = area.dataset.imagesUrl;
    picker.search.value = '';
    picker.load('');
    picker.dialog.showModal();
    picker.search.focus();
  }

  function buildPicker() {
    var p = {};
    var dialog = p.dialog = document.createElement('dialog');
    dialog.className = 'md-picker';
    dialog.setAttribute('aria-labelledby', 'md-picker-title');
    dialog.innerHTML =
      '<div class="md-picker-head"><h2 id="md-picker-title">Insert an image</h2>' +
      '<button type="button" class="md-picker-close" aria-label="Close">✕</button></div>' +
      '<input type="search" class="md-picker-search" placeholder="Search by alt text" aria-label="Search images">' +
      '<ul class="md-picker-grid" aria-live="polite"></ul>' +
      '<div class="md-picker-foot"><a class="md-picker-add" target="_blank" rel="noopener">Upload a new image ↗</a>' +
      '<button type="button" class="md-picker-manual">Insert by address instead</button></div>';
    document.body.appendChild(dialog);
    p.search = dialog.querySelector('.md-picker-search');
    p.grid = dialog.querySelector('.md-picker-grid');
    p.addLink = dialog.querySelector('.md-picker-add');

    var timer, request;
    p.load = function (text) {
      if (request) request.abort();
      request = new AbortController();
      p.grid.innerHTML = '<li class="md-picker-note">Loading…</li>';
      fetch(p.url + '?q=' + encodeURIComponent(text), { signal: request.signal, credentials: 'same-origin' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (data) { render(data.images); })
        .catch(function (error) {
          if (error.name !== 'AbortError') p.grid.innerHTML = '<li class="md-picker-note">The library could not be loaded.</li>';
        });
    };

    function render(images) {
      p.grid.textContent = '';
      if (!images.length) {
        p.grid.innerHTML = '<li class="md-picker-note">No images yet. Upload one with the link below, then search again.</li>';
        return;
      }
      images.forEach(function (image) {
        var li = document.createElement('li');
        var button = document.createElement('button');
        var img = document.createElement('img');
        var label = document.createElement('span');
        button.type = 'button';
        img.src = image.url;
        img.alt = '';
        img.loading = 'lazy';
        label.textContent = image.alt;
        button.append(img, label);
        button.addEventListener('click', function () { insert(image.markdown); });
        li.appendChild(button);
        p.grid.appendChild(li);
      });
    }

    // on its own line, so Markdown renders it as a block image
    function insert(markdown) {
      var a = p.editor.area, s = a.selectionStart, e = a.selectionEnd;
      var lead = s > 0 && a.value[s - 1] !== '\n' ? '\n\n' : '';
      var out = lead + markdown + '\n';
      dialog.close();
      p.editor.replace(s, e, out, out.length, out.length);
    }

    p.search.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { p.load(p.search.value.trim()); }, 200);
    });
    dialog.querySelector('.md-picker-close').addEventListener('click', function () { dialog.close(); });
    dialog.querySelector('.md-picker-manual').addEventListener('click', function () {
      dialog.close();
      p.editor.wrap('![', '](https://)', 'what the image shows', 'https://');
    });
    // a click on the backdrop closes it
    dialog.addEventListener('click', function (event) { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener('close', function () { p.editor.area.focus(); });
    return p;
  }

  // insertText keeps Ctrl+Z working; setRangeText is the fallback
  Editor.prototype.replace = function (start, end, text, selStart, selEnd) {
    var area = this.area;
    area.focus();
    area.setSelectionRange(start, end);
    if (!document.execCommand('insertText', false, text)) {
      area.setRangeText(text, start, end, 'end');
      area.dispatchEvent(new Event('input', { bubbles: true }));
    }
    area.setSelectionRange(start + selStart, start + selEnd);
  };

  // wrap the selection, or a placeholder; `select` picks what to leave selected afterwards
  Editor.prototype.wrap = function (before, after, placeholder, select) {
    var a = this.area, s = a.selectionStart, e = a.selectionEnd;
    var text = a.value.slice(s, e) || placeholder;
    var out = before + text + after;
    if (select && a.value.slice(s, e)) {
      var at = out.indexOf(select, before.length + text.length);
      this.replace(s, e, out, at, at + select.length);
    } else {
      this.replace(s, e, out, before.length, before.length + text.length);
    }
  };

  // a fenced block on its own lines
  Editor.prototype.block = function (before, after, placeholder, select) {
    var a = this.area, s = a.selectionStart, e = a.selectionEnd;
    var lead = s > 0 && a.value[s - 1] !== '\n' ? '\n\n' : '';
    var text = a.value.slice(s, e) || placeholder;
    var out = lead + before + text + after + '\n';
    var at = out.indexOf(select);
    this.replace(s, e, out, at, at + select.length);
  };

  // add (or remove, when every line has it) a prefix on each selected line
  Editor.prototype.prefix = function (mark, numbered) {
    var a = this.area;
    var s = a.value.lastIndexOf('\n', a.selectionStart - 1) + 1;
    var e = a.value.indexOf('\n', a.selectionEnd);
    if (e === -1) e = a.value.length;
    var lines = a.value.slice(s, e).split('\n');
    var pattern = numbered ? /^\d+\. / : new RegExp('^' + mark.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    var undo = lines.every(function (line) { return pattern.test(line); });
    var out = lines.map(function (line, i) {
      if (undo) return line.replace(pattern, '');
      var clean = line.replace(/^(#{1,6} |> |- |\d+\. )/, '');
      return (numbered ? (i + 1) + '. ' : mark) + clean;
    }).join('\n');
    this.replace(s, e, out, out.length, out.length);
  };

  Editor.prototype.inCodeBlock = function () {
    var before = this.area.value.slice(0, this.area.selectionStart);
    return ((before.match(/^```/gm) || []).length % 2) === 1;
  };

  function setup(area) {
    var ed = new Editor(area);
    var bar = document.createElement('div');
    bar.className = 'md-toolbar';
    bar.setAttribute('role', 'toolbar');
    bar.setAttribute('aria-label', 'Formatting');

    TOOLS.forEach(function (tool) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = tool[0];
      b.title = tool[1];
      b.setAttribute('aria-label', tool[1]);
      b.addEventListener('click', function () { if (!area.hidden) tool[2](ed); });
      bar.appendChild(b);
    });

    var tabs = document.createElement('div');
    tabs.className = 'md-tabs';
    var write = document.createElement('button');
    var view = document.createElement('button');
    write.type = view.type = 'button';
    write.textContent = 'Write';
    view.textContent = 'Preview';
    write.setAttribute('aria-pressed', 'true');
    view.setAttribute('aria-pressed', 'false');
    tabs.append(write, view);
    bar.appendChild(tabs);

    var preview = document.createElement('div');
    preview.className = 'md-preview';
    preview.hidden = true;
    preview.setAttribute('aria-live', 'polite');

    // one block, so admin's flex rows keep the toolbar above the text
    var box = document.createElement('div');
    box.className = 'md-editor';
    area.parentNode.insertBefore(box, area);
    box.append(bar, area, preview);

    function show(previewing) {
      area.hidden = previewing;
      preview.hidden = !previewing;
      write.setAttribute('aria-pressed', String(!previewing));
      view.setAttribute('aria-pressed', String(previewing));
      bar.classList.toggle('previewing', previewing);
      if (!previewing) { area.focus(); return; }
      preview.style.minHeight = area.offsetHeight + 'px';
      preview.textContent = 'Rendering…';
      var body = new FormData();
      body.append('text', area.value);
      var token = area.form && area.form.querySelector('[name=csrfmiddlewaretoken]');
      fetch(area.dataset.previewUrl, {
        method: 'POST', body: body, credentials: 'same-origin',
        headers: { 'X-CSRFToken': token ? token.value : '' },
      }).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.text();
      }).then(function (html) {
        preview.innerHTML = html || '<p class="md-empty">Nothing to preview yet.</p>';
      }).catch(function () {
        preview.textContent = 'The preview could not be loaded. Your text is unchanged.';
      });
    }
    write.addEventListener('click', function () { show(false); });
    view.addEventListener('click', function () { show(true); });

    area.addEventListener('keydown', function (event) {
      var key = event.key.toLowerCase();
      if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey) {
        if (key === 'b') { event.preventDefault(); TOOLS[2][2](ed); }
        else if (key === 'i') { event.preventDefault(); TOOLS[3][2](ed); }
        else if (key === 'k') { event.preventDefault(); TOOLS[4][2](ed); }
      }
      // Tab indents only inside a code block; elsewhere it moves focus as usual
      if (key === 'tab' && !event.shiftKey && !event.ctrlKey && ed.inCodeBlock()) {
        event.preventDefault();
        ed.replace(area.selectionStart, area.selectionEnd, '    ', 4, 4);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('textarea[data-markdown]').forEach(setup);
  });
})();
