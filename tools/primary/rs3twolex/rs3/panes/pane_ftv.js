// pane_ftv.js -- the file tree (see pane_ftv.py for its signals).
RS.pane('ftv', function(ctx){
  var tree = ctx.el.querySelector('.ftree'), sendBox = ctx.el.querySelector('.fsend'), files = [], want = '',
      marks = {}, sendto = 0, key = 'ftvdirs:' + ctx.page.hash;
  RS.doors(ctx.el.querySelector('.doors'), ['ftv']);      // its own door: to hide it; the code and options bars open it again
  var targets = ctx.page.panes.filter(function(p){ return (p.block === 'code' || p.block === 'toptabs') && !p.host; });
  if (targets.length) sendto = targets[0].where;      // with no pane to take a file it goes to a new browser tab (0)
  try { files = JSON.parse(tree.dataset.files || '[]'); } catch (e) {}
  function kept(){ try { return new Set(JSON.parse(localStorage.getItem(key) || '[]')); } catch (e) { return new Set(); } }
  function keep(set){ try { localStorage.setItem(key, JSON.stringify(Array.from(set))); } catch (e) {} }
  function nest(){                       // the flat list as folders
    var top = {dirs: {}, files: []};
    files.forEach(function(f){
      var parts = f[0].slice(2).split('/'), at = top;
      parts.slice(0, -1).forEach(function(d){ at = at.dirs[d] || (at.dirs[d] = {dirs: {}, files: []}); });
      at.files.push(f);
    });
    return top;
  }
  function matches(path){               // a part of a path, or a wildcard: * any text, ? one character
    if (!want) return true;
    var p = path.toLowerCase();
    if (!/[*?]/.test(want)) return p.indexOf(want) >= 0;
    var body = want.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.');
    if (want.indexOf('/') >= 0) return new RegExp('(^|/)' + body + '$').test(p.slice(2));   // with a slash: the end of the path
    return new RegExp('^' + body + '$').test(p.split('/').pop());                          // without: the file name
  }
  function isOpen(path){ return marks[path] && marks[path].size > 0; }
  function draw(){
    var open = kept(), shown = files.filter(function(f){ return matches(f[0]); });
    tree.innerHTML = '';
    if (!shown.length){ tree.innerHTML = '<p class="mute">no files' + (want ? ' match' : '') + '</p>'; return; }
    function fill(parent, folder, path){
      Object.keys(folder.dirs).sort(function(a, b){ return a.toLowerCase() < b.toLowerCase() ? -1 : 1; }).forEach(function(name){
        var det = document.createElement('details'), sum = document.createElement('summary'), here = path + name + '/';
        sum.textContent = name; det.appendChild(sum); det.dataset.path = here; det.open = !!want || open.has(here);
        fill(det, folder.dirs[name], here); parent.appendChild(det);
      });
      folder.files.forEach(function(f){
        var a = document.createElement('a'), p = f[0];
        a.href = '#'; a.dataset.p = p; a.dataset.k = f[1]; a.title = p; a.className = 'ff ' + f[1] + (isOpen(p) ? ' on' : '');
        a.textContent = p.split('/').pop(); parent.appendChild(a);
      });
    }
    var top = { dirs: {}, files: [] };
    shown.forEach(function(f){
      var parts = f[0].slice(2).split('/'), at = top;
      parts.slice(0, -1).forEach(function(d){ at = at.dirs[d] || (at.dirs[d] = {dirs: {}, files: []}); });
      at.files.push(f);
    });
    fill(tree, top, '');
  }
  tree.addEventListener('toggle', function(e){
    var d = e.target;
    if (want || !d.matches || !d.matches('details')) return;
    var s = kept(); if (d.open) s.add(d.dataset.path); else s.delete(d.dataset.path); keep(s);
  }, true);
  tree.addEventListener('click', function(e){
    var a = e.target.closest('a.ff');
    if (!a) return;
    e.preventDefault();
    var path = a.dataset.p, where = a.dataset.k === 'html' ? 0 : sendto;
    if (marks[path] && marks[path].has(where)) ctx.emit('closefile', {path: path, where: where});
    else ctx.emit('openfile', {path: path, where: where});
  });
  // the send-to toggle: only when more than one pane takes files
  if (targets.length > 1){
    sendBox.innerHTML = 'send to <select>' + targets.map(function(p){ return '<option value="' + p.where + '">' + p.loc + '</option>'; }).join('') +
      '<option value="0">new tab</option></select>';
    sendBox.querySelector('select').onchange = function(){ sendto = +this.value; };
  }
  var filter = ctx.el.querySelector('.ffilter');
  filter.addEventListener('input', function(){ want = filter.value.trim().toLowerCase(); draw(); });
  ctx.el.querySelector('.freload').onclick = function(){
    ctx.verb('tree', {}).then(function(r){
      if (r.ok && r.files){ files = r.files.map(function(f){ return [f.p, f.k]; }); draw(); }
    });
  };
  function reveal(path){
    var a = tree.querySelector('a.ff[data-p="' + path.replace(/"/g, '\\"') + '"]');
    if (!a) return;
    for (var d = a.parentElement; d && d !== tree; d = d.parentElement) if (d.tagName === 'DETAILS') d.open = true;
    a.scrollIntoView({block: 'nearest'});
  }
  draw();
  return {
    onOpenfile: function(d){
      (marks[d.path] = marks[d.path] || new Set()).add(d.where);
      if (want && files.every(function(f){ return f[0] !== d.path; })) return;
      draw();
      if (targets.length < 2 || d.where === sendto || d.where === 0) reveal(d.path);
    },
    onClosefile: function(d){
      if (marks[d.path]){ marks[d.path].delete(d.where); if (!marks[d.path].size) delete marks[d.path]; }
      draw();
    },
    onSearchtext: function(d){ if (d.mode === 'files'){ want = (d.text || '').trim().toLowerCase(); filter.value = d.text || ''; draw(); } }
  };
});
