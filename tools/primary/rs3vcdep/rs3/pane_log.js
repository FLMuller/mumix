// pane_log.js -- the server's log (see pane_log.py for its signals).
RS.pane('log', function(ctx){
  var MAX = @@MAX@@, box = ctx.el.querySelector('.log'), out = box.querySelector('.llines'),
      count = box.querySelector('.lcount'), follow = box.querySelector('.lfollow');
  var rows = new Map(), want = '';                  // row -> [time, text]; a Map keeps the order of arrival
  function line(row, t, text){
    var d = document.createElement('div');
    d.className = 'lrow'; d.dataset.row = row;
    d.innerHTML = '<span class="lt"></span><span class="lx"></span>';
    d.firstChild.textContent = t.slice(11); d.firstChild.title = t; d.lastChild.textContent = text;
    if (want && text.toLowerCase().indexOf(want) < 0) d.hidden = true;
    return d;
  }
  function trim(){
    while (rows.size > MAX){
      var oldest = rows.keys().next().value;
      rows.delete(oldest);
      if (out.firstChild) out.removeChild(out.firstChild);
    }
  }
  function redraw(){
    out.innerHTML = '';
    var frag = document.createDocumentFragment();
    rows.forEach(function(v, row){ frag.appendChild(line(row, v[0], v[1])); });
    out.appendChild(frag);
  }
  return {
    onLog: function(d){
      if (d.reset){ rows.clear(); out.innerHTML = ''; count.textContent = '0 lines'; return; }
      var frag = document.createDocumentFragment();
      d.rows.forEach(function(r){ rows.set(r[0], [r[1], r[2]]); frag.appendChild(line(r[0], r[1], r[2])); });
      out.appendChild(frag);
      trim();
      count.textContent = rows.size + ' lines';
      if (follow.checked) ctx.el.scrollTop = ctx.el.scrollHeight;
    },
    onSearchtext: function(d){ if (d.mode === 'log'){ want = (d.text || '').toLowerCase(); redraw(); } }
  };
});
