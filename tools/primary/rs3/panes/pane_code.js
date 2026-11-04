// pane_code.js -- the code block (see pane_code.py for its signals).
RS.codeSkeleton = '<div class="codeview"><div class="cbar"><span class="cpath">no file</span>' +
  '<button class="cprev" title="previous comment">&#8592;</button><button class="cnext" title="next comment">&#8594;</button></div>' +
  '<div class="clines"><p class="mute">no file open</p></div></div>';
RS.pane('code', function(ctx){
  var view = ctx.el.querySelector('.codeview'), lines = view.querySelector('.clines'),
      cpath = view.querySelector('.cpath'), cur = {path: '', base: ''}, hits = [], at = -1;
  var cfg = ctx.config || {};
  var place = '<p class="mute">no file open</p>';

  var chosen = null;                    // the line that was clicked: the whole row is marked until a scroll or a click elsewhere
  function away(e){      // not a line of this pane, and not a block that keeps it (data-keepsel: the comment box is for that line)
    if (!(lines.contains(e.target) && e.target.closest('.ln')) && !e.target.closest('[data-keepsel]')) choose(null);
  }
  function choose(row){
    if (chosen) chosen.classList.remove('sel');
    chosen = row;
    if (row) row.classList.add('sel');
    document[row ? 'addEventListener' : 'removeEventListener']('click', away);       // (only while a line is chosen: every tab has a code pane)
  }
  lines.addEventListener('scroll', function(){ if (chosen) choose(null); });
  function wipe(){ choose(null); lines.innerHTML = place; cpath.textContent = 'no file'; cur = {path: '', base: ''}; hits = []; }
  function load(path, keep){
    var top = lines.scrollTop;
    return ctx.verb('open', {path: path}).then(function(r){
      if (!r.ok){ lines.innerHTML = '<p class="mute">' + (r.error || 'the server would not open it') + '</p>'; return; }
      choose(null);
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
        tag: cm.dataset.who === 'claude' ? 'cld' : (cm.dataset.initials || cfg.initials || 'user'), text: cm.dataset.md || ''});
      return;
    }
    var ln = e.target.closest('.ln');
    if (!ln || !ln.dataset.n) return;
    var n = +ln.dataset.n;
    choose(ln);                         // a click anywhere on the line marks it, and methods follows it ...
    ctx.emit('linenoClicked', {lineno: n});
    var numbered = e.target.classList.contains('no') || e.target.classList.contains('mg');
    if (cur.path && (numbered || !String(window.getSelection()).length))           // ... and asks for a comment (not after text was selected: the comment box would take the focus from a copy)
      ctx.emit('commentline', {path: cur.path, base: cur.base, line: n});
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
    ctx.emit('searchcount', {index: at + 1, total: hits.length});
  }
  function say(on){ if (cur.path) ctx.emit('showcode', {path: cur.path, loc: ctx.loc, on: on}); }    // this file is shown, or no longer

  var h = {
    onShowfile: function(d){
      if (d.show === false){ if (d.path === cur.path){ say(false); wipe(); } return; }
      if (d.path === cur.path){ say(true); return; }
      say(false);                                         // the old file goes: we say so
      cur = {path: d.path, base: ''};
      load(d.path);
      say(true);
    },
    onSelectfunk: function(d){ var el = lineOf(d.lineno); if (el){ el.scrollIntoView({block: 'start'}); flash(el); } },
    onSaved: function(d){ if (d.path === cur.path) load(cur.path, true); },
    onSearchtext: function(d){
      if (d.mode !== 'text') return;
      var n = mark(d.text);
      if (n) go(1); else ctx.emit('searchcount', {index: 0, total: 0});
    },
    onSearchnext: function(d){ if (d.mode === 'text') go(1); },
    onSearchprev: function(d){ if (d.mode === 'text') go(-1); },
    shown: function(){ say(true); },                      // a tab switch: this one is in front
    hidden: function(){ say(false); },                    // ... and this one is behind
    remove: function(){ say(false); cur = {path: '', base: ''}; },
    path: function(){ return cur.path; },
    open: function(path){ cur = {path: path, base: ''}; say(true); return load(path); }
  };
  var first = view.dataset.path;
  if (first) ctx.whenLinked(function(){ cur = {path: first, base: ''}; load(first); say(true); });
  return h;
});
