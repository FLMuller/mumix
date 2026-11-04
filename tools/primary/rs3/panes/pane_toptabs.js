// pane_toptabs.js -- the tab strip (see pane_toptabs.py for its signals).
RS.pane('toptabs', function(ctx){
  var bar = ctx.el.querySelector('.ttbar'), body = ctx.el.querySelector('.ttbody'), tabs = [], active = null;
  var host = ctx.page.panes.filter(function(p){ return p.block === 'code' && p.host; })[0];
  var hostEl = host && document.querySelector('.cell[data-loc="' + host.loc + '"]');
  if (hostEl){                          // the page has a code block: the files show there, this is only the strip
    hostEl.innerHTML = ''; body.remove(); body = hostEl;
    ctx.el.style.flex = '0 0 auto';
  }
  var combo = ctx.el.querySelector('.ttcombo'), left = ctx.el.querySelector('.ttl'), right = ctx.el.querySelector('.ttr');
  function base(p){ return p.split('/').pop(); }
  function rebuild(){                   // the combo lists every tab: a long strip has some out of sight
    combo.innerHTML = '<option value="">tabs&hellip;</option>';
    tabs.forEach(function(t, i){
      var o = document.createElement('option'); o.value = i; o.textContent = base(t.path); o.title = t.path; combo.appendChild(o);
    });
  }
  combo.onchange = function(){ var t = tabs[+combo.value]; combo.selectedIndex = 0; if (t) show(t); };
  var holdTimer = null, holdIv = null, held = false;      // a click scrolls a tab's width, a hold scrolls on
  function holdStart(d){
    held = false;
    holdTimer = setTimeout(function(){ held = true; holdIv = setInterval(function(){ bar.scrollBy({left: d * 6}); }, 16); }, 350);
  }
  function holdEnd(d){
    clearTimeout(holdTimer);
    if (holdIv){ clearInterval(holdIv); holdIv = null; }
    else if (!held && d !== undefined){
      var w = tabs.length ? tabs[0].button.offsetWidth + 4 : 120;
      bar.scrollBy({left: d * w, behavior: 'smooth'});
    }
  }
  [[left, -1], [right, 1]].forEach(function(b){
    b[0].onmousedown = function(){ holdStart(b[1]); };
    b[0].onmouseup = function(){ holdEnd(b[1]); };
    b[0].onmouseleave = function(){ holdEnd(); };
  });
  function show(tab){
    active = tab;
    tabs.forEach(function(t){
      t.pane.style.display = t === tab ? '' : 'none';
      t.button.classList.toggle('on', t === tab);
    });
    if (tab){ tab.button.scrollIntoView({block: 'nearest', inline: 'nearest'}); tab.code.shown && tab.code.shown(); }
  }
  function find(path){ return tabs.filter(function(t){ return t.path === path; })[0]; }
  function drop(tab, announce){
    tabs.splice(tabs.indexOf(tab), 1);
    if (announce) tab.code.remove();
    tab.pane.remove(); tab.button.remove();
    if (active === tab) show(tabs[tabs.length - 1] || null);
    rebuild();
  }
  function add(path){
    var pane = document.createElement('div'), button = document.createElement('span');
    pane.className = 'ttpane'; pane.innerHTML = RS.codeSkeleton; body.appendChild(pane);
    var tab = {path: path, pane: pane, button: button};
    tab.code = ctx.make('code', pane, {where: ctx.where, config: ctx.config});
    button.className = 'ttab'; button.title = path;
    button.innerHTML = '<span class="ttn"></span><button class="ttx" title="close this tab">&times;</button>';
    button.querySelector('.ttn').textContent = base(path);
    button.querySelector('.ttn').onclick = function(){ show(tab); };
    button.querySelector('.ttx').onclick = function(){ drop(tab, true); };
    bar.appendChild(button); tabs.push(tab);
    rebuild();
    show(tab);
    tab.code.open(path);                // loads; the pane announces nothing for a file it was just given
    return tab;
  }
  function active_(name){ return function(d){ var h = active && active.code[name]; if (h) h.call(active.code, d); }; }
  var h = {
    onOpenfile: function(d){
      var tab = find(d.path);
      if (tab) { if (active !== tab) show(tab); } else add(d.path);
    },
    onClosefile: function(d){ var tab = find(d.path); if (tab) drop(tab, false); }
  };
  ['onSelectfunk', 'onSaved', 'onSearchtext', 'onSearchnext', 'onSearchprev']
    .forEach(function(n){ h[n] = active_(n); });
  var first = [];
  try { first = JSON.parse(ctx.el.querySelector('.tt').dataset.open || '[]'); } catch (e) {}
  if (first.length) ctx.whenLinked(function(){        // files the page was made with: ask for them as ftv would
    window.setTimeout(function(){
      first.forEach(function(p){ ctx.emit('openfile', {path: p, where: ctx.where}); });
    }, 500);
  });
  return h;
});
