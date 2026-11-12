// pane_methods.js -- the methods block: a table of the functions, classes and constants of the file (see pane_methods.py).
RS.pane('methods', function(ctx){
  RS.doors(ctx.el.querySelector('.doors'), ['methods']);   // its own door, as the ftv has: shut this pane
  var box = ctx.el.querySelector('.methods'), wrap = box.querySelector('.mlist'), cur = '', rows = [], want = '', from = '';    // from: the pane that shows cur
  var tbl = null, picked = [], anchor = null, focused = false, filtering = false, sent = '', info = null;
  var WORD = {green: 'green', '': 'grey', orange: 'orange', red: 'red'};         // the band of a pie, as the word the filter sees
  var COLOURS = ['#1a7f37', '#b0b0b0', '#d98200', '#c0392b'];                      // green, grey, orange, red
  function at(a){ return (8 + 7 * Math.cos(a)).toFixed(2) + ' ' + (8 + 7 * Math.sin(a)).toFixed(2); }
  var DOTS = {red: '#c0392b', orange: '#d98200', grey: '#b0b0b0', green: '#1a7f37'};     // the proof dot: not tested, some tested, all tested but not all reached, all reached
  function pie(shares, dot){            // the pie of an item as svg: four slices from 12 o'clock, clockwise; the proof dot a pie diameter before it
    var total = shares.reduce(function(a, b){ return a + b; }, 0), start = -Math.PI / 2;
    var out = '<svg viewBox="0 0 16 16" width="14" height="14" style="overflow:visible">';       // the pie keeps its size and centre; the dot is drawn outside the box
    if (dot) out += '<circle cx="-8" cy="8" r="2.6" fill="' + DOTS[dot] + '"/>';
    if (!total) out += '<circle cx="8" cy="8" r="6.5" fill="none" stroke="#bbb"/>';
    shares.forEach(function(v, k){
      if (!v) return;
      if (v >= total){ out += '<circle cx="8" cy="8" r="7" fill="' + COLOURS[k] + '"/>'; return; }
      var end = start + 2 * Math.PI * v / total;
      out += '<path d="M8 8 L' + at(start) + ' A7 7 0 ' + (v > total / 2 ? 1 : 0) + ' 1 ' + at(end) + ' Z" fill="' + COLOURS[k] + '"/>';
      start = end;
    });
    return out + '</svg>';
  }
  function frame(){                     // the pie of the file in the header, and the colour of the frame of the pane
    var band = info ? WORD[info.band] : 'none';
    box.className = 'methods band-' + band;
    var head = box.querySelector('.fpie'), score = box.querySelector('.fscore');
    head.innerHTML = info ? pie(info.pie, info.dot) : '';
    head.title = score.title = info ? 'the file: ' + band + ' (score ' + info.score + ')\n' + info.why.join('\n') : '';
    score.textContent = info ? Math.max(1, Math.round(info.score)) + '%' : '';            // green plus half the grey: 1 to 100
  }
  var NAME = 2, OWNER = 3;                              // the columns the status bar's find looks in
  function byName(a, b){
    var A = rows[+a.dataset.i], B = rows[+b.dataset.i];
    return A.owner.localeCompare(B.owner, undefined, {numeric: true}) || A.name.localeCompare(B.name, undefined, {numeric: true});
  }
  function cell(tr, cls, text, v){
    var td = tr.insertCell();
    td.className = cls; td.textContent = text;
    if (v !== undefined) td.dataset.v = v;
    return td;
  }
  function draw(){
    wrap.innerHTML = '';
    tbl = null; picked = []; anchor = null; focused = false; filtering = false;
    frame();
    if (!rows.length){ wrap.innerHTML = '<p class="mute">' + (cur ? 'no methods' : 'no file') + '</p>'; return; }
    var t = document.createElement('table');
    t.className = 'mtab';
    t.innerHTML = '<thead><tr><th class="st" title="the pie of each function and class: green good, grey middle, orange poorish, red very poor. The dot before it, for a name in __all__: red not tested, orange some tested, grey all tested but not all the functions under it reached, green all tested and reached">&#9679;</th>' +
                  '<th>line</th><th>name</th><th>class</th><th>definition</th></tr></thead><tbody></tbody>';
    var tb = t.tBodies[0];
    rows.forEach(function(m, i){
      var tr = tb.insertRow(), word = m.pie ? WORD[m.band] : 'none', st;
      tr.dataset.i = i;
      tr.title = m.kind + ', ' + m.size + ' lines, used ' + m.calls + ' times' + (m.why ? '\n' + m.why.join('\n') : '');
      st = cell(tr, 'st ' + word, '', m.pie ? m.score : -1);
      st.innerHTML = (m.pie ? pie(m.pie, m.dot) : '') + '<span class="w">' + word + '</span>';
      cell(tr, 'lno', m.line, m.line);
      cell(tr, 'nm ' + (m.colour || '') + ' ' + m.kind, m.name);
      cell(tr, 'ow', m.owner);
      cell(tr, 'df', m.text);
    });
    wrap.appendChild(t);
    tbl = RS.table.make(t, {initial: byName, onchange: function(info){ filtering = info.filtering; announce(); }});
    if (want) tbl.setFind(want, [NAME, OWNER]);
  }
  function load(path){
    cur = path;
    return ctx.verb('methods', {path: path}).then(function(r){
      if (cur !== path) return;
      rows = r.ok ? r.methods : [];
      info = r.ok ? r.file : null;
      draw();
      sent = '';
      send(null, false);                                // the pane that shows it is not folded to another file's methods
    }).catch(function(){ rows = []; info = null; draw(); });
  }
  function target(){ return from ? [from] : undefined; }
  function send(ranges, focus){                         // the lines the code pane keeps, or null: the whole file
    var key = JSON.stringify([cur, ranges, focus, from]);
    if (key === sent) return;
    sent = key;
    ctx.emit('showmethods', {path: cur, ranges: ranges, focus: focus, to: target()});
  }
  function rangesOf(trs){                               // the lines of those rows, joined where they touch
    var list = trs.map(function(tr){ var m = rows[+tr.dataset.i]; return [m.top, m.last]; }).sort(function(a, b){ return a[0] - b[0]; });
    var out = [];
    list.forEach(function(r){
      var last = out[out.length - 1];
      if (last && r[0] <= last[1] + 1) last[1] = Math.max(last[1], r[1]); else out.push([r[0], r[1]]);
    });
    return out;
  }
  function visible(){ return tbl ? tbl.rowsAll.filter(function(r){ return !r.classList.contains('nomatch'); }) : []; }
  function announce(){                                  // the code is folded when rows were picked (two or more) or a filter is on
    if (focused) return;
    var chosen = picked.filter(function(tr){ return !tr.classList.contains('nomatch'); });
    send(chosen.length > 1 ? rangesOf(chosen) : filtering ? rangesOf(visible()) : null, false);
  }
  function pick(list){
    picked.forEach(function(tr){ tr.classList.remove('pick'); });
    picked = list;
    picked.forEach(function(tr){ tr.classList.add('pick'); });
  }
  wrap.addEventListener('mousedown', function(e){        // a shift click picks rows: it does not extend a text selection
    if (e.shiftKey){ e.preventDefault(); window.getSelection().removeAllRanges(); }
  });
  wrap.addEventListener('click', function(e){
    var tr = e.target.closest('tbody tr');
    if (!tr) return;
    focused = false;
    if (e.ctrlKey || e.metaKey){                        // one more, or one less
      pick(picked.indexOf(tr) >= 0 ? picked.filter(function(x){ return x !== tr; }) : picked.concat(tr));
      anchor = tr;
    } else if (e.shiftKey && anchor){                   // from the last one clicked to this one, as the list shows them
      var shown = visible(), a = shown.indexOf(anchor), b = shown.indexOf(tr);
      pick(shown.slice(Math.min(a, b), Math.max(a, b) + 1));
    } else {
      pick([tr]); anchor = tr;
      ctx.emit('selectfunk', {lineno: rows[+tr.dataset.i].line, to: target()});
    }
    sent = '';
    announce();
  });
  wrap.addEventListener('dblclick', function(e){        // all the text but this method greyed; again: back
    var tr = e.target.closest('tbody tr');
    if (!tr) return;
    var m = rows[+tr.dataset.i];
    focused = !focused;
    if (focused){ pick([tr]); anchor = tr; send([[m.top, m.last]], true); }
    else { sent = ''; announce(); }
  });
  var h = {
    onShowcode: function(d){              // the file of the pane that was last in front; one that is put behind blanks the list only if it is ours
      if (d.on){ from = d.loc === 'tab' ? '' : d.loc; if (d.path !== cur) load(d.path); }
      else if (d.path === cur && d.loc === (from || 'tab')){ cur = ''; from = ''; rows = []; info = null; draw(); }
    },
    onLinenoClicked: function(d){
      var best = -1;
      rows.forEach(function(m, i){ if (m.line <= d.lineno && (best < 0 || m.line >= rows[best].line)) best = i; });
      Array.prototype.forEach.call(wrap.querySelectorAll('tr.cur'), function(r){ r.classList.remove('cur'); });
      var row = best < 0 ? null : wrap.querySelector('tbody tr[data-i="' + best + '"]');
      if (row){ row.classList.add('cur'); row.scrollIntoView({block: 'nearest'}); }
    },
    onSaved: function(d){ if (d.path === cur) load(cur); },
    onSearchtext: function(d){
      if (d.mode !== 'names') return;
      want = (d.text || '').toLowerCase();
      if (tbl) tbl.setFind(want, [NAME, OWNER]);
    }
  };
  var first = box.dataset.path;
  if (first) ctx.whenLinked(function(){ load(first); });
  return h;
});
