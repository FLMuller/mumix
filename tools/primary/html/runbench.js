var KEY = 'report:' + STEM;                    // what is remembered, per report name
function store(name, value){ try { localStorage.setItem(KEY + ':' + name, JSON.stringify(value)); } catch(e){} }
function recall(name, dflt){
  try { var v = localStorage.getItem(KEY + ':' + name); return v === null ? dflt : JSON.parse(v); }
  catch(e){ return dflt; }
}
function hiddenSet(){ return new Set(recall('hidden', [])); }
function tabId(name){ return 't_' + String(name).replace(/\W+/g, '_').replace(/^_+|_+$/g, ''); }
// The page holds a div for each tab (class mk-tab, its name in data-name), and inside it a div
// for each sub-tab. This makes the buttons: the row of tabs, and a row of sub-tabs in a tab.
function buildTabs(){
  var strip = document.getElementById('tabStrip');
  strip.innerHTML = '';
  var seen = {};
  Array.prototype.slice.call(document.getElementById('panels').children).forEach(function(div){
    if (!div.classList.contains('mk-tab')) return;
    var name = div.dataset.name, id = tabId(name);
    while (seen[id]) id += '_';
    seen[id] = true;
    var bad = div.classList.contains('bad');
    var btn = document.createElement('button');
    btn.className = 'tbtn' + (bad ? ' bad' : '');
    btn.id = 'btn_' + id;
    btn.onclick = function(){ selTab(id); };
    btn.appendChild(document.createTextNode(name));
    var x = document.createElement('span');
    x.className = 'tclose'; x.title = 'hide tab'; x.innerHTML = '&#10005;';
    x.onclick = function(e){ e.stopPropagation(); closeTab(id); };
    btn.appendChild(x);
    strip.appendChild(btn);
    div.id = id;
    div.className = 'tpanel';
    var subs = Array.prototype.filter.call(div.children, function(c){ return c.classList.contains('mk-tab'); });
    if (!subs.length) return;
    var bar = document.createElement('div');
    bar.className = 'subtabs';
    subs.forEach(function(s, k){
      var b = document.createElement('button');
      b.className = 'stab' + (k ? '' : ' on') + (s.classList.contains('bad') ? ' bad' : '');
      b.textContent = s.dataset.name;
      b.onclick = function(){ sub(b, s.dataset.name); };
      bar.appendChild(b);
      s.className = 'spane' + (k ? '' : ' on');
    });
    div.insertBefore(bar, subs[0]);
  });
}
function allBtns(){ return Array.prototype.slice.call(document.querySelectorAll('.tbtn')); }
function visBtns(){ return allBtns().filter(function(b){ return b.style.display !== 'none'; }); }
function tabIdOf(b){ return b.id.replace(/^btn_/, ''); }
function labelOf(b){ return b.childNodes[0].textContent.trim(); }

function selTab(id){
  document.querySelectorAll('.tpanel').forEach(function(p){ p.classList.remove('active'); });
  document.querySelectorAll('.tbtn').forEach(function(b){ b.classList.remove('active'); });
  document.getElementById(id).classList.add('active');
  var b = document.getElementById('btn_' + id);
  b.classList.add('active');
  b.scrollIntoView({inline:'nearest', block:'nearest'});
  store('tab', id);
}
function closeTab(id){
  var s = hiddenSet(); s.add(id); store('hidden', Array.from(s));
  var btn = document.getElementById('btn_' + id);
  var idx = visBtns().indexOf(btn);
  var wasActive = btn.classList.contains('active');
  btn.style.display = 'none';
  document.getElementById(id).classList.remove('active');
  if (wasActive){
    var rest = visBtns();
    if (rest.length) selTab(tabIdOf(idx > 0 ? rest[idx-1] : rest[0]));
  }
  buildCombo();
}
function comboSel(id){
  if (!id) return;
  var btn = document.getElementById('btn_' + id);
  if (btn.style.display === 'none'){
    var s = hiddenSet(); if (s.delete(id)) store('hidden', Array.from(s));
    var act = document.querySelector('.tbtn.active');
    if (act && act !== btn) act.after(btn);
    btn.style.display = '';
  }
  selTab(id);
  document.getElementById('tabCombo').selectedIndex = 0;
  buildCombo();
}
var holdTimer = null, holdIv = null, didHold = false;
function holdStart(d){
  didHold = false;
  holdTimer = setTimeout(function(){
    didHold = true;
    holdIv = setInterval(function(){ document.getElementById('tabStrip').scrollBy({left: d*6}); }, 16);
  }, 350);
}
function holdEnd(d){
  clearTimeout(holdTimer);
  if (holdIv){ clearInterval(holdIv); holdIv = null; }
  else if (!didHold && d !== undefined){
    var vis = visBtns();
    var w = vis.length ? vis[0].offsetWidth + 4 : 120;
    document.getElementById('tabStrip').scrollBy({left: d*w, behavior:'smooth'});
  }
}
function buildCombo(){
  var c = document.getElementById('tabCombo');
  c.innerHTML = '<option value="">tabs&hellip;</option>';
  allBtns().forEach(function(b){
    var o = document.createElement('option');
    o.value = tabIdOf(b);
    o.textContent = (b.style.display === 'none' ? '· ' : '') + labelOf(b);
    c.appendChild(o);
  });
}
function sub(btn, name){
  var panel = btn.closest('.tpanel');
  panel.querySelectorAll('.stab').forEach(function(b){ b.classList.toggle('on', b === btn); });
  panel.querySelectorAll('.spane').forEach(function(p){ p.classList.toggle('on', p.dataset.name === name); });
}

// ---- the reports of this series, and the report server ----
// The report server (reportserver.py) lists the other reports of this series and sends the tabs
// of the one chosen; the page swaps them in, so no file has to be opened. Without the server the
// dropdown still lists the names written with this file, and choosing another says how to start
// the server. SELF is this file's name, TOKEN proves who is asking (see reportserver.py).
var BOOK = {};                  // the tabs of each report seen: file name -> {html, title}
var ws = null, waiting = null, current = SELF;
// One colour per report of the series, so a change of file is seen at once. The set keeps
// off red (red means "no server"), clear of the cream footer (3:1 or better) and far apart.
var TINTS = ['#2F6FE0', '#DD5A08', '#1B8F33', '#E0338C', '#8E22E0', '#A87C00',   // vivid only: no
             '#0C8FA0', '#C62BE8', '#5E9400', '#3B3BD6', '#0E937A', '#0F86D6'];   // greys, browns, blacks
var PING_EVERY = 20000, PONG_WITHIN = 5000, pongTimer = null;
var upNow = false, busyNow = false;       // as pypanes: red disc down, a pulse up, a turn while busy
function showLive(){ document.getElementById('live').setAttribute('data-live', !upNow ? 'disc' : busyNow ? 'spin' : 'pulse'); }
function setLive(up){ upNow = up; if (!up) busyNow = false; showLive(); }
function tintOf(names, name){ return TINTS[Math.max(0, names.indexOf(name)) % TINTS.length]; }
function tint(){
  var sel = document.getElementById('runs');
  var opts = Array.prototype.slice.call(sel.options);
  var names = opts.map(function(o){ return o.value; }).sort();   // oldest first: a new report never recolours the others
  opts.forEach(function(o){ o.style.color = tintOf(names, o.value); o.style.fontWeight = 'bold'; });
  var now = tintOf(names, current);
  sel.style.color = now;
  document.getElementById('live').style.setProperty('--tint', now);
  var h = document.querySelector('h1');
  if (h) h.style.color = now;
}
function pulse(){
  if (ws && ws.readyState === 1){
    ws.send(JSON.stringify({hash: TOKEN, ping: 1}));
    clearTimeout(pongTimer);
    pongTimer = setTimeout(function(){ if (ws) ws.close(); }, PONG_WITHIN);
  } else if (PORT) connect();
}
function noServer(){
  setLive(false);
  var s = document.getElementById('srv');
  s.textContent = 'report server not running: start ';
  var c = document.createElement('code');
  c.textContent = BAT || 'reportserver.bat';
  c.title = 'paste into Win+R or the Explorer address bar';
  s.appendChild(c);
}
function fillRuns(names){
  var sel = document.getElementById('runs');
  sel.innerHTML = '';
  [SELF].concat(names.filter(function(n){ return n !== SELF; })).forEach(function(n){
    var o = document.createElement('option');
    o.value = n; o.textContent = n;
    sel.appendChild(o);
  });
  sel.value = current;
  tint();
}
function connect(then){
  if (!PORT){ noServer(); return; }
  var sock;
  try { sock = new WebSocket('ws://127.0.0.1:' + PORT); } catch(e){ noServer(); return; }
  var timer = setTimeout(function(){ if (sock.readyState === 0){ sock.close(); noServer(); } }, 1500);
  sock.onopen = function(){ clearTimeout(timer); ws = sock; document.getElementById('srv').textContent = ''; setLive(true); if (then) then(); };
  sock.onerror = function(){ clearTimeout(timer); if (ws !== sock) noServer(); };
  sock.onclose = function(){ if (ws === sock){ ws = null; clearTimeout(pongTimer); noServer(); } };
  sock.onmessage = function(e){
    var m;
    try { m = JSON.parse(e.data); } catch(x){ return; }
    if (m && m.pong){ clearTimeout(pongTimer); return; }
    busyNow = false; showLive();
    var kind = waiting; waiting = null;
    if (typeof kind === 'function'){ kind(m); return; }
    if (kind === 'list'){ fillRuns(Array.isArray(m) ? m.map(function(r){ return r.file; }) : []); loadConfig(); }
    else if (m && m.html){ BOOK[m.file] = {html: m.html, title: m.title}; showRun(m.file); }
    else { document.getElementById('srv').textContent = 'the report server would not give that file'; document.getElementById('runs').value = current; }
  };
}
function ask(kind, message){
  waiting = kind;
  busyNow = true; showLive();               // turns until the answer comes
  var m = {hash: TOKEN};
  for (var k in message) m[k] = message[k];
  ws.send(JSON.stringify(m));
}
function switchRun(name){
  if (name === current) return;
  if (BOOK[name]){ showRun(name); return; }
  var go = function(){ ask('load', {filename: name}); };
  if (ws && ws.readyState === 1) go(); else connect(go);
  document.getElementById('runs').value = current;     // until the file arrives
}
function showRun(name){
  var b = BOOK[name];
  document.getElementById('panels').innerHTML = b.html;
  document.title = b.title;
  document.querySelector('h1').textContent = b.title;
  current = name;
  tint();
  store('run', name);
  document.getElementById('runs').value = name;
  setupBook();
  var f = document.getElementById('find').value;
  if (f !== '') findText(f);
}

// ---- tables: sort, select (filter) and find ----
function cellValue(td){ return td.dataset.v !== undefined ? td.dataset.v : td.textContent.trim(); }
// A six-pointed star: an up triangle over a down triangle, drawn once. Both show when not
// sorted (the star), only the up one ascending, only the down one descending. They never
// move; data-dir on the button (see the css) hides the one not in use.
var STAR = '<svg viewBox="0 0 20 20"><polygon class="up" points="10,1.5 17.4,14.5 2.6,14.5"/><polygon class="dn" points="10,18.5 2.6,5.5 17.4,5.5"/></svg>';
// Column widths. A column of numbers or short text (nothing over 11 characters) is at most 11
// wide; a column of text may go to 42. What does not fit ends in an ellipsis and the hover has it
// all. A cell of several lines shows its first line that has text; the hover shows every line.
var CAP_SHORT = 11, CAP_TEXT = 42;
function capColumns(t, rows){
  var heads = t.tHead ? t.tHead.rows[0].cells : [];
  Array.prototype.forEach.call(heads, function(th, c){
    var longest = 0, numeric = rows.length > 0, any = false;
    rows.forEach(function(r){
      var td = r.cells[c];
      if (!td || td.classList.contains('bar')) return;
      var full = td.textContent.trim();
      if (/[\r\n]/.test(full)){
        var lines = full.split(/\r?\n/).map(function(x){ return x.trim(); }).filter(Boolean);
        td.dataset.v = full; td.title = full;
        td.textContent = lines[0] + (lines.length > 1 ? ' …' : '');
        full = td.textContent;
      }
      if (full !== ''){ any = true; if (isNaN(numval(full))) numeric = false; }
      longest = Math.max(longest, full.length);
    });
    var cap = (numeric || longest <= CAP_SHORT) ? CAP_SHORT : CAP_TEXT, cls = 'cap' + cap;
    rows.forEach(function(r){
      var td = r.cells[c];
      if (!td || td.classList.contains('bar')) return;
      td.classList.add(cls);
      if (!td.title && td.textContent.trim().length > cap) td.title = td.textContent.trim();
    });
    th.classList.add(cls);
    var label = th.textContent.trim();
    if (label.length > cap) th.title = label;
  });
}
function setupTable(t){
  var rows = Array.prototype.slice.call(t.tBodies.length ? t.tBodies[0].rows : []);
  capColumns(t, rows);
  t.rowsAll = rows;
  rows.forEach(function(r, i){ r.dataset.no = i; });
  t.filters = {};
  var heads = Array.prototype.slice.call(t.tHead ? t.tHead.rows[0].cells : []);
  var forced = (t.dataset.select || 'auto');
  heads.forEach(function(th, c){
    var vals = rows.map(function(r){ return cellValue(r.cells[c] || {textContent:'', dataset:{}}); });
    var numeric = vals.length > 0 && vals.every(function(v){ return v === '' || !isNaN(numval(v)); });
    th.dataset.num = numeric ? '1' : '0';
    var hd = document.createElement('div'), hl = document.createElement('span');   // label | star hambo
    hd.className = 'hd'; hl.className = 'hl';
    while (th.firstChild) hl.appendChild(th.firstChild);
    hd.appendChild(hl); th.appendChild(hd);
    var distinct = Array.from(new Set(rows.map(function(r){ return (r.cells[c] || {textContent:''}).textContent.trim(); })));
    var varied = distinct.length > 1;       // an empty column, or one value, has nothing to sort or filter
    if (t.dataset.sort !== '0' && varied){
      var sb = document.createElement('button');
      sb.className = 'sortbtn'; sb.innerHTML = STAR; sb.title = 'sort: ascending, descending, original order';
      sb.onclick = function(e){ e.stopPropagation(); sortBy(t, c, sb); };
      hd.appendChild(sb);
    }
    var want = forced === 'none' ? false : forced === 'auto' ? varied
               : varied && forced.split(',').indexOf(String(c)) >= 0;
    if (want) hd.appendChild(selectMenu(t, c, distinct));
  });
  var note = document.createElement('span');
  note.className = 'shown';
  t.parentNode.insertBefore(note, t);
  t.note = note;
}
function sortBy(t, c, btn){
  // each click moves the column on: not sorted -> ascending -> descending -> the original order
  var was = !btn.classList.contains('on') ? 'none' : btn.dataset.dir;
  var now = was === 'none' ? 'asc' : was === 'asc' ? 'desc' : 'none';
  t.querySelectorAll('.sortbtn').forEach(function(b){ b.classList.remove('on'); b.innerHTML = STAR; delete b.dataset.dir; });
  var num = t.tHead.rows[0].cells[c].dataset.num === '1';
  var rows = t.rowsAll.slice();
  if (now === 'none'){ rows.sort(function(a, b){ return a.dataset.no - b.dataset.no; }); }
  else {
    btn.classList.add('on'); btn.dataset.dir = now;
    rows.sort(function(a, b){
      var A = cellValue(a.cells[c]), B = cellValue(b.cells[c]);
      var d = num ? (numval(A) || 0) - (numval(B) || 0) : A.localeCompare(B, undefined, {numeric:true});
      return now === 'asc' ? d : -d;
    });
  }
  var tb = t.tBodies[0];
  rows.forEach(function(r){ tb.appendChild(r); });
}
// FILTER:BEGIN -- the filter expression language: pure functions, tested with node (b_htmlwriter)
//   numbers   >3 & <6.3   <3 | >6   >= <= = !=   3   3..6        text   p*.3 (whole cell, * ? wild)
//   text      [plain] or {a b} contains   [lo - hi] or [lo hi] or [a-f] range by first letters
//   either    *  all     blank  empty cell     !x  not x     x & y  both     x | y  either
function FilterError(message, at, len){ this.message = message; this.at = at; this.len = len; }
function splitTop(s, ch, base){        // pieces of s cut at ch outside [] and {}, with offsets
  var out = [], depth = 0, from = 0;
  for (var i = 0; i <= s.length; i++){
    var c = s.charAt(i);
    if (c === '[' || c === '{') depth++;
    else if (c === ']' || c === '}') depth--;
    if (i === s.length || (c === ch && depth === 0)){ out.push({s: s.slice(from, i), at: base + from}); from = i + 1; }
  }
  return out;
}
var NUM = '-?(?:\\d+\\.?\\d*|\\.\\d+)(?:e[+-]?\\d+)?[kMG]?';
function numval(s){                    // a number, or a figure with the suffix k M G (14.4k); NaN if neither
  var m = /^(-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)([kMG])?$/.exec(String(s).trim());
  return m ? parseFloat(m[1]) * ({k: 1e3, M: 1e6, G: 1e9}[m[2]] || 1) : NaN;
}
function numTerm(t, at){
  var m = new RegExp('^(>=|<=|!=|>|<|=)?\\s*(' + NUM + ')$', 'i').exec(t);
  if (m){
    var n = numval(m[2]), op = m[1] || '=';
    return function(v){
      if (v === '') return false;
      var x = numval(v);
      return op === '>' ? x > n : op === '<' ? x < n : op === '>=' ? x >= n : op === '<=' ? x <= n : op === '!=' ? x !== n : x === n;
    };
  }
  m = new RegExp('^(' + NUM + ')\\.\\.(' + NUM + ')$', 'i').exec(t);
  if (m){
    var lo = Math.min(numval(m[1]), numval(m[2])), hi = Math.max(numval(m[1]), numval(m[2]));
    return function(v){ if (v === '') return false; var x = numval(v); return x >= lo && x <= hi; };
  }
  throw new FilterError('not a number test', at, t.length);
}
function contains(word){ var w = word.toLowerCase(); return function(v){ return v.toLowerCase().indexOf(w) >= 0; }; }
function letters(a, b){                // a range by first letters: lo.. up to the start of hi
  var lo = a.replace(/\*+$/, '').toLowerCase(), hi = b.replace(/\*+$/, '').toLowerCase();
  if (lo > hi){ var swap = lo; lo = hi; hi = swap; }
  return function(v){ var s = v.toLowerCase(); return s >= lo && s.slice(0, hi.length) <= hi; };
}
function textTerm(t, at){
  var first = t.charAt(0), last = t.charAt(t.length - 1), inner;
  if (first === '[' && last === ']' && t.length > 2){
    inner = t.slice(1, -1).trim();
    var m = /^(.*\S)\s+-\s+(.*\S)$/.exec(inner) || /^([^\s-]+)-([^\s-]+)$/.exec(inner);
    if (m) return letters(m[1], m[2]);
    var parts = inner.split(/\s+/);
    if (parts.length === 1) return contains(parts[0]);
    if (parts.length === 2) return letters(parts[0], parts[1]);
    throw new FilterError('a phrase goes in { }', at, t.length);
  }
  if (first === '{' && last === '}' && t.length > 2) return contains(t.slice(1, -1).trim());
  if (/[\[\]{}]/.test(t)) throw new FilterError('a bracket is not closed', at, t.length);
  var re = new RegExp('^' + t.replace(/[.+^$()|\\\/-]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$', 'i');
  return function(v){ return re.test(v); };
}
function parseTerm(raw, numeric){
  var t = raw.s.replace(/^\s+/, ''), at = raw.at + raw.s.length - t.length;
  t = t.replace(/\s+$/, '');
  if (t === '') throw new FilterError('a test is missing', raw.at, Math.max(1, raw.s.length));
  if (t === '*') return function(){ return true; };
  if (t.toLowerCase() === 'blank') return function(v){ return v.trim() === ''; };
  if (t.charAt(0) === '!' && t.charAt(1) !== '='){
    var not = parseTerm({s: t.slice(1), at: at + 1}, numeric);
    return function(v){ return !not(v); };
  }
  return numeric ? numTerm(t, at) : textTerm(t, at);
}
function parseFilter(text, numeric){   // a function of the cell text, or null for no filter; or throws FilterError
  if (text.trim() === '') return null;
  var ors = splitTop(text, '|', 0).map(function(o){
    return splitTop(o.s, '&', o.at).map(function(a){ return parseTerm(a, numeric); });
  });
  return function(v){
    return ors.some(function(ands){ return ands.every(function(f){ return f(v); }); });
  };
}
// FILTER:END
var GUIDE = {
  num: [['&gt;3 &amp; &lt;6.3', 'a range: more than 3 and less than 6.3'], ['&lt;3 | &gt;6', 'the extremes: below 3 or above 6'],
        ['3..6', 'from 3 to 6 inclusive (6..3 works too)'], ['&gt;= &lt;= = !=', 'the other comparisons; a bare 3 means = 3']],
  text: [['p*.3', 'the whole cell: * is any run of characters, ? is one'], ['*plain*', 'cells that contain plain'],
         ['[plain]', 'a shortcut for *plain*'], ['{plain plan2}', 'contains the phrase, spaces and all'],
         ['[p* - s*]', 'a range by first letters, p up to s'], ['[a-f]', 'short for letters a to f'],
         ['[plan plan2]', 'two words are a range too; low-high or high-low, same result']],
  both: [['*', 'everything'], ['blank', 'empty cells (!blank: the others)'], ['!x', 'not x'], ['x &amp; y', 'both'], ['x | y', 'either']]
};
function showGuide(anchor, numeric){
  hideGuide();
  var g = document.createElement('div');
  g.id = 'fguide';
  var rows = function(list){ return list.map(function(r){ return '<tr><td><code>' + r[0] + '</code></td><td>' + r[1] + '</td></tr>'; }).join(''); };
  g.innerHTML = '<b>Filter guide</b> &mdash; ' + (numeric ? 'a number column' : 'a text column') +
    '<p>Type an expression in the box; the table follows as you type. It combines (AND) with the values ticked below it. Text is not case sensitive.</p>' +
    '<table>' + rows(numeric ? GUIDE.num : GUIDE.text) + rows(GUIDE.both) + '</table>' +
    '<p>Leaving the box with a mistake in it is refused; the &#10005; clears it. Esc or a click elsewhere closes this guide.</p>';
  document.body.appendChild(g);
  var r = anchor.getBoundingClientRect();
  g.style.left = Math.max(4, Math.min(r.left, window.innerWidth - g.offsetWidth - 4)) + 'px';
  g.style.top = Math.max(4, Math.min(r.bottom + 4, window.innerHeight - g.offsetHeight - 4)) + 'px';
}
function hideGuide(){ var g = document.getElementById('fguide'); if (g) g.remove(); }
document.addEventListener('mousedown', function(e){ var g = document.getElementById('fguide'); if (g && !g.contains(e.target)) hideGuide(); });
document.addEventListener('keydown', function(e){ if (e.key === 'Escape') hideGuide(); });
var HAMBO ='<svg viewBox="0 0 14 10"><path d="M1 1.5h12M1 5h12M1 8.5h12"/></svg>';
function esc(s){ return s.replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
function selectMenu(t, c, distinct){
  var numeric = t.tHead.rows[0].cells[c].dataset.num === '1';
  var d = document.createElement('details');
  d.className = 'bandmenu';
  var s = document.createElement('summary'); s.innerHTML = HAMBO; s.title = 'filter (right click for the guide)';
  s.oncontextmenu = function(e){ e.preventDefault(); showGuide(s, numeric); };
  var pop = document.createElement('div'); pop.className = 'bandpop';
  var hint = numeric ? '&gt;3 &amp; &lt;6.3 | 9' : 'p*.3 | [a-f] | {a b}';
  var head = '<div class="fx"><input class="fbox" spellcheck="false" placeholder="' + hint + '"><button class="fclr" title="clear">&#10005;</button></div><div class="ferr"></div>';
  var all = '<label class="all"><input type="checkbox" class="all" checked> all</label>';
  if (distinct.length > 20) distinct = [], all = '';      // too many values to tick: the box alone
  pop.innerHTML = head + all + distinct.sort(function(a, b){ return a.localeCompare(b, undefined, {numeric:true}); }).map(function(v){
    return '<label><input type="checkbox" value="' + v.replace(/"/g, '&quot;') + '"> ' + (v === '' ? '(blank)' : v.replace(/</g, '&lt;')) + '</label>';
  }).join('');
  var fbox = pop.querySelector('.fbox'), ferr = pop.querySelector('.ferr');
  var set = null, pred = null;
  function apply(){
    d.classList.toggle('filtering', !!(set || pred));
    if (set || pred) t.filters[c] = {set: set, pred: pred, numeric: numeric}; else delete t.filters[c];
    applyTable(t);
  }
  function tryParse(){ try { return {pred: parseFilter(fbox.value, numeric)}; } catch(e){ if (e instanceof FilterError) return {error: e}; throw e; } }
  function calm(){ fbox.classList.remove('bad'); ferr.innerHTML = ''; }
  fbox.oninput = function(){ var r = tryParse(); calm(); if (!r.error){ pred = r.pred; apply(); } };   // while typing: no colour, the last good filter stays
  fbox.onblur = function(){                                   // leaving is refused while the expression is wrong
    var r = tryParse();
    if (!r.error) return;
    var e = r.error, v = fbox.value;
    fbox.classList.add('bad');
    ferr.innerHTML = esc(v.slice(0, e.at)) + '<b>' + esc(v.slice(e.at, e.at + e.len)) + '</b>' + esc(v.slice(e.at + e.len)) + ' &mdash; ' + e.message;
    setTimeout(function(){ fbox.focus(); }, 0);
  };
  pop.querySelector('.fclr').onmousedown = function(e){ e.preventDefault(); };   // keep the focus: clearing is always allowed
  pop.querySelector('.fclr').onclick = function(){ fbox.value = ''; calm(); pred = null; apply(); };
  pop.onchange = function(e){
    if (e.target === fbox) return;
    var boxes = Array.prototype.slice.call(pop.querySelectorAll('input[type=checkbox]:not(.all)'));
    var allBox = pop.querySelector('input.all');
    if (e.target === allBox) boxes.forEach(function(b){ b.checked = false; });
    var picked = boxes.filter(function(b){ return b.checked; }).map(function(b){ return b.value; });
    allBox.checked = picked.length === 0;
    set = picked.length ? new Set(picked) : null;
    apply();
  };
  d.appendChild(s); d.appendChild(pop);
  return d;
}
var findTerm = '';
function rowText(r){ if (r.text === undefined) r.text = r.textContent.toLowerCase(); return r.text; }
function applyTable(t){
  var shown = 0, filtering = Object.keys(t.filters).length > 0 || findTerm !== '';
  t.rowsAll.forEach(function(r){
    var ok = true;
    for (var c in t.filters){
      var f = t.filters[c], cell = r.cells[c] || {textContent: '', dataset: {}};
      var text = cell.textContent.trim();
      if (f.set && !f.set.has(text)){ ok = false; break; }
      if (f.pred && !f.pred(f.numeric ? cellValue(cell).trim() : text)){ ok = false; break; }
    }
    if (ok && findTerm !== '' && rowText(r).indexOf(findTerm) < 0) ok = false;
    r.classList.toggle('nomatch', !ok);
    if (ok) shown++;
  });
  t.note.textContent = filtering ? 'showing ' + shown + ' of ' + t.rowsAll.length : '';
}
document.addEventListener('click', function(e){
  document.querySelectorAll('details.bandmenu[open]').forEach(function(d){
    if (!d.contains(e.target) && !d.querySelector('.fbox.bad')) d.removeAttribute('open');
  });
});

// ---- find: tables are filtered, every tab says how many places match ----
function findText(text){
  findTerm = text.trim().toLowerCase();
  var total = 0;
  document.querySelectorAll('.tpanel').forEach(function(p){
    var n = 0;
    if (findTerm !== ''){
      var low = p.textContent.toLowerCase(), at = 0;
      while ((at = low.indexOf(findTerm, at)) >= 0){ n++; at += findTerm.length; }
    }
    total += n;
    var b = document.getElementById('btn_' + p.id);
    var badge = b.querySelector('.hits');
    if (n){
      if (!badge){ badge = document.createElement('span'); badge.className = 'hits'; b.insertBefore(badge, b.querySelector('.tclose')); }
      badge.textContent = n;
    } else if (badge) badge.remove();
  });
  document.querySelectorAll('table.grid').forEach(applyTable);
  document.getElementById('findInfo').textContent = findTerm === '' ? '' : total + ' matches';
}
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape'){ var f = document.getElementById('find'); if (f.value){ f.value = ''; findText(''); } }
});

// ---- click a block that kept its Markdown to edit it ----
document.addEventListener('dblclick', function(e){
  var el = e.target.closest('[data-md]');
  if (!el || el.querySelector('textarea')) return;
  var area = document.createElement('textarea');
  area.className = 'edit'; area.value = el.dataset.md; area.rows = Math.max(3, el.dataset.md.split('\n').length + 1);
  area.title = 'Markdown of this block; Escape leaves it';
  el.parentNode.insertBefore(area, el);
  area.focus();
  area.onkeydown = function(k){ if (k.key === 'Escape'){ area.remove(); } };
});

function setupBook(){
  buildTabs();
  var s = hiddenSet();
  allBtns().forEach(function(b){ if (s.has(tabIdOf(b))) b.style.display = 'none'; });
  var last = recall('tab', '');
  var btn = last && document.getElementById('btn_' + last);
  if (!btn || btn.style.display === 'none'){ var v = visBtns(); btn = v.length ? v[0] : null; }
  if (btn) selTab(tabIdOf(btn));
  buildCombo();
  document.querySelectorAll('table.grid').forEach(setupTable);
  document.querySelectorAll('.mk-flex:not(.cards)').forEach(checkered);
}
// A flex is a checker board: an item is tinted when its row and column add to an odd number, so
// no two tinted ones touch at a side. The columns are what the grid has now, so this is done
// when the flex is first laid out and again whenever its size changes (a resize, a tab shown).
function checker(el){
  if (!el.offsetParent) return;                           // not shown: nothing is laid out
  var cols = getComputedStyle(el).gridTemplateColumns.split(' ').length;
  Array.prototype.forEach.call(el.children, function(item, i){
    item.classList.toggle('alt', (i % cols + Math.floor(i / cols)) % 2 === 1);
  });
}
function checkered(el){
  if (!el._watched && window.ResizeObserver){
    el._watched = new ResizeObserver(function(){ checker(el); });
    el._watched.observe(el);
  }
  checker(el);
}
window.addEventListener('resize', function(){
  document.querySelectorAll('.mk-flex:not(.cards)').forEach(checker);
});
document.addEventListener('click', function(e){         // [name](#tab_x) in the Markdown opens that tab
  var a = e.target.closest ? e.target.closest('a[href^="#tab_"]') : null;
  if (!a) return;
  e.preventDefault();
  var id = tabId(decodeURIComponent(a.getAttribute('href').slice(5)));
  if (document.getElementById('btn_' + id)) comboSel(id);
});
// ---- settings, and the code tab: function list, comments ----
// The settings (font, size, initials, line numbers, tab width, wrap, your colour) live in the
// report server, which keeps them between reports; a page asks for them when it opens and
// sends a change. Without a server the last ones this browser saw are used.
var CFG = {font: 'Consolas', size: 12, initials: 'user', linenos: true, tabwidth: 4, wrap: false, color: '#e8650f'};
var MONO = ['Consolas', 'Courier New', 'Lucida Console', 'Cascadia Code', 'Cascadia Mono', 'JetBrains Mono',
            'Fira Code', 'Fira Mono', 'Source Code Pro', 'DejaVu Sans Mono', 'Menlo', 'Monaco', 'SF Mono',
            'Ubuntu Mono', 'Roboto Mono', 'IBM Plex Mono', 'Inconsolata', 'Hack', 'Liberation Mono',
            'Noto Sans Mono', 'Courier'];
function monoFonts(){                       // the monospaced ones of these that this machine has
  var c = document.createElement('canvas').getContext('2d');
  function w(f, t){ c.font = '16px ' + f; return c.measureText(t).width; }
  return MONO.filter(function(f){
    var q = "'" + f + "'";
    var here = w(q + ', serif', 'iiiiWWWW') !== w('serif', 'iiiiWWWW') || w(q + ', sans-serif', 'iiiiWWWW') !== w('sans-serif', 'iiiiWWWW');
    return here && Math.abs(w(q + ', monospace', 'iiiiiiii') - w(q + ', monospace', 'WWWWWWWW')) < 0.5;
  });
}
function applyConfig(){
  var s = document.documentElement.style;
  s.setProperty('--cfont', "'" + CFG.font + "', monospace");
  s.setProperty('--csize', CFG.size + 'px');
  s.setProperty('--ctab', CFG.tabwidth);
  s.setProperty('--usercolor', CFG.color);
  document.body.classList.toggle('nonos', !CFG.linenos);
  document.body.classList.toggle('wrap', !!CFG.wrap);
}
function sendLater(fn, message){            // one question at a time: wait for the one in flight
  if (!ws || ws.readyState !== 1) return false;
  if (waiting !== null){ setTimeout(function(){ sendLater(fn, message); }, 150); return true; }
  ask(fn, message);
  return true;
}
function takeConfig(m){
  if (!m || Array.isArray(m)) return;
  for (var k in m) CFG[k] = m[k];
  store('config', CFG); applyConfig(); fillCfg();
}
function loadConfig(){
  var kept = recall('config', null);
  if (kept) for (var k in kept) CFG[k] = kept[k];
  applyConfig();
  sendLater(takeConfig, {config: true});
}
function fillCfg(){
  var sel = document.getElementById('cfgfont');
  if (!sel.options.length){
    var fonts = monoFonts();
    if (fonts.indexOf(CFG.font) < 0) fonts.unshift(CFG.font);
    fonts.forEach(function(f){ var o = document.createElement('option'); o.value = o.textContent = f; sel.appendChild(o); });
  }
  sel.value = CFG.font;
  document.getElementById('cfgsize').value = CFG.size;
  document.getElementById('cfginitials').value = CFG.initials;
  document.getElementById('cfgtab').value = CFG.tabwidth;
  document.getElementById('cfglines').checked = !!CFG.linenos;
  document.getElementById('cfgwrap').checked = !!CFG.wrap;
  document.getElementById('cfgcolor').value = CFG.color;
}
function toggleCfg(){ var m = document.getElementById('cfgmenu'); m.hidden = !m.hidden; if (!m.hidden) fillCfg(); }
function cfgChanged(){
  var size = parseInt(document.getElementById('cfgsize').value, 10), tab = parseInt(document.getElementById('cfgtab').value, 10);
  var initials = document.getElementById('cfginitials').value.replace(/\W/g, '').slice(0, 8);
  var change = {font: document.getElementById('cfgfont').value, color: document.getElementById('cfgcolor').value,
                linenos: document.getElementById('cfglines').checked, wrap: document.getElementById('cfgwrap').checked};
  if (size >= 6 && size <= 40) change.size = size;
  if (tab >= 1 && tab <= 16) change.tabwidth = tab;
  if (initials) change.initials = initials;
  for (var k in change) CFG[k] = change[k];
  store('config', CFG); applyConfig();
  sendLater(takeConfig, {config: change});
}

function paneOf(el){ return el.closest('.codepane'); }
function lineEl(pane, n){ return pane.querySelector('.ln[data-n="' + n + '"]'); }
function flash(el){ el.classList.add('flash'); setTimeout(function(){ el.classList.remove('flash'); }, 1200); }
function goTo(pane, el){ pane.querySelector('.clines').scrollTop = el.offsetTop - 30; flash(el); }
function stepComment(pane, d){              // the next or previous comment from where the code is scrolled to
  var box = pane.querySelector('.clines'), all = Array.prototype.slice.call(box.querySelectorAll('.cm')), here = box.scrollTop + 32, pick = null;
  if (!all.length) return;
  if (d > 0) pick = all.filter(function(c){ return c.offsetTop > here + 2; })[0] || all[0];
  else { all.forEach(function(c){ if (c.offsetTop < here - 2) pick = c; }); pick = pick || all[all.length - 1]; }
  goTo(pane, pick);
}
function bump(el, delta){                   // the lines from el on move by delta
  for (; el; el = el.nextElementSibling){
    if (el.classList.contains('ln')){
      var n = parseInt(el.dataset.n, 10) + delta;
      el.dataset.n = n; el.id = 'L' + n; el.querySelector('.no').textContent = n;
    } else if (el.classList.contains('cm')){
      el.dataset.first = parseInt(el.dataset.first, 10) + delta; el.dataset.last = parseInt(el.dataset.last, 10) + delta;
    }
  }
}
var askedInitials = false;
function needInitials(){                    // a comment is tagged ###initials: ask once for yours while it is still "user"
  if (CFG.initials !== 'user' || askedInitials) return;
  askedInitials = true;
  var a = (window.prompt('Your initials (1-8 letters or digits) tag your comments in the file as ###initials.\nCancel to stay "user". You can change them later in the settings.', '') || '').replace(/\W/g, '').slice(0, 8);
  if (!a || a.toLowerCase() === 'cld') return;
  CFG.initials = a; store('config', CFG);
  sendLater(takeConfig, {config: {initials: a}});
}
function tagOf(cm){ return cm.dataset.who === 'claude' ? 'cld' : cm.dataset.initials; }
function openEditor(pane, target, reply){   // ask the server first: an outdated report or file may not be edited, and then nothing opens
  var state = pane.querySelector('.cstate');
  state.textContent = 'checking the report';
  var ok = sendLater(function(m){
    if (!Array.isArray(m) && m.ok) startEditor(pane, target, reply);
    else state.textContent = (m && m.outdated) || 'not allowed: the server refused';
  }, {check: true, filename: pane.querySelector('.cpath').dataset.path});
  if (!ok) state.textContent = 'not saved: no report server (see the footer)';
}
function startEditor(pane, target, reply){  // a line number or comment mark was clicked: its comment, or an empty one for the line; reply: a new one after the comment target
  var ta = pane.querySelector('.cedit textarea'), prev = target.previousElementSibling, ed;
  var cm = target.classList.contains('cm') ? target : (prev && prev.classList.contains('cm') ? prev : null);
  if (reply || !cm) needInitials();
  if (reply) ed = {cm: null, anchor: target.nextElementSibling, line: parseInt(target.dataset.last, 10) + 1, tag: CFG.initials};
  else ed = {cm: cm, anchor: target, line: cm ? null : parseInt(target.dataset.n, 10), tag: cm ? tagOf(cm) : CFG.initials};
  if (cm && !reply) ed.orig = cm.querySelector('.cmt').innerHTML;       // what to show again if the edit is refused
  pane.ed = ed;
  ta.value = cm && !reply ? cm.dataset.md : '';
  pane.querySelector('.cstate').textContent = reply ? 'a reply as ' + ed.tag : cm ? 'editing the comment' : 'a new comment on line ' + ed.line + ' as ' + ed.tag;
  ta.focus();
}
function draft(pane, text){                 // what is typed shows in the code at once, as plain text until it is saved
  var ed = pane.ed;
  if (!ed.cm){
    var cm = document.createElement('div');
    cm.className = 'cm'; cm.dataset.who = ed.tag === 'cld' ? 'claude' : 'user'; cm.dataset.initials = ed.tag === 'cld' ? '' : ed.tag;
    cm.innerHTML = '<span class="mg"><i class="dot"></i></span><div class="cmt"></div>';
    ed.anchor.parentNode.insertBefore(cm, ed.anchor);
    ed.cm = cm;
  }
  var box = ed.cm.querySelector('.cmt');
  box.classList.add('draft'); box.textContent = text;
}
function saveComment(pane){
  var ed = pane.ed, ta = pane.querySelector('.cedit textarea'), state = pane.querySelector('.cstate');
  if (!ed) return;
  var text = ta.value.replace(/\s+$/, ''), sent = ta.value;
  var full = text;
  var msg = {filename: pane.querySelector('.cpath').dataset.path, base: pane.querySelector('.clines').dataset.base, text: full, tag: ed.tag};
  if (ed.cm && ed.cm.dataset.first){ msg.update = true; msg.first = parseInt(ed.cm.dataset.first, 10); msg.last = parseInt(ed.cm.dataset.last, 10); }
  else if (text === ''){ if (ed.cm) ed.cm.remove(); pane.ed = null; return; }
  else { msg.insert = true; msg.line = ed.line; }
  if (!msg.base){ state.textContent = 'not saved: this tab shows an older copy of the file; reload the report to edit it'; return; }
  var sentTo = ed;
  state.textContent = 'saving';
  var ok = sendLater(function(m){
    if (Array.isArray(m) || !m.ok){                // refused: the draft is not kept, the comment is as it was
      if (sentTo.cm && !sentTo.cm.dataset.first) sentTo.cm.remove();
      else if (sentTo.cm && sentTo.orig !== undefined){ var b = sentTo.cm.querySelector('.cmt'); b.classList.remove('draft'); b.innerHTML = sentTo.orig; }
      if (pane.ed === sentTo){ pane.ed = null; ta.value = ''; }
      state.textContent = (!Array.isArray(m) && m.outdated) || 'not saved: the server refused (has the file changed? reload the page)';
      return;
    }
    pane.querySelector('.clines').dataset.base = m.base;
    // the same file in another tab (two suites test one unit): the file is now newer than that tab shows, so it is
    // marked out of date: the server holds the one master file, and an edit from an old copy would hit the wrong lines
    var path = msg.filename;
    Array.prototype.forEach.call(document.querySelectorAll('.codepane'), function(other){
      if (other !== pane && other.querySelector('.cpath').dataset.path === path){
        other.querySelector('.clines').dataset.base = '';
        other.querySelector('.cstate').textContent = 'this file was changed from another tab: reload the report to see it and edit here';
      }
    });
    var cm = sentTo.cm, after = cm ? cm.nextElementSibling : sentTo.anchor;
    if (m.removed){ if (cm) cm.remove(); bump(after, m.delta); if (pane.ed === sentTo) pane.ed = null; state.textContent = 'removed'; return; }
    cm.dataset.first = m.first; cm.dataset.last = m.last; cm.dataset.md = full;
    var box = cm.querySelector('.cmt'); box.classList.remove('draft'); box.innerHTML = m.html + '<a class="reply" href="#">reply</a>';
    bump(after, m.delta);
    state.textContent = 'saved';
    if (pane.ed === sentTo && ta.value !== sent) saveComment(pane);      // typed on while it saved
  }, msg);
  if (!ok) state.textContent = 'not saved: no report server (see the footer)';
}
document.addEventListener('click', function(e){
  var t = e.target;
  if (!t.closest) return;
  var pane = t.closest('.codepane'), a;
  if (!pane){ if (!t.closest('#cfgmenu') && !t.closest('#cfgbtn')) document.getElementById('cfgmenu').hidden = true; return; }
  if (t.closest('.fnbtn')){ pane.querySelector('.funcs').classList.toggle('hid'); return; }
  if (t.closest('.cprev')){ stepComment(pane, -1); return; }
  if (t.closest('.cnext')){ stepComment(pane, 1); return; }
  if ((a = t.closest('.funclist a'))){ e.preventDefault(); var el = lineEl(pane, parseInt(a.dataset.line, 10)); if (el) goTo(pane, el); return; }
  if ((a = t.closest('.reply'))){ e.preventDefault(); var thread = a.closest('.cm'); if (thread.dataset.first) openEditor(pane, thread, true); return; }
  var no = t.closest('.no');                       // a line number: a comment above that line
  if (no && no.parentNode.classList.contains('ln')){ openEditor(pane, no.parentNode); return; }
  var mg = t.closest('.mg');
  if (mg && mg.parentNode.classList.contains('ln')){ if (document.body.classList.contains('nonos')) openEditor(pane, mg.parentNode); }   // with no numbers shown, the margin is the way in
  else if (mg && mg.parentNode.classList.contains('cm')) openEditor(pane, mg.parentNode);
});
document.addEventListener('input', function(e){
  var ta = e.target;
  if (!ta.matches || !ta.matches('.cedit textarea')) return;
  var pane = paneOf(ta);
  if (!pane.ed) return;
  draft(pane, ta.value);
  clearTimeout(pane.saveTimer);
  pane.saveTimer = setTimeout(function(){ saveComment(pane); }, 600);
});
function init(){
  applyConfig();
  BOOK[SELF] = {html: document.getElementById('panels').innerHTML, title: document.title};
  setupBook();
  fillRuns(RUNS.map(function(r){ return r.file; }));
  connect(function(){ ask('list', {}); });
  setInterval(pulse, PING_EVERY);                   // keeps the socket awake; also reconnects
}
window.addEventListener('DOMContentLoaded', init);
