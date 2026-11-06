// pane_log.js -- the server's log (see pane_log.py for its signals).
RS.pane('log', function(ctx){
  var MAX = @@MAX@@, box = ctx.el.querySelector('.log'), out = box.querySelector('.llines'),
      count = box.querySelector('.lcount'), follow = box.querySelector('.lfollow'), sort = box.querySelector('.lsort');
  var rows = new Map(), want = '', newest = true;   // row -> [time, text], in the order of arrival; newest: the newest is at the top
  try { newest = localStorage.getItem('rs3.log.newest') !== '0'; } catch (e) {}
  function line(row, t, text){
    var d = document.createElement('div');
    d.className = 'lrow'; d.dataset.row = row;
    d.innerHTML = '<span class="lt"></span><span class="lx"></span>';
    d.firstChild.textContent = t.slice(11); d.firstChild.title = t; d.lastChild.textContent = text;
    if (want && text.toLowerCase().indexOf(want) < 0) d.hidden = true;
    return d;
  }
  function trim(){                      // the oldest line goes: the last one shown newest first, the first one otherwise
    while (rows.size > MAX){
      var oldest = rows.keys().next().value;
      rows.delete(oldest);
      var gone = newest ? out.lastChild : out.firstChild;
      if (gone) out.removeChild(gone);
    }
  }
  function arrow(){ sort.innerHTML = 'time <i class="' + (newest ? 'down' : 'up') + '"></i>'; sort.title = newest ? 'newest first: click for oldest first' : 'oldest first: click for newest first'; }
  function redraw(){
    out.innerHTML = '';
    var frag = document.createDocumentFragment();
    rows.forEach(function(v, row){ newest ? frag.insertBefore(line(row, v[0], v[1]), frag.firstChild) : frag.appendChild(line(row, v[0], v[1])); });
    out.appendChild(frag);
  }
  sort.onclick = function(){
    newest = !newest;
    try { localStorage.setItem('rs3.log.newest', newest ? '1' : '0'); } catch (e) {}
    arrow(); redraw();
    if (follow.checked) out.scrollTop = newest ? 0 : out.scrollHeight;
  };
  arrow();
  return {
    onLog: function(d){
      if (d.reset){ rows.clear(); out.innerHTML = ''; count.textContent = '0 lines'; return; }
      var frag = document.createDocumentFragment();
      d.rows.forEach(function(r){
        rows.set(r[0], [r[1], r[2]]);
        newest ? frag.insertBefore(line(r[0], r[1], r[2]), frag.firstChild) : frag.appendChild(line(r[0], r[1], r[2]));
      });
      if (newest) out.insertBefore(frag, out.firstChild); else out.appendChild(frag);
      trim();
      count.textContent = rows.size + ' lines';
      if (follow.checked) out.scrollTop = newest ? 0 : out.scrollHeight;       // follow: stay where the newest is
    },
    onSearchtext: function(d){ if (d.mode === 'log'){ want = (d.text || '').toLowerCase(); redraw(); } }
  };
});
