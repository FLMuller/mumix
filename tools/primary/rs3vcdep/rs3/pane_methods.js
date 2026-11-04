// pane_methods.js -- the methods block (see pane_methods.py for its signals).
RS.pane('methods', function(ctx){
  var box = ctx.el.querySelector('.methods'), list = box.querySelector('.mlist'), cur = '', rows = [], want = '';
  function esc(t){ return t.replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
  function draw(){
    if (!rows.length){ list.innerHTML = '<p class="mute">' + (cur ? 'no methods' : 'no file') + '</p>'; return; }
    list.innerHTML = rows.map(function(m, i){
      var hide = want && m.name.toLowerCase().indexOf(want) < 0;
      return '<div class="mrow ' + (m.colour || '') + '" data-i="' + i + '"' + (hide ? ' hidden' : '') + ' title="' +
        m.size + ' lines, called ' + m.calls + ' times"><span class="mname">' + esc(m.name) + '</span><span class="mline">' +
        m.line + '</span></div>';
    }).join('');
  }
  function load(path){
    cur = path;
    return ctx.verb('methods', {path: path}).then(function(r){
      if (cur !== path) return;
      rows = r.ok ? r.methods : [];
      draw();
    }).catch(function(){ rows = []; draw(); });
  }
  list.addEventListener('click', function(e){
    var row = e.target.closest('.mrow');
    if (row) ctx.emit('selectfunk', {lineno: rows[+row.dataset.i].line, where: ctx.where});
  });
  var h = {
    onOpenfile: function(d){ if (d.path !== cur) load(d.path); },
    onClosefile: function(d){ if (d.path === cur){ cur = ''; rows = []; draw(); } },
    onLinenoClicked: function(d){
      var best = -1;
      rows.forEach(function(m, i){ if (m.line <= d.lineno && (best < 0 || m.line >= rows[best].line)) best = i; });
      Array.prototype.forEach.call(list.querySelectorAll('.mrow.cur'), function(r){ r.classList.remove('cur'); });
      var row = best < 0 ? null : list.querySelector('.mrow[data-i="' + best + '"]');
      if (row){ row.classList.add('cur'); row.scrollIntoView({block: 'nearest'}); }
    },
    onSaved: function(d){ if (d.path === cur) load(cur); },
    onSearchtext: function(d){ if (d.mode === 'names'){ want = (d.text || '').toLowerCase(); draw(); } }
  };
  var first = box.dataset.path;
  if (first) ctx.whenLinked(function(){ load(first); });
  return h;
});
