// pane_ftv.js -- the file tree (see pane_ftv.py for its signals).
RS.pane('ftv', function(ctx){
  var tree = ctx.el.querySelector('.ftree'), sendBox = ctx.el.querySelector('.fsend'), files = [], want = '',
      marks = {}, sendto = '', key = 'ftvdirs:' + ctx.page.hash;       // marks[path]: the panes that show it; sendto: '' = the manager chooses
  RS.doors(ctx.el.querySelector('.doors'), ['ftv']);      // its own door: to hide it; the code and options bars open it again
  var targets = ctx.page.panes.filter(function(p){ return p.takes && !p.hosted; });      // the blocks that say they take files
  try { files = JSON.parse(tree.dataset.files || '[]'); } catch (e) {}
  function limit(more){ if (more) ctx.emit('notice', {text: 'max files exceeded: the tree lists the first ' + files.length, bad: true}); }
  ctx.whenLinked(function(){ limit(tree.dataset.truncated === '1'); });
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
    var path = a.dataset.p, want = a.dataset.k === 'html' ? 'tab' : sendto, at = marks[path];
    if (a.dataset.k === 'pdf'){                                      // a pdf is not shown in a pane: the server opens it in the system's program for pdfs
      ctx.verb('openfile', {path: path}).then(function(r){ if (!r.ok) ctx.emit('notice', {text: r.error || 'the pdf was not opened', bad: true}); })
        .catch(function(err){ ctx.emit('notice', {text: err.message, bad: true}); });
      return;
    }
    var shown = !!(at && at.size && (!want || at.has(want)));       // a click on a file that is shown closes it
    ctx.emit('mngshowfile', {path: path, show: !shown, to: want === 'tab' ? 'tab' : want ? [want] : undefined});
  });
  // the send-to toggle: only when more than one pane takes files
  if (targets.length > 1){
    sendBox.innerHTML = 'send to <select><option value="">auto</option>' +
      targets.map(function(p){ return '<option value="' + p.loc + '">' + p.loc + '</option>'; }).join('') +
      '<option value="tab">new tab</option></select>';
    sendBox.querySelector('select').onchange = function(){ sendto = this.value; };
  }
  var filter = ctx.el.querySelector('.ffilter');
  filter.addEventListener('input', function(){ want = filter.value.trim().toLowerCase(); draw(); });
  ctx.el.querySelector('.freload').onclick = function(){
    ctx.verb('tree', {}).then(function(r){
      if (r.ok && r.files){ files = r.files.map(function(f){ return [f.p, f.k]; }); draw(); limit(r.truncated); }
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
    onShowcode: function(d){               // a file is in front in some pane (or no longer): its mark
      var set = marks[d.path] = marks[d.path] || new Set();
      if (d.on) set.add(d.loc); else set.delete(d.loc);
      if (!set.size) delete marks[d.path];
      if (want && files.every(function(f){ return f[0] !== d.path; })) return;
      draw();
      if (d.on) reveal(d.path);
    },
    onSearchtext: function(d){ if (d.mode === 'files'){ want = (d.text || '').trim().toLowerCase(); filter.value = d.text || ''; draw(); } }
  };
});
