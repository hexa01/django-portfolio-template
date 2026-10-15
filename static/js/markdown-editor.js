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
    ['Image', 'Image: describe it, then paste its address', function (ed) { ed.wrap('![', '](https://)', 'what the image shows', 'https://'); }],
  ];

  function Editor(area) {
    this.area = area;
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
