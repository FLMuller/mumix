// manager.js -- the hidden manager of every rs3 page: it makes the blocks, routes their signals, owns the
// link to the server, and opens and closes the browser tabs of files.
//
// A block is registered by its script:  RS.pane('code', function(ctx){ ...; return {onShowfile: fn, ...}; })
// ctx = {loc, block, el, page, config,
//        emit(name, data)         announce a signal: every block with an  on<Name>  handler gets it
//        verb(name, fields)       ask the server; a Promise of its reply (fields get the page's hash)
//        whenLinked(fn)           run fn when the link to the server is up (now, if it is)
//        linked()                 is the link up?}
// A signal is  name  and  data  (an object). The emitter writes  showfile , a receiver defines
// onShowfile . A handler may respond but cannot avoid, change or hold a signal: its return value is
// ignored, and a handler that throws is reported to the console and the others still get the signal.
// Signals sent while another is being delivered wait their turn, so every block sees them in order.
// Who gets a signal. Three ways (SIGNALS.md says which a signal uses):
//   to           the data holds  to: [locators]  : only those blocks (a selectfunk goes back to the code that was shown)
//   nearest      the names in PAGE.routed (commentline, commentselect, saved): of each kind of block that listens, the
//                one nearest the sender in the layout: the most groups [...] shared with it; of those the first after
//                the sender, round the end; or the blocks of the sender's  blk{a,b}  list in the layout string
//   everyone     all the others: every block with the handler
// A name that starts with mng goes only to this manager: it decides who gets what, and no block listens to it.
//
// Files.  ftv emits  mngshowfile {path, show, to?}  ; the manager sends  showfile {path, show}  to the blocks that take
// files (PAGE.panes[].takes): those the layout list (or  to ) names, else a container (a block that holds another: toptabs
// holds code) before a lone block, else a new browser tab. show false closes. A block that shows or stops showing
// a file says so with  showcode {path, loc, on} , to everyone (the manager does it for a browser tab: loc 'tab').
//
// The manager's own signals:   newtabopened {path}  after this page has loaded (and after a tab was opened)
//                              closingmaintab {path}  just before a tab closes
//                              showcode {path, loc: 'tab', on}  a browser tab of a file opened or closed
//                              status {...} / log {rows|reset}  what the server says (pulse, once a second)
//   it listens to              closemaintab           (a button): closing, then the window closes
//                              mngshowfile            ftv: who gets the file
// Server commands to the page (snap, trigger) are answered here.
var RS = (function(){
  var panes = {}, inst = [], queue = [], draining = false, tabs = {}, started = false, shownAt = {};    // shownAt[path]: {loc: true}
  var link = {ws: null, up: false, waiting: [], hello: false, row: 0, bye: '', pulsing: false, ever: false};
  var cap = function(s){ return s.charAt(0).toUpperCase() + s.slice(1); };

  // ---- signals ----
  function paneOf(loc){ return PAGE.panes.filter(function(p){ return p.loc === loc; })[0]; }
  function listeners(name){
    return inst.filter(function(it){ return it.h && typeof it.h['on' + cap(name)] === 'function'; });
  }
  function nearest(list, from){         // of each kind of block: the listener sharing most groups with the sender; a tie: the first after it, round the end
    var me = paneOf(from), order = PAGE.panes.map(function(p){ return p.loc; }), here = order.indexOf(from), by = {};
    list.forEach(function(it){
      if (it.loc === from) return;
      var p = paneOf(it.loc), n = 0, away = (order.indexOf(it.loc) - here + order.length) % order.length;
      while (me && n < me.at.length && n < p.at.length && me.at[n] === p.at[n]) n++;
      var best = by[it.block];
      if (!best || n > best.n || (n === best.n && away < best.away)) by[it.block] = {it: it, n: n, away: away};
    });
    return Object.keys(by).map(function(block){ return by[block].it; });
  }
  function receivers(name, data, from){
    var list = listeners(name), to = data.to, own = paneOf(from);
    if (!to && (PAGE.routed || []).indexOf(name) >= 0){
      if (!own || !own.to.length) return nearest(list, from);
      to = own.to;                      // the sender's  blk{a,b}  in the layout string
    }
    return to ? list.filter(function(it){ return to.indexOf(it.loc) >= 0; }) : list;
  }
  function deliver(name, data, from){
    receivers(name, data, from).forEach(function(it){
      try { it.h['on' + cap(name)].call(it.h, data); } catch (e) { console.error('rs3: ' + it.loc + ' on' + cap(name) + ':', e); }
    });
  }
  function emit(name, data, from){
    queue.push({name: name, data: data || {}, from: from});
    if (draining) return;
    draining = true;
    try {
      while (queue.length){
        var s = queue.shift();
        manage(s.name, s.data, s.from);
        deliver(s.name, s.data, s.from);
      }
    } finally { draining = false; }
  }
  function showFile(d, from){           // mngshowfile: who gets the file, or who is to stop showing it
    var path = d.path, show = d.show !== false, own = paneOf(from), to = d.to;
    if (!path) return;
    if (!to && own && own.to.length) to = own.to;
    var takes = listeners('showfile').map(function(it){ return it.loc; });
    function send(locs){ locs.forEach(function(loc){ deliver('showfile', {path: path, show: show, to: [loc]}, null); }); }
    if (!show){                         // where it is shown now (and the lists, when given)
      Object.keys(shownAt[path] || {}).forEach(function(loc){
        if (to === 'tab' ? loc !== 'tab' : to && to.indexOf(loc) < 0) return;
        if (loc === 'tab') closeTab(path); else send([loc]);
      });
      return;
    }
    if (to === 'tab'){ openTab(path); return; }
    var panes = PAGE.panes.filter(function(p){ return p.takes && !p.hosted && takes.indexOf(p.loc) >= 0; });
    if (to) panes = panes.filter(function(p){ return to.indexOf(p.loc) >= 0; });
    else {
      var boxes = panes.filter(function(p){ return p.holds; });          // a container before a lone block
      panes = (boxes.length ? boxes : panes).slice(0, 1);
    }
    if (panes.length) send(panes.map(function(p){ return p.loc; }));
    else if (!to) openTab(path);
    else console.warn('rs3: no block of ' + to.join(',') + ' takes files');
  }
  function manage(name, data, from){    // what the manager itself does with a signal, before the blocks get it
    if (name === 'mngshowfile') showFile(data, from);
    else if (name === 'showcode'){
      var at = shownAt[data.path] || (shownAt[data.path] = {});
      if (data.on) at[data.loc] = true; else delete at[data.loc];
    }
    else if (name === 'closemaintab') closeMain();
    else if (name === 'showpane') showPane(data.block, data.on);
    else if (name === 'withlineno') document.documentElement.classList.toggle('nolinenos', !data.on);
    else if (name === 'withwrap') document.documentElement.classList.toggle('nowrap', !data.on);
    else if (name === 'withconfig') applyConfig();
  }
  function applyConfig(){               // the settings are the page's: every code view, tab and block reads them from here
    var c = PAGE.config, root = document.documentElement;
    root.style.setProperty('--usercolor', c.color || '#e8650f');
    root.style.setProperty('--cfont', c.font || 'Consolas');
    root.style.setProperty('--csize', (c.size || 12) + 'px');
    root.style.setProperty('--ctab', c.tabwidth || 4);
    root.classList.toggle('nolinenos', c.linenos === false);
    root.classList.toggle('nowrap', !c.wrap);
  }

  // ---- panes that can be hidden: the door buttons ----
  var shown = {};                       // block -> false while its pane is shut
  var SHUT = 22;                        // px: a shut pane is a strip this wide, with its door in it
  function showPane(block, on, keep){   // shut: the cell shrinks to the strip (its door and its drag edge stay), the rest fills
    shown[block] = !!on;                // open: the width it had, or (keep) the one a drag is setting
    PAGE.panes.filter(function(p){ return p.block === block; }).forEach(function(p){
      var cell = document.querySelector('.cell[data-loc="' + p.loc + '"]');
      if (!cell) return;
      var isShut = cell.classList.contains('shut');
      if (!on && !isShut){
        cell.dataset.was = cell.style.flex || '';
        cell.style.flex = '0 0 ' + SHUT + 'px';
      } else if (on && isShut && !keep){
        cell.style.flex = cell.dataset.was || '';
      }
      cell.classList.toggle('shut', !on);
    });
    Array.prototype.forEach.call(document.querySelectorAll('.door[data-block="' + block + '"]'), function(b){
      b.classList.toggle('off', !on);
    });
  }
  function blockOf(cell){
    var p = PAGE.panes.filter(function(x){ return x.loc === cell.dataset.loc; })[0];
    return p && p.block;
  }
  var DOORS = [['ftv', '&#9707;', 'the files'], ['methods', '&#9707;', 'the methods']];       // one door symbol: the title says which pane
  function doors(el, only){             // buttons in el for the hideable panes this page has (only: these blocks)
    DOORS.forEach(function(k){
      if (only && only.indexOf(k[0]) < 0) return;
      if (!PAGE.panes.some(function(p){ return p.block === k[0]; })) return;
      var b = document.createElement('button');
      b.className = 'door' + (shown[k[0]] === false ? ' off' : '');
      b.dataset.block = k[0];
      b.title = 'show or hide ' + k[2];
      b.innerHTML = k[1];
      b.onclick = function(){ emit('showpane', {block: k[0], on: shown[k[0]] === false}); };
      el.appendChild(b);
    });
  }

  // ---- browser tabs of files ----
  function tabUrl(path){                // a report page is a doc block in a layout of its own, so it has the status bar
    var rel = path.slice(2).split('/').map(encodeURIComponent).join('/');
    return /\.(html|result)$/i.test(path) ? '/?layout=[doc]&doc=' + rel : '/code/' + encodeURI(path.slice(2));
  }
  function openTab(path){               // tabs[path] = {win}; a blocked tab is no file shown: nothing is announced
    if (!path) return;
    var old = tabs[path];
    if (old && !old.win.closed){ old.win.focus(); return; }
    var win = window.open(tabUrl(path), 'rs3:' + path);
    if (!win){
      console.warn('rs3: the browser blocked the new tab for ' + path);
      return;
    }
    tabs[path] = {win: win};
    emit('showcode', {path: path, loc: 'tab', on: true});
    emit('newtabopened', {path: path});
  }
  function closeTab(path){
    var tab = tabs[path];
    delete tabs[path];
    if (!tab) return;
    emit('closingmaintab', {path: path});
    emit('showcode', {path: path, loc: 'tab', on: false});
    try { tab.win.close(); } catch (e) {}
  }
  function closeMain(){                 // a button asked: tell the blocks, then the window goes
    emit('closingmaintab', {path: PAGE.address});
    window.setTimeout(function(){
      window.close();                   // works for a window a script opened; the message stays for the rest
      document.title = 'closed - ' + document.title;
    }, 50);
  }
  function watchTabs(){                 // a tab closed by hand: the file is closed
    Object.keys(tabs).forEach(function(path){
      if (tabs[path].win.closed){
        delete tabs[path];
        emit('closingmaintab', {path: path});
        emit('showcode', {path: path, loc: 'tab', on: false});
      }
    });
  }

  // ---- the link to the server ----
  function send(obj){ link.ws.send(JSON.stringify(obj)); }
  function verb(name, fields){
    return new Promise(function(resolve, reject){
      if (!link.up){ reject(new Error('no link to the server')); return; }
      var quiet = name === 'pulse';       // the pulse is every second: it does not make the status bar turn
      if (!quiet && !out++) emit('busy', {on: true});
      var done = function(){ if (!quiet && !--out) emit('busy', {on: false}); };
      link.waiting.push({resolve: function(m){ done(); resolve(m); }, reject: function(e){ done(); reject(e); }});
      send(Object.assign({do: name, hash: PAGE.hash}, fields || {}));
    });
  }
  var out = 0;                            // requests to the server that are not answered yet
  function drop(error){
    var w = link.waiting;
    link.waiting = [];
    w.forEach(function(x){ x.reject(error); });
  }
  function command(m){                  // the server asks this page for something (snap, trigger)
    var reply = {re: m.id, ok: false};
    if (m.do === 'trigger'){
      var el = m.sel ? document.querySelector(m.sel) : null;
      if (el){ el.click(); reply = {re: m.id, ok: true}; } else reply.error = 'no element ' + m.sel;
    } else reply.error = m.do + ' is not built into rs3 pages yet';
    send(reply);
  }
  function newServer(){                 // the server was restarted: it serves this page again (reload: new code and styles), or it is gone
    fetch(location.pathname + location.search, {cache: 'no-store'}).then(function(r){
      if (r.ok) location.reload();
      else emit('notice', {text: 'the server was restarted and no longer has this page: open it again', bad: true});
    }).catch(function(){});
  }
  function connect(){
    var ws = new WebSocket('ws://127.0.0.1:' + PAGE.port + '/');
    link.ws = ws;
    ws.onopen = function(){
      send({do: 'hello', url: PAGE.address});
    };
    ws.onmessage = function(e){
      var m;
      try { m = JSON.parse(e.data); } catch (x) { return; }
      if (m.bye){ link.bye = m.bye; return; }
      if (m.id && m.do){ command(m); return; }
      if (!link.up){                   // the reply to hello
        if (!m.ok){ console.warn('rs3: hello refused: ' + m.error); return; }
        link.up = true; link.row = 0; link.bye = '';
        if (link.boot && m.boot !== link.boot) newServer();         // back to a server that was restarted
        link.boot = m.boot;
        emit('log', {reset: true});
        var first = !link.ever;
        link.ever = true;
        started && pending.splice(0).forEach(function(fn){ fn(); });
        return;
      }
      var w = link.waiting.shift();
      if (w) w.resolve(m);
    };
    ws.onclose = function(){
      var was = link.up;
      link.up = false;
      drop(new Error('the link to the server closed'));
      if (link.bye === 'stop'){ emit('status', {stopped: 'stop'}); return; }
      emit('status', {lost: true, restarting: link.bye === 'restart'});
      window.setTimeout(connect, link.bye === 'restart' ? 800 : 1500);
    };
    ws.onerror = function(){};
  }
  var pending = [];
  function whenLinked(fn){ if (link.up) fn(); else pending.push(fn); }
  function listening(name){ return inst.some(function(it){ return it.h && typeof it.h['on' + cap(name)] === 'function'; }); }
  function pulse(){
    if (!link.up || link.pulsing || !(listening('status') || listening('log'))) return;
    link.pulsing = true;
    verb('pulse', {since: link.row}).then(function(r){
      link.pulsing = false;
      if (!r.ok) return;
      emit('status', r.status);
      if (r.rows && r.rows.length){
        link.row = r.rows[r.rows.length - 1][0];
        emit('log', {rows: r.rows});
      }
    }).catch(function(){ link.pulsing = false; });
  }

  // ---- draggable edges ----
  function dragging(){
    Array.prototype.forEach.call(document.querySelectorAll('.drag'), function(bar){
      var before = bar.classList.contains('before');        // the bar of a last item is before it, and drags it the other way
      var cell = before ? bar.nextElementSibling : bar.previousElementSibling, vertical = bar.classList.contains('v'), at = null, opening = false;
      if (!cell) return;
      bar.addEventListener('pointerdown', function(e){
        opening = cell.classList.contains('shut');      // a drag on the edge of a shut pane opens it to the width dragged
        if (opening) showPane(blockOf(cell), true, true);
        var box = cell.getBoundingClientRect();
        at = {id: e.pointerId, from: vertical ? e.clientX : e.clientY, size: vertical ? box.width : box.height};
        bar.setPointerCapture(e.pointerId);
        bar.classList.add('on');
        e.preventDefault();
      });
      bar.addEventListener('pointermove', function(e){
        if (!at || at.id !== e.pointerId) return;
        var moved = (vertical ? e.clientX : e.clientY) - at.from;
        var now = at.size + (before ? -moved : moved);
        cell.style.flex = '0 0 ' + Math.max(40, now) + 'px';
      });
      function end(e){
        if (!at || at.id !== e.pointerId) return;
        at = null;
        bar.classList.remove('on');
        var box = cell.getBoundingClientRect();
        if (opening && (vertical ? box.width : box.height) < 60){     // only a click on the edge: open to the old width
          cell.style.flex = cell.dataset.was || '';           // (the shut flag is already off: only the width is back)
        }
        opening = false;
      }
      bar.addEventListener('pointerup', end);
      bar.addEventListener('pointercancel', end);
    });
  }

  // ---- start ----
  function start(){
    var host = function(loc){ return document.querySelector('.cell[data-loc="' + loc + '"]'); };
    PAGE.panes.forEach(function(p){
      var ctor = panes[p.block], el = host(p.loc), it = {loc: p.loc, block: p.block, el: el, h: {}};
      inst.push(it);
      if (p.hosted) return;             // a code block on a page with tabs is only the place the tabs show their file
      if (!ctor || !el){ console.warn('rs3: no script for block ' + p.block); return; }
      var ctx = {loc: p.loc, block: p.block, el: el, page: PAGE, config: PAGE.config,
                 emit: function(name, data){ emit(name, data, p.loc); },
                 verb: verb, whenLinked: whenLinked, linked: function(){ return link.up; }, make: make};
      it.h = ctor(ctx) || {};
    });
    started = true;
    applyConfig();
    PAGE.panes.forEach(function(p){     // the strip a pane leaves when it is shut: its door, always visible
      var cell = host(p.loc);
      if (!cell || !DOORS.some(function(k){ return k[0] === p.block; })) return;
      var strip = document.createElement('div');
      strip.className = 'shutdoor';
      cell.appendChild(strip);
      doors(strip, [p.block]);
    });
    dragging();
    connect();
    window.setInterval(function(){ pulse(); watchTabs(); }, 1000);
    window.addEventListener('beforeunload', function(){ emit('closingmaintab', {path: PAGE.address}); });
    emit('newtabopened', {path: PAGE.address});
  }
  function make(block, el, extra){      // a pane inside a pane (toptabs makes code panes)
    var ctor = panes[block];
    var ctx = Object.assign({loc: block, block: block, el: el, page: PAGE, config: PAGE.config,
                             verb: verb, whenLinked: whenLinked, linked: function(){ return link.up; },
                             make: make}, extra || {});
    ctx.emit = function(name, data){ emit(name, data, ctx.loc); };       // a pane inside a pane speaks as the pane that made it
    return ctor ? (ctor(ctx) || {}) : {};
  }
  return {pane: function(name, ctor){ panes[name] = ctor; }, start: start, emit: function(name, data){ emit(name, data, null); },
          cap: cap, doors: doors};
})();
