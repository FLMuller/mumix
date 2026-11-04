// manager.js -- the hidden manager of every rs3 page: it makes the blocks, routes their signals, owns the
// link to the server, and opens and closes the browser tabs of files.
//
// A block is registered by its script:  RS.pane('code', function(ctx){ ...; return {onOpenfile: fn, ...}; })
// ctx = {loc, block, where, el, page, config,
//        emit(name, data)         announce a signal: every block with an  on<Name>  handler gets it
//        verb(name, fields)       ask the server; a Promise of its reply (fields get the page's hash)
//        whenLinked(fn)           run fn when the link to the server is up (now, if it is)
//        linked()                 is the link up?}
// A signal is  name  and  data  (an object). The emitter writes  openfile , a receiver defines
// onOpenfile . A handler may respond but cannot avoid, change or hold a signal: its return value is
// ignored, and a handler that throws is reported to the console and the others still get the signal.
// Signals sent while another is being delivered wait their turn, so every block sees them in order.
// A signal's data may hold  where : the number of the pane it is for (the nth code/toptabs pane, the nth
// methods pane ...). A block with a number acts only on a signal for its number (or for none);
// ftv, serverstatus and log take them all. where 0 is a new browser tab.
//
// The manager's own signals:   newtabopened {path}  after this page has loaded (and after a tab was opened)
//                              closingmaintab {path}  just before a tab closes
//                              status {...} / log {rows|reset}  what the server says (pulse, once a second)
//   it listens to              closemaintab           (a button): closing, then the window closes
//                              openfile / closefile   when no pane takes a file: a new tab
// Server commands to the page (snap, trigger) are answered here.
var RS = (function(){
  var panes = {}, inst = [], queue = [], draining = false, tabs = {}, started = false;
  var link = {ws: null, up: false, waiting: [], hello: false, row: 0, bye: '', pulsing: false, ever: false};
  var NOWHERE = {ftv: 1, serverstatus: 1, log: 1, doc: 1};
  var cap = function(s){ return s.charAt(0).toUpperCase() + s.slice(1); };

  // ---- signals ----
  function wanted(it, name, data){
    var h = it.h && it.h['on' + cap(name)];
    if (typeof h !== 'function') return null;
    if (NOWHERE[it.block] || data.where == null) return h;
    return it.where === data.where ? h : null;
  }
  function deliver(name, data){
    inst.forEach(function(it){
      var h = wanted(it, name, data);
      if (!h) return;
      try { h.call(it.h, data); } catch (e) { console.error('rs3: ' + it.loc + ' on' + cap(name) + ':', e); }
    });
  }
  function emit(name, data){
    queue.push({name: name, data: data || {}});
    if (draining) return;
    draining = true;
    try {
      while (queue.length){
        var s = queue.shift();
        manage(s.name, s.data);
        deliver(s.name, s.data);
      }
    } finally { draining = false; }
  }
  function takers(data){                // the panes that take a file: code/toptabs with onOpenfile, for this number
    return inst.filter(function(it){
      return (it.block === 'code' || it.block === 'toptabs') && it.h && it.h.onOpenfile &&
             (data.where == null || it.where === data.where);
    });
  }
  function manage(name, data){          // what the manager itself does with a signal, before the blocks get it
    if (name === 'openfile' && (data.where === 0 || !takers(data).length)) openTab(data.path);
    else if (name === 'closefile' && tabs[data.path]) closeTab(data.path);
    else if (name === 'closemaintab') closeMain();
  }

  // ---- browser tabs of files ----
  function tabUrl(path){
    return /\.(html|result)$/i.test(path) ? encodeURI(path.slice(1)) : '/code/' + encodeURI(path.slice(2));
  }
  function openTab(path){
    if (!path) return;
    var old = tabs[path];
    if (old && !old.closed){ old.focus(); return; }
    var win = window.open(tabUrl(path), 'rs3:' + path);
    if (!win){ console.warn('rs3: the browser blocked the new tab for ' + path); return; }
    tabs[path] = win;
    emit('newtabopened', {path: path});
  }
  function closeTab(path){
    var win = tabs[path];
    delete tabs[path];
    if (!win) return;
    emit('closingmaintab', {path: path});
    try { win.close(); } catch (e) {}
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
      if (tabs[path].closed){
        delete tabs[path];
        emit('closingmaintab', {path: path});
        emit('closefile', {path: path, where: 0});
      }
    });
  }

  // ---- the link to the server ----
  function send(obj){ link.ws.send(JSON.stringify(obj)); }
  function verb(name, fields){
    return new Promise(function(resolve, reject){
      if (!link.up){ reject(new Error('no link to the server')); return; }
      link.waiting.push({resolve: resolve, reject: reject});
      send(Object.assign({do: name, hash: PAGE.hash}, fields || {}));
    });
  }
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
      var cell = bar.previousElementSibling, vertical = bar.classList.contains('v'), at = null;
      if (!cell) return;
      bar.addEventListener('pointerdown', function(e){
        var box = cell.getBoundingClientRect();
        at = {id: e.pointerId, from: vertical ? e.clientX : e.clientY, size: vertical ? box.width : box.height};
        bar.setPointerCapture(e.pointerId);
        bar.classList.add('on');
        e.preventDefault();
      });
      bar.addEventListener('pointermove', function(e){
        if (!at || at.id !== e.pointerId) return;
        var now = at.size + (vertical ? e.clientX : e.clientY) - at.from;
        cell.style.flex = '0 0 ' + Math.max(40, now) + 'px';
      });
      function end(e){ if (at && at.id === e.pointerId){ at = null; bar.classList.remove('on'); } }
      bar.addEventListener('pointerup', end);
      bar.addEventListener('pointercancel', end);
    });
  }

  // ---- start ----
  function start(){
    var host = function(loc){ return document.querySelector('.cell[data-loc="' + loc + '"]'); };
    PAGE.panes.forEach(function(p){
      var ctor = panes[p.block], el = host(p.loc), it = {loc: p.loc, block: p.block, where: p.where, el: el, h: {}};
      inst.push(it);
      if (p.host) return;               // a code block on a page with tabs is only the place the tabs show their file
      if (!ctor || !el){ console.warn('rs3: no script for block ' + p.block); return; }
      var ctx = {loc: p.loc, block: p.block, where: p.where, el: el, page: PAGE, config: PAGE.config,
                 emit: emit, verb: verb, whenLinked: whenLinked, linked: function(){ return link.up; }, make: make};
      it.h = ctor(ctx) || {};
    });
    started = true;
    dragging();
    connect();
    window.setInterval(function(){ pulse(); watchTabs(); }, 1000);
    window.addEventListener('beforeunload', function(){ emit('closingmaintab', {path: PAGE.address}); });
    emit('newtabopened', {path: PAGE.address});
  }
  function make(block, el, extra){      // a pane inside a pane (toptabs makes code panes)
    var ctor = panes[block];
    var ctx = Object.assign({loc: block, block: block, where: 0, el: el, page: PAGE, config: PAGE.config,
                             emit: emit, verb: verb, whenLinked: whenLinked, linked: function(){ return link.up; },
                             make: make}, extra || {});
    return ctor ? (ctor(ctx) || {}) : {};
  }
  var DOCS = {};                         // the script of each doc block, run with aDOM = the block's element
  panes.doc = function(ctx){ if (DOCS[ctx.loc]) DOCS[ctx.loc](ctx.el); return {}; };
  return {pane: function(name, ctor){ panes[name] = ctor; }, start: start, emit: emit, cap: cap,
          doc: function(loc, fn){ DOCS[loc] = fn; }};
})();
