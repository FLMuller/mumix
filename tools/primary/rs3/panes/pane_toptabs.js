// pane_toptabs.js -- the tab strip (see pane_toptabs.py for its signals).
RS.pane('toptabs', function(ctx){
  var bar = ctx.el.querySelector('.ttbar'), body = ctx.el.querySelector('.ttbody'), tabs = [], active = null;
  var mine = ctx.page.panes.filter(function(p){ return p.loc === ctx.loc; })[0];
  var host = ctx.page.panes.filter(function(p){ return p.hosted && p.block === mine.holds; })[0];   // the block this one holds
  var hostEl = host && document.querySelector('.cell[data-loc="' + host.loc + '"]');
  if (hostEl){                          // the page has a code block: the files show there, this is only the strip
    hostEl.innerHTML = ''; body.remove(); body = hostEl;
    ctx.el.style.flex = '0 0 auto';
  }
  var combo = ctx.el.querySelector('.ttcombo'), left = ctx.el.querySelector('.ttl'), right = ctx.el.querySelector('.ttr');
  var KEY = 'ttHidden:' + ctx.page.hash;
  function hiddenSet(){ try { return new Set(JSON.parse(localStorage.getItem(KEY) || '[]')); } catch (e) { return new Set(); } }
  function keepHidden(){
    try { localStorage.setItem(KEY, JSON.stringify(tabs.filter(function(t){ return t.hidden; }).map(function(t){ return t.title; }))); } catch (e) {}
  }
  function base(p){ return p.split('/').pop(); }
  function label(t){ return t.section ? t.title : base(t.path); }
  function rebuild(){                   // the combo lists every tab, a hidden one too: choosing it brings it back
    combo.innerHTML = '<option value="">tabs&hellip;</option>';
    tabs.forEach(function(t, i){
      var o = document.createElement('option');
      o.value = i; o.textContent = (t.hidden ? '(hidden) ' : '') + label(t); o.title = t.section ? t.title : t.path;
      combo.appendChild(o);
    });
  }
  combo.onchange = function(){
    var t = tabs[+combo.value]; combo.selectedIndex = 0;
    if (!t) return;
    if (t.hidden){ t.hidden = false; t.button.hidden = false; keepHidden(); rebuild(); }
    show(t);
  };
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
    if (active && active !== tab && active.code) active.code.hidden();      // the one that was in front says it is behind
    active = tab;
    tabs.forEach(function(t){
      t.pane.style.display = t === tab ? '' : 'none';
      t.button.classList.toggle('on', t === tab);
    });
    if (tab){ tab.button.scrollIntoView({block: 'nearest', inline: 'nearest'}); tab.code && tab.code.shown && tab.code.shown(); }
  }
  function lastShown(){ return tabs.filter(function(t){ return !t.hidden; }).pop() || null; }
  function find(path){ return tabs.filter(function(t){ return !t.section && t.path === path; })[0]; }
  function drop(tab){                   // a file's tab goes: the code pane announces showcode off for its file
    tabs.splice(tabs.indexOf(tab), 1);
    tab.code.remove();
    tab.pane.remove(); tab.button.remove();
    if (active === tab) show(lastShown());
    rebuild();
  }
  function hide(tab){                   // a section's tab is put away, not lost: the combo brings it back
    tab.hidden = true; tab.button.hidden = true;
    keepHidden(); rebuild();
    if (active === tab) show(lastShown());
  }
  function add(path){
    var pane = document.createElement('div'), button = document.createElement('span');
    pane.className = 'ttpane'; pane.innerHTML = RS.codeSkeleton; body.appendChild(pane);
    var tab = {path: path, pane: pane, button: button};
    tab.code = ctx.make('code', pane, {loc: ctx.loc, config: ctx.config});      // it speaks as this block
    button.className = 'ttab'; button.title = path;
    button.innerHTML = '<span class="ttn"></span><button class="ttx" title="close this tab">&times;</button>';
    button.querySelector('.ttn').textContent = base(path);
    button.querySelector('.ttn').onclick = function(){ show(tab); };
    button.querySelector('.ttx').onclick = function(){ drop(tab); };
    bar.appendChild(button); tabs.push(tab);
    rebuild();
    show(tab);
    tab.code.open(path);                // loads; the pane announces nothing for a file it was just given
    return tab;
  }
  function addSection(title, html, bad, hidden){          // a section of a static page: its html, as it was written
    var pane = document.createElement('div'), button = document.createElement('span');
    pane.className = 'ttpane sec'; pane.innerHTML = html; pane.style.display = 'none'; body.appendChild(pane);
    var tab = {section: true, title: title, path: 'section:' + title, pane: pane, button: button, hidden: hidden};
    button.className = 'ttab' + (bad ? ' bad' : ''); button.title = title; button.hidden = hidden;
    button.innerHTML = '<span class="ttn"></span><button class="ttx" title="put this tab away (the tabs list brings it back)">&times;</button>';
    button.querySelector('.ttn').textContent = title;
    button.querySelector('.ttn').onclick = function(){ show(tab); };
    button.querySelector('.ttx').onclick = function(){ hide(tab); };
    bar.appendChild(button); tabs.push(tab);
    return tab;
  }
  function active_(name){ return function(d){ var h = active && active.code && active.code[name]; if (h) h.call(active.code, d); }; }
  var h = {
    onShowfile: function(d){
      var tab = find(d.path);
      if (d.show === false){ if (tab) drop(tab); return; }
      if (tab) { if (active !== tab) show(tab); } else add(d.path);
    }
  };
  ['onSelectfunk', 'onSaved', 'onSearchtext', 'onSearchnext', 'onSearchprev']
    .forEach(function(n){ h[n] = active_(n); });
  // the sections the page was made with, in their order: the first that is not put away shows
  var away = hiddenSet();
  Array.prototype.forEach.call(ctx.el.querySelectorAll('template.ttsec'), function(t){
    addSection(t.dataset.title, t.innerHTML, !!t.dataset.bad, away.has(t.dataset.title));
  });
  if (tabs.length){ rebuild(); show(tabs.filter(function(t){ return !t.hidden; })[0] || null); }
  var first = [];
  try { first = JSON.parse(ctx.el.querySelector('.tt').dataset.open || '[]'); } catch (e) {}
  if (first.length) ctx.whenLinked(function(){        // files the page was made with: ask for them as ftv would
    window.setTimeout(function(){
      first.forEach(function(p){ ctx.emit('mngshowfile', {path: p, show: true, to: [ctx.loc]}); });
    }, 500);
  });
  return h;
});
