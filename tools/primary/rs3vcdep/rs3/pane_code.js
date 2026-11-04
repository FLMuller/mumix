// pane_code.js -- the code block (see pane_code.py for its signals).
RS.codeSkeleton = '<div class="codeview"><div class="cbar"><span class="cpath">no file</span>' +
  '<button class="cprev" title="previous comment">&#8592;</button><button class="cnext" title="next comment">&#8594;</button></div>' +
  '<div class="clines"><p class="mute">no file open</p></div></div>';
RS.pane('code', function(ctx){
  var view = ctx.el.querySelector('.codeview'), lines = view.querySelector('.clines'),
      cpath = view.querySelector('.cpath'), cur = {path: '', base: ''}, hits = [], at = -1;
  var cfg = ctx.config || {};
  view.style.setProperty('--usercolor', cfg.color || '#e8650f');
  view.style.setProperty('--cfont', cfg.font || 'Consolas');
  view.style.setProperty('--csize', (cfg.size || 12) + 'px');
  view.style.setProperty('--ctab', cfg.tabwidth || 4);
  if (cfg.linenos === false) view.classList.add('nonos');
  var place = '<p class="mute">no file open</p>';

  function wipe(){ lines.innerHTML = place; cpath.textContent = 'no file'; cur = {path: '', base: ''}; hits = []; }
  function load(path, keep){
    var top = lines.scrollTop;
    return ctx.verb('open', {path: path}).then(function(r){
      if (!r.ok){ lines.innerHTML = '<p class="mute">' + (r.error || 'the server would not open it') + '</p>'; return; }
      lines.innerHTML = r.html;
      cur = {path: path, base: r.base};
      cpath.textContent = path.replace(/^\.\//, '');      // direction:rtl would move a leading ./ to the end
      cpath.title = path;
      hits = []; at = -1;
      if (keep) lines.scrollTop = top;
    }).catch(function(e){ lines.innerHTML = '<p class="mute">' + e.message + '</p>'; });
  }
  function lineOf(n){ return lines.querySelector('[data-n="' + n + '"]'); }
  function flash(el){ if (!el) return; el.classList.add('flash'); setTimeout(function(){ el.classList.remove('flash'); }, 1200); }

  lines.addEventListener('click', function(e){
    var cm = e.target.closest('.cm');
    if (cm && cur.path){
      ctx.emit('commentselect', {path: cur.path, base: cur.base, first: +cm.dataset.first, last: +cm.dataset.last,
        tag: cm.dataset.who === 'claude' ? 'cld' : (cm.dataset.initials || cfg.initials || 'user'), text: cm.dataset.md || '', where: ctx.where});
      return;
    }
    var ln = e.target.closest('.ln');
    if (!ln || !(e.target.classList.contains('no') || e.target.classList.contains('mg'))) return;
    var n = +ln.dataset.n;
    ctx.emit('linenoClicked', {lineno: n, where: ctx.where});
    if (cur.path) ctx.emit('commentline', {path: cur.path, base: cur.base, line: n, where: ctx.where});
  });
  function step(dir){                   // the arrows of the bar: from comment to comment
    var all = lines.querySelectorAll('.cm');
    if (!all.length) return;
    var here = lines.scrollTop, pick = null, i;
    if (dir > 0){ for (i = 0; i < all.length; i++) if (all[i].offsetTop > here + 8){ pick = all[i]; break; } }
    else { for (i = all.length - 1; i >= 0; i--) if (all[i].offsetTop < here - 8){ pick = all[i]; break; } }
    if (pick){ lines.scrollTop = pick.offsetTop - 20; flash(pick); }
  }
  view.querySelector('.cprev').onclick = function(){ step(-1); };
  view.querySelector('.cnext').onclick = function(){ step(1); };

  // ---- search: the Highlight API marks the hits without touching the lines' html ----
  function mark(text){
    hits = []; at = -1;
    if (window.CSS && CSS.highlights) CSS.highlights.delete('rs-find');
    if (text){
      var want = text.toLowerCase(), walker = document.createTreeWalker(lines, NodeFilter.SHOW_TEXT), node;
      while ((node = walker.nextNode())){
        if (node.parentElement.closest('.cm') || node.parentElement.classList.contains('no')) continue;
        var low = node.nodeValue.toLowerCase(), from = 0, k;
        while ((k = low.indexOf(want, from)) >= 0){
          var r = document.createRange(); r.setStart(node, k); r.setEnd(node, k + want.length); hits.push(r); from = k + want.length;
        }
      }
      if (window.CSS && CSS.highlights && hits.length) CSS.highlights.set('rs-find', new Highlight(...hits));
    }
    return hits.length;
  }
  function go(dir){
    if (!hits.length) return;
    at = (at + dir + hits.length) % hits.length;
    var el = hits[at].startContainer.parentElement;
    if (el) el.scrollIntoView({block: 'center'});
    ctx.emit('searchcount', {index: at + 1, total: hits.length, where: ctx.where});
  }

  var h = {
    onOpenfile: function(d){
      if (d.path === cur.path) return;
      if (cur.path) ctx.emit('closefile', {path: cur.path, where: ctx.where});    // the old file goes: we say so
      cur = {path: d.path, base: ''};
      load(d.path);
    },
    onClosefile: function(d){ if (d.path === cur.path) wipe(); },
    onSelectfunk: function(d){ var el = lineOf(d.lineno); if (el){ el.scrollIntoView({block: 'start'}); flash(el); } },
    onWithlineno: function(d){ view.classList.toggle('nonos', !d.on); },
    onWithwrap: function(d){ view.classList.toggle('nowrap', !d.on); },
    onSaved: function(d){ if (d.path === cur.path) load(cur.path, true); },
    onSearchtext: function(d){
      if (d.mode !== 'text') return;
      var n = mark(d.text);
      if (n) go(1); else ctx.emit('searchcount', {index: 0, total: 0, where: ctx.where});
    },
    onSearchnext: function(d){ if (d.mode === 'text') go(1); },
    onSearchprev: function(d){ if (d.mode === 'text') go(-1); },
    shown: function(){ if (cur.path) ctx.emit('openfile', {path: cur.path, where: ctx.where}); },   // a tab switch
    remove: function(){ if (cur.path) ctx.emit('closefile', {path: cur.path, where: ctx.where}); cur = {path: '', base: ''}; },
    path: function(){ return cur.path; },
    open: function(path){ cur = {path: path, base: ''}; return load(path); }
  };
  var first = view.dataset.path;
  if (first) ctx.whenLinked(function(){ cur = {path: first, base: ''}; load(first); });
  return h;
});
