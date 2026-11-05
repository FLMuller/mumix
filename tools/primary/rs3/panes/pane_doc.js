// pane_doc.js -- the doc block's run time (see pane_doc.py for its signals): the box a script runs in, and the search of its text.
RS.pane('doc', function(ctx){
  var cell = ctx.el, box = cell.querySelector('.doc'), loc = ctx.loc, page = ctx.page;
  var setup = RS.docs && RS.docs[loc];
  var ready = [], hits = [], at = -1, home = null;

  // ---- aDOM: the box, and nothing outside it ----
  var aDOM = {currentdiv: box, title: page.title, body: box, documentElement: box};
  function shut(name){ return {get: function(){ throw new Error('a doc cannot reach ' + name + ': it lives in its box'); },
                              enumerable: false}; }
  ['parent', 'parentNode', 'parentElement', 'ownerDocument', 'defaultView', 'top', 'opener', 'frames', 'window',
   'location', 'cookie', 'domain', 'referrer', 'head', 'forms', 'scripts', 'activeElement'].forEach(function(name){
    Object.defineProperty(aDOM, name, shut('aDOM.' + name));
  });
  aDOM.getElementById = function(id){ return box.querySelector('[id="' + String(id).replace(/(["\\])/g, '\\$1') + '"]'); };
  aDOM.querySelector = function(sel){ return box.querySelector(sel); };
  aDOM.querySelectorAll = function(sel){ return box.querySelectorAll(sel); };
  aDOM.getElementsByClassName = function(name){ return box.getElementsByClassName(name); };
  aDOM.getElementsByTagName = function(name){ return box.getElementsByTagName(name); };
  aDOM.createElement = function(tag){ return document.createElement(tag); };
  aDOM.createTextNode = function(text){ return document.createTextNode(text); };
  aDOM.addEventListener = function(type, fn){
    if (type === 'DOMContentLoaded' || type === 'load') ready.push(fn);
    else box.addEventListener(type, fn);
  };
  aDOM.removeEventListener = function(type, fn){ box.removeEventListener(type, fn); };
  aDOM.on = function(types, list){       // the inline handlers: one listener of the box for each kind, finding the element
    types.forEach(function(type){
      var attr = 'data-aon-' + type;
      box.addEventListener(type, function(e){
        var el = e.target;
        while (el && el !== box && !(el.hasAttribute && el.hasAttribute(attr))) el = el.parentNode;
        if (el && el !== box){ var f = list[+el.getAttribute(attr)]; if (f) f.call(el, e, el); }
      }, type === 'focus' || type === 'blur');
    });
  };
  var aWindow = {
    addEventListener: function(type, fn){
      if (type === 'DOMContentLoaded' || type === 'load') ready.push(fn);
      else if (type === 'resize') window.addEventListener('resize', fn);
    }
  };
  var aLocation = Object.freeze({href: page.address, pathname: page.address.split('?')[0], search: '', hash: ''});
  var prefix = 'rs3doc:' + page.address + ':' + loc + ':';
  var aStorage = {
    getItem: function(k){ try { return window.localStorage.getItem(prefix + k); } catch (e) { return null; } },
    setItem: function(k, v){ try { window.localStorage.setItem(prefix + k, String(v)); } catch (e) {} },
    removeItem: function(k){ try { window.localStorage.removeItem(prefix + k); } catch (e) {} }
  };
  function timer(real){ return function(fn, ms){
    if (typeof fn !== 'function') throw new Error('a timer takes a function, not text');
    return real.call(window, fn, ms);
  }; }
  if (setup){
    try {
      setup(aDOM, aDOM, aWindow, aLocation, aStorage, timer(window.setTimeout), window.clearTimeout.bind(window),
            timer(window.setInterval), window.clearInterval.bind(window));
      ready.forEach(function(fn){ fn({type: 'DOMContentLoaded'}); });
    } catch (error) {
      var note = document.createElement('div');
      note.className = 'docerr';
      note.textContent = 'the script of this page stopped: ' + error.message;
      box.insertBefore(note, box.firstChild);
    }
  }
  Array.prototype.forEach.call(box.querySelectorAll('table'), function(t){      // a table with a header row gets the star and the hamburger (RS.table), unless its page made its own
    if (t.tHead && t.tHead.rows.length && t.tBodies.length && !t.querySelector('.sortbtn')) RS.table.make(t);
  });

  // ---- the search of the text of the box ----
  function clear(){
    box.querySelectorAll('mark.dochit').forEach(function(m){
      var p = m.parentNode;
      p.replaceChild(document.createTextNode(m.textContent), m);
      p.normalize();
    });
    hits = []; at = -1;
  }
  function textNodes(){
    var out = [], w = document.createTreeWalker(box, NodeFilter.SHOW_TEXT, null);
    for (var n = w.nextNode(); n; n = w.nextNode()){
      var tag = n.parentNode.nodeName;
      if (tag !== 'SCRIPT' && tag !== 'STYLE' && tag !== 'TEMPLATE' && n.nodeValue.trim()) out.push(n);
    }
    return out;
  }
  function mark(text){
    var needle = text.toLowerCase(), size = needle.length;
    textNodes().forEach(function(node){
      var value = node.nodeValue, low = value.toLowerCase(), from = 0, found = low.indexOf(needle), frag = null;
      while (found >= 0 && hits.length < 2000){
        frag = frag || document.createDocumentFragment();
        if (found > from) frag.appendChild(document.createTextNode(value.slice(from, found)));
        var m = document.createElement('mark');
        m.className = 'dochit'; m.textContent = value.slice(found, found + size);
        frag.appendChild(m); hits.push(m);
        from = found + size; found = low.indexOf(needle, from);
      }
      if (frag){
        if (from < value.length) frag.appendChild(document.createTextNode(value.slice(from)));
        node.parentNode.replaceChild(frag, node);
      }
    });
  }
  function show(k){
    if (!hits.length){ ctx.emit('searchcount', {index: 0, total: 0}); return; }
    if (at >= 0) hits[at].classList.remove('cur');
    at = (k + hits.length) % hits.length;
    hits[at].classList.add('cur');
    hits[at].scrollIntoView({block: 'center', inline: 'nearest'});
    ctx.emit('searchcount', {index: at + 1, total: hits.length});
  }
  return {
    onSearchtext: function(d){
      if (d.mode !== 'text') return;
      if (home === null) home = cell.scrollTop;      // where the box was before the search: the star goes back here
      clear();
      if (!d.text){ ctx.emit('searchcount', {index: 0, total: 0}); home = null; return; }
      mark(d.text);
      show(0);
    },
    onSearchnext: function(d){ if (d.mode === 'text') show(at + 1); },
    onSearchprev: function(d){ if (d.mode === 'text') show(at - 1); },
    onSearchhome: function(d){ if (d.mode === 'text' && home !== null) cell.scrollTop = home; }
  };
});
