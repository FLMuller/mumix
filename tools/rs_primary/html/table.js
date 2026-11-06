// table.js -- sort and filter for a table, as the report pages have it: RS.table.make(table, options).
//
// Every column that has more than one value gets a star (sort: ascending, descending, then the original order: two
// triangles that show together as a star and one at a time when sorted) and a hamburger (a menu: a filter box with the
// expression language below, and a tick list of the column's values when there are 20 or fewer; right click for the
// guide, the cross clears). A row that does not pass is hidden (class nomatch) and "showing N of M" says so.
//
//   RS.table.make(t, {initial: fn, onchange: fn})
//       t          a <table> with a <thead> row of headers and a <tbody>; a cell's data-v is what it sorts and filters
//                  by when its text is not (a number, a status), else its text is
//       initial    a comparison function: the rows are put in that order first, and it is the "original order"
//       onchange   fn({visible, all, filtering}) after every sort, filter or find: the rows that pass, all the rows
//   t.setFind(text, columns)   a find on top of the filters: rows whose text (of those columns, else of the whole row) does not hold
//                      it are hidden
//   t.rowsAll          the rows in their original order
//
// This is a copy of the table code of runbench.js (the report pages), made for rs3; the filter language (the block marked FILTER
// below) is the same text. The cap on column widths is left out (the pane sets its own).
//
// VERSION  M1 m01.v03 (2026-11-05): the filter popup is fixed to the window under its button, so the pane does not clip it.
//          M1 m01.v02 (2026-11-04): every value ticked is "all" again (the others are cleared).
//          M1 m01.v01 (2026-11-04): first version, from runbench.js.
RS.table = (function(){
'use strict';
function cellValue(td){ return td.dataset.v !== undefined ? td.dataset.v : td.textContent.trim(); }
// A six-pointed star: an up triangle over a down triangle, drawn once. Both show when not sorted (the star), only the up one
// ascending, only the down one descending; data-dir on the button (see the css) hides the one not in use.
var STAR = '<svg viewBox="0 0 20 20"><polygon class="up" points="10,1.5 17.4,14.5 2.6,14.5"/><polygon class="dn" points="10,18.5 2.6,5.5 17.4,5.5"/></svg>';
// FILTER:BEGIN -- the filter expression language: pure functions (tested in a page by tests/b_rs3page.py)
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
    if (boxes.length > 1 && boxes.every(function(b){ return b.checked; })) boxes.forEach(function(b){ b.checked = false; });   // every value ticked is no filter: "all", the others cleared
    var picked = boxes.filter(function(b){ return b.checked; }).map(function(b){ return b.value; });
    allBox.checked = picked.length === 0;
    set = picked.length ? new Set(picked) : null;
    apply();
  };
  d.appendChild(s); d.appendChild(pop);
  // The popup is fixed to the window, placed under the button: the pane around the table scrolls and clips what hangs out of it.
  function place(){
    var r = s.getBoundingClientRect();
    pop.style.position = 'fixed';
    pop.style.top = (r.bottom + 3) + 'px';
    pop.style.maxHeight = Math.max(120, Math.min(260, window.innerHeight - r.bottom - 12)) + 'px';
    pop.style.left = Math.max(4, Math.min(r.left, window.innerWidth - pop.offsetWidth - 8)) + 'px';
  }
  d.addEventListener('toggle', function(){
    if (d.open){ place(); window.addEventListener('scroll', place, true); window.addEventListener('resize', place); }
    else { window.removeEventListener('scroll', place, true); window.removeEventListener('resize', place); }
  });
  return d;
}

function rowText(r, columns){
  if (columns) return columns.map(function(c){ return r.cells[c] ? r.cells[c].textContent.toLowerCase() : ''; }).join('\n');
  if (r.text === undefined) r.text = r.textContent.toLowerCase();
  return r.text;
}
function applyTable(t){
  var shown = 0, filtering = Object.keys(t.filters).length > 0 || t.find !== '';
  t.rowsAll.forEach(function(r){
    var ok = true;
    for (var c in t.filters){
      var f = t.filters[c], cell = r.cells[c] || {textContent: '', dataset: {}};
      var text = cell.textContent.trim();
      if (f.set && !f.set.has(text)){ ok = false; break; }
      if (f.pred && !f.pred(f.numeric ? cellValue(cell).trim() : text)){ ok = false; break; }
    }
    if (ok && t.find !== '' && rowText(r, t.findColumns).indexOf(t.find) < 0) ok = false;
    r.classList.toggle('nomatch', !ok);
    if (ok) shown++;
  });
  t.note.textContent = filtering ? 'showing ' + shown + ' of ' + t.rowsAll.length : '';
  changed(t, filtering);
}
function changed(t, filtering){
  if (t.options.onchange) t.options.onchange({visible: t.rowsAll.filter(function(r){ return !r.classList.contains('nomatch'); }),
                                              all: t.rowsAll, filtering: filtering === undefined ? (Object.keys(t.filters).length > 0 || t.find !== '') : filtering});
}
document.addEventListener('click', function(e){
  Array.prototype.forEach.call(document.querySelectorAll('details.bandmenu[open]'), function(d){
    if (!d.contains(e.target) && !d.querySelector('.fbox.bad')) d.removeAttribute('open');
  });
});
function sortBy(t, c, btn){
  // each click moves the column on: not sorted -> ascending -> descending -> the original order
  var was = !btn.classList.contains('on') ? 'none' : btn.dataset.dir;
  var now = was === 'none' ? 'asc' : was === 'asc' ? 'desc' : 'none';
  Array.prototype.forEach.call(t.querySelectorAll('.sortbtn'), function(b){ b.classList.remove('on'); b.innerHTML = STAR; delete b.dataset.dir; });
  var num = t.tHead.rows[0].cells[c].dataset.num === '1';
  var rows = t.rowsAll.slice();
  if (now === 'none'){ rows.sort(function(a, b){ return a.dataset.no - b.dataset.no; }); }
  else {
    btn.classList.add('on'); btn.dataset.dir = now;
    rows.sort(function(a, b){
      var A = cellValue(a.cells[c]), B = cellValue(b.cells[c]);
      var d = num ? (numval(A) || 0) - (numval(B) || 0) : A.localeCompare(B, undefined, {numeric: true});
      return now === 'asc' ? d : -d;
    });
  }
  var tb = t.tBodies[0];
  rows.forEach(function(r){ tb.appendChild(r); });
  changed(t);
}
function make(t, options){
  if (t.rowsAll) return t;                               // made already
  var rows = Array.prototype.slice.call(t.tBodies.length ? t.tBodies[0].rows : []);
  options = options || {};
  if (options.initial){
    rows.sort(options.initial);
    rows.forEach(function(r){ t.tBodies[0].appendChild(r); });
  }
  t.options = options;
  t.rowsAll = rows;
  t.find = '';
  t.filters = {};
  t.classList.add('tbl');
  rows.forEach(function(r, i){ r.dataset.no = i; });
  var heads = Array.prototype.slice.call(t.tHead ? t.tHead.rows[0].cells : []);
  heads.forEach(function(th, c){
    var vals = rows.map(function(r){ return cellValue(r.cells[c] || {textContent: '', dataset: {}}); });
    var numeric = vals.length > 0 && vals.every(function(v){ return v === '' || !isNaN(numval(v)); });
    th.dataset.num = numeric ? '1' : '0';
    var hd = document.createElement('div'), hl = document.createElement('span');   // label | star hambo
    hd.className = 'hd'; hl.className = 'hl';
    while (th.firstChild) hl.appendChild(th.firstChild);
    hd.appendChild(hl); th.appendChild(hd);
    var distinct = Array.from(new Set(rows.map(function(r){ return (r.cells[c] || {textContent: ''}).textContent.trim(); })));
    if (distinct.length < 2) return;                     // an empty column, or one value, has nothing to sort or filter
    var sb = document.createElement('button');
    sb.className = 'sortbtn'; sb.innerHTML = STAR; sb.title = 'sort: ascending, descending, original order';
    sb.onclick = function(e){ e.stopPropagation(); sortBy(t, c, sb); };
    hd.appendChild(sb);
    hd.appendChild(selectMenu(t, c, distinct));
  });
  var note = document.createElement('span');
  note.className = 'shown';
  t.parentNode.insertBefore(note, t);
  t.note = note;
  t.setFind = function(text, columns){ t.find = (text || '').trim().toLowerCase(); t.findColumns = columns; applyTable(t); };
  t.refresh = function(){ applyTable(t); };
  return t;
}
return {make: make};
})();
