// pane_statusbar.js -- the status bar block (see pane_statusbar.py for its signals).
RS.pane('statusbar', function(ctx){
  var el = ctx.el, q = function(c){ return el.querySelector('.' + c); };
  var cfg = ctx.config, panes = ctx.page.panes, port = ctx.page.port;
  var mode = q('smode'), find = q('sfind'), info = q('sinfo'), state = q('sstate'), srv = q('ssrv'), live = q('slive');
  var menu = q('cfgmenu'), FONTS = ['Consolas', 'Courier New', 'Lucida Console', 'Menlo', 'Monaco', 'monospace'];
  var up = ctx.linked(), busy = false, said = null, monitors = 0;

  // ---- find: what can be searched is what the blocks of the page say they can find (the search their write() returned) ----
  panes.forEach(function(p){
    if (p.search && !mode.querySelector('[value="' + p.search + '"]')){
      var o = document.createElement('option'); o.value = o.textContent = p.search; mode.appendChild(o);
    }
  });
  var last = mode.value;
  if (!mode.options.length) mode.hidden = find.hidden = q('sprev').hidden = q('snext').hidden = q('shome').hidden = true;
  function fire(m, text){ ctx.emit('searchtext', {text: text, mode: m}); }
  find.addEventListener('input', function(){ info.textContent = ''; fire(mode.value, find.value); });
  find.addEventListener('keydown', function(e){
    if (e.key === 'Enter') ctx.emit(e.shiftKey ? 'searchprev' : 'searchnext', {mode: mode.value});
  });
  mode.addEventListener('change', function(){
    fire(last, '');                         // the one we leave is cleared
    last = mode.value; info.textContent = '';
    if (find.value) fire(mode.value, find.value);
  });
  q('snext').onclick = function(){ ctx.emit('searchnext', {mode: mode.value}); };
  q('sprev').onclick = function(){ ctx.emit('searchprev', {mode: mode.value}); };
  q('shome').onclick = function(){ ctx.emit('searchhome', {mode: mode.value}); };

  // ---- the settings menu ----
  function fill(){
    var f = q('cfgfont');
    f.innerHTML = '';
    (FONTS.indexOf(cfg.font) < 0 ? [cfg.font].concat(FONTS) : FONTS).forEach(function(n){
      var o = document.createElement('option'); o.value = o.textContent = n; f.appendChild(o);
    });
    f.value = cfg.font;
    q('cfgsize').value = cfg.size; q('cfginitials').value = cfg.initials; q('cfgtab').value = cfg.tabwidth;
    q('cfglines').checked = cfg.linenos !== false; q('cfgwrap').checked = !!cfg.wrap; q('cfgcolor').value = cfg.color;
  }
  q('cfgbtn').onclick = function(){ menu.hidden = !menu.hidden; if (!menu.hidden) fill(); };
  document.addEventListener('click', function(e){      // the menu closes on a click anywhere outside it
    if (!menu.hidden && !e.target.closest('.cfgmenu') && !e.target.closest('.cfgbtn')) menu.hidden = true;
  });
  q('cfgsrv').onclick = function(e){       // a report server page with a live socket is already open: nothing is opened
    if (monitors){ e.preventDefault(); menu.hidden = true; say('the report server is already open'); }
  };
  var OPEN = 'the report server is already open';
  live.onclick = function(){               // the circle opens the report server in a new tab, unless one is open
    if (monitors) say(OPEN);
    else window.open('/reportserver', '_blank');
  };
  document.addEventListener('click', function(e){      // that message goes at the next click anywhere else
    if (state.textContent === OPEN && !e.target.closest('.slive')) say('');
  });
  function changed(){
    var change = {font: q('cfgfont').value, size: +q('cfgsize').value, initials: q('cfginitials').value.trim(),
                  tabwidth: +q('cfgtab').value, linenos: q('cfglines').checked, wrap: q('cfgwrap').checked,
                  color: q('cfgcolor').value};
    ctx.verb('config', {change: change}).then(function(r){
      if (!r.ok){ say(r.error || 'the server refused that setting', true); return; }
      Object.assign(cfg, r.config || change);          // the page's config (every block reads this object)
      ctx.emit('withconfig', {});
      ctx.emit('withlineno', {on: cfg.linenos !== false});
      ctx.emit('withwrap', {on: !!cfg.wrap});
      say('settings kept');
    }).catch(function(e){ say(e.message, true); });
  }
  ['cfgfont', 'cfgsize', 'cfginitials', 'cfgtab', 'cfglines', 'cfgwrap', 'cfgcolor'].forEach(function(c){ q(c).onchange = changed; });

  // ---- the state, the server and the pulse ----
  function say(text, bad){
    state.textContent = text || ''; state.classList.toggle('bad', !!bad);
    clearTimeout(said);
    if (text && !bad) said = setTimeout(function(){ state.textContent = ''; }, 6000);
  }
  function show(){ live.setAttribute('data-live', !up ? 'disc' : busy ? 'spin' : 'pulse'); }
  srv.textContent = 'rs3 :' + port;
  show();
  return {
    onSearchcount: function(d){ info.textContent = d.total ? d.index + ' / ' + d.total : 'none'; },
    onStatus: function(d){
      if (d.stopped){ up = false; srv.textContent = 'rs3 :' + port + ' stopped'; }
      else if (d.lost){ up = false; srv.textContent = d.restarting ? 'rs3 restarting' : 'rs3 :' + port + ' no link'; }
      else { up = true; monitors = d.monitors || 0; srv.textContent = 'rs3 :' + port + (d.pages != null ? ' - ' + d.pages + ' open' : ''); }
      show();
    },
    onBusy: function(d){ busy = !!d.on; show(); },
    onNotice: function(d){ say(d.text, d.bad); }
  };
});
