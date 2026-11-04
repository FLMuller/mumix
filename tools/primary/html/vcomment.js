// vcomment.js -- the file tree and the file tabs of a vcomment page. runbench.js (loaded first,
// unchanged) does the tabs, the code pane, the comment editor and the report server link; this
// adds a list of the repository's files beside them and opens a file as a tab on a click.
// VC = {root, title, open: [files to open at the start]} is written by vcomment.py.
var vcTree = null;                      // what the server sent: {root, name, base, files}
var vcWant = '';                        // the filter box's text, lower case
var vcOpening = false;

function vcState(text){ document.getElementById('vcstate').textContent = text || ''; }
function vcBase(p){ return p.split('/').pop(); }
function vcPanel(rel){                  // the panel of a file that was opened at some time
  var all = document.querySelectorAll('#panels > [data-rel]');
  for (var i = 0; i < all.length; i++) if (all[i].dataset.rel === rel) return all[i];
  return null;
}
function vcIsOpen(rel){                 // open = its tab button shows: closing a tab only hides the button (closeTab in runbench.js)
  var p = vcPanel(rel), b = p && document.getElementById('btn_' + p.id);
  return !!(b && b.style.display !== 'none');
}
function vcSync(){                      // the tree marks the files that are open tabs (orange)
  Array.prototype.forEach.call(document.querySelectorAll('#vcfiles a.vcf[data-p]'), function(a){
    a.classList.toggle('on', vcIsOpen(a.dataset.p));
  });
}
document.addEventListener('tabschanged', vcSync);   // runbench.js says so when a tab is closed or shown again
function vcWhenUp(fn){                  // wait for the report server socket, then go
  if (ws && ws.readyState === 1) fn(); else setTimeout(function(){ vcWhenUp(fn); }, 250);
}

// ---- the tree ----
function vcLoadTree(){
  vcState('reading the file list');
  vcWhenUp(function(){
    sendLater(function(m){
      if (!m || !m.files){ vcState('the server did not give a file list (is this page registered? run vcomment again)'); return; }
      vcTree = m;
      vcState('');
      vcDraw();
      if (!vcOpening && VC.open && VC.open.length){ vcOpening = true; vcOpenMany(VC.open.slice()); }
    }, {tree: true});
  });
}
function vcFilter(text){ vcWant = text.trim().toLowerCase(); vcDraw(); }      // the filter box calls this
function vcNest(files){                 // the flat list as folders: {dirs: {name: folder}, files: [file]}
  var top = {dirs: {}, files: []};
  files.forEach(function(f){
    var parts = f.p.split('/'), at = top;
    parts.slice(0, -1).forEach(function(d){ at = at.dirs[d] || (at.dirs[d] = {dirs: {}, files: []}); });
    at.files.push(f);
  });
  return top;
}
function vcUrl(p){ return vcTree.base + '/' + p.split('/').map(encodeURIComponent).join('/'); }
function vcDraw(){
  if (!vcTree) return;
  var box = document.getElementById('vcfiles'), kept = recall('vcdirs', []), show = new Set(kept);
  var files = vcTree.files.filter(function(f){ return !vcWant || f.p.toLowerCase().indexOf(vcWant) >= 0; });
  box.innerHTML = '';
  if (!files.length){ box.innerHTML = '<p class="mute">no files' + (vcWant ? ' match' : '') + '</p>'; return; }
  function fill(parent, folder, path){
    Object.keys(folder.dirs).sort(function(a, b){ return a.toLowerCase() < b.toLowerCase() ? -1 : 1; }).forEach(function(name){
      var det = document.createElement('details'), sum = document.createElement('summary'), here = path + name + '/';
      sum.textContent = name;
      det.appendChild(sum);
      det.dataset.path = here;
      det.open = !!vcWant || show.has(here);
      fill(det, folder.dirs[name], here);
      parent.appendChild(det);
    });
    folder.files.forEach(function(f){
      var el, k = f.k;
      if (k === 'html'){ el = document.createElement('a'); el.href = vcUrl(f.p); el.target = '_blank'; el.rel = 'noopener'; el.title = 'opens in a new browser tab'; }
      else if (k === 'code' || k === 'md' || k === 'text'){ el = document.createElement('a'); el.href = '#'; el.dataset.p = f.p; el.title = f.p; if (vcIsOpen(f.p)) el.classList.add('on'); }
      else { el = document.createElement('span'); el.title = k === 'big' ? 'too large to open (over 4 MB)' : 'vcomment does not open this kind of file'; }
      el.className += ' vcf ' + k;
      el.textContent = vcBase(f.p);
      parent.appendChild(el);
    });
  }
  fill(box, vcNest(files), '');
}
document.addEventListener('toggle', function(e){
  var d = e.target;
  if (!d.matches || !d.matches('#vcfiles details') || vcWant) return;
  var s = new Set(recall('vcdirs', []));
  if (d.open) s.add(d.dataset.path); else s.delete(d.dataset.path);
  store('vcdirs', Array.from(s));
}, true);
document.addEventListener('click', function(e){
  var a = e.target.closest ? e.target.closest('#vcfiles a.vcf[data-p]') : null;
  if (!a) return;
  e.preventDefault();
  var p = vcPanel(a.dataset.p);
  if (p && vcIsOpen(a.dataset.p)) closeTab(p.id);   // open: a second click closes its tab (click again to read the file afresh)
  else vcOpen(a.dataset.p);
});

// ---- a file as a tab ----
function vcLabel(rel){                  // the file name, or its path when another open tab has that name
  var name = vcBase(rel), clash = false;
  Array.prototype.forEach.call(document.querySelectorAll('#panels > [data-rel]'), function(d){
    if (d.dataset.rel !== rel && vcBase(d.dataset.rel) === name) clash = true;
  });
  return clash ? rel : name;
}
function vcOpen(rel, then){
  vcState('opening ' + rel);
  var ok = sendLater(function(m){
    if (m && m.ok && m.html){ vcAdd(rel, m.html); vcState(''); }
    else vcState('the server would not open ' + rel);
    if (then) then();
  }, {open: rel, label: vcLabel(rel)});
  if (!ok){ vcState('not open: no report server (see the footer)'); if (then) then(); }
}
function vcOpenMany(list){              // one after the other: the socket takes one question at a time
  if (!list.length) return;
  vcOpen(list.shift(), function(){ vcOpenMany(list); });
}
function vcAdd(rel, htmlText){          // the tab of a file, replacing the tab it had
  var box = document.createElement('div'), panels = document.getElementById('panels');
  box.innerHTML = htmlText;
  var div = box.firstElementChild;
  if (!div) return;
  Array.prototype.forEach.call(panels.querySelectorAll(':scope > [data-rel]'), function(d){
    if (d.dataset.rel === rel) d.remove();
  });
  panels.appendChild(div);
  // buildTabs (runbench.js) makes the buttons from the panels still marked mk-tab, and starts by
  // clearing the strip, so the panels it built before are marked again for it
  Array.prototype.forEach.call(panels.children, function(p){
    if (p.classList.contains('tpanel')) p.className = 'mk mk-tab';
  });
  var hidden = hiddenSet();
  hidden.delete(tabId(div.dataset.name));
  store('hidden', Array.from(hidden));
  buildTabs();
  hidden = hiddenSet();
  allBtns().forEach(function(b){ if (hidden.has(tabIdOf(b))) b.style.display = 'none'; });
  div.querySelectorAll('table.grid').forEach(setupTable);
  selTab(div.id);
  buildCombo();
  var f = document.getElementById('find').value;
  if (f !== '') findText(f);
  vcGrips(div);
  vcSync();
}

// ---- the tree: shown or folded away, and its width ----
function vcFold(on){                    // the button in the tree's header folds it away; the arrow beside the line brings it back
  document.querySelector('.vcwrap').classList.toggle('folded', !!on);
  store('vcfold', !!on);
}
// Pointer events, not mouse events: a pen or a finger sends no mouse events while it drags, so a splitter
// that listens for mousedown and mousemove never moves under one. setPointerCapture keeps the moves
// coming to the line when the pointer strays off it, and touch-action:none (vcomment.css) stops the
// browser taking the gesture to scroll. One drag is one pointer, told by its id.
(function(){
  var split = document.getElementById('vcsplit'), tree = document.getElementById('vctree'), wrap = document.querySelector('.vcwrap'), drag = null;
  var w = recall('vcwidth', 0);
  if (w >= 120) tree.style.width = w + 'px';
  split.addEventListener('pointerdown', function(e){
    if (wrap.classList.contains('folded')) return;
    drag = e.pointerId; split.classList.add('drag');
    split.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  split.addEventListener('pointermove', function(e){
    if (drag !== e.pointerId) return;
    tree.style.width = Math.max(120, Math.min(e.clientX - tree.getBoundingClientRect().left, window.innerWidth * 0.7)) + 'px';
  });
  function end(e){
    if (drag !== e.pointerId) return;
    drag = null; split.classList.remove('drag');
    store('vcwidth', tree.getBoundingClientRect().width);
  }
  split.addEventListener('pointerup', end);
  split.addEventListener('pointercancel', end);
})();

// ---- the comment box: drag the line on its top edge ----
// The box is the bottom row of the code pane, so it grows upward: the code lines above give up the
// height (the pane is a flex column, see vcomment.css) and nothing else on the page moves.
function vcGrips(div){
  Array.prototype.forEach.call(div.querySelectorAll('.cedit'), function(box){
    if (box.querySelector('.cgrip')) return;
    var grip = document.createElement('div'), ta = box.querySelector('textarea'), drag = null, h = recall('vcedith', 0);
    grip.className = 'cgrip'; grip.title = 'drag to resize the comment box';
    box.insertBefore(grip, box.firstChild);
    if (h >= 40) ta.style.height = h + 'px';
    grip.addEventListener('pointerdown', function(e){
      drag = {id: e.pointerId, y: e.clientY, h: ta.offsetHeight};
      grip.classList.add('drag');
      grip.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    grip.addEventListener('pointermove', function(e){
      if (!drag || drag.id !== e.pointerId) return;
      var room = box.parentNode.clientHeight - 140;      // keep the bar and some code lines in sight
      ta.style.height = Math.max(40, Math.min(drag.h + drag.y - e.clientY, room)) + 'px';
    });
    function end(e){
      if (!drag || drag.id !== e.pointerId) return;
      drag = null; grip.classList.remove('drag');
      store('vcedith', ta.offsetHeight);
    }
    grip.addEventListener('pointerup', end);
    grip.addEventListener('pointercancel', end);
  });
}

window.addEventListener('DOMContentLoaded', function(){
  if (VC.title) document.title = VC.title;
  vcFold(recall('vcfold', false));
  vcLoadTree();
});
