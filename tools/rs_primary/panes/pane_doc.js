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
  function own(el){ return !el.closest('.rslayout'); };         // the layouts of blocks a page's html holds are not the doc's own
  aDOM.querySelector = function(sel){ return Array.prototype.filter.call(box.querySelectorAll(sel), own)[0] || null; };
  aDOM.querySelectorAll = function(sel){ return Array.prototype.filter.call(box.querySelectorAll(sel), own); };
  aDOM.getElementsByClassName = function(name){ return box.getElementsByClassName(name); };
  aDOM.getElementsByTagName = function(name){ return box.getElementsByTagName(name); };
  aDOM.createElement = function(tag){ return document.createElement(tag); };
  aDOM.createTextNode = function(text){ return document.createTextNode(text); };
  aDOM.addEventListener = function(type, fn){
    if (type === 'DOMContentLoaded' || type === 'load') ready.push(fn);
    else box.addEventListener(type, fn);
  };
  aDOM.removeEventListener = function(type, fn){ box.removeEventListener(type, fn); };
  // the notes of a page that is an html file (rs3microDB): a page asks for its notes, says which line or note the user clicked (the editbox of the page
  // takes it), and hears when a note was written
  var saved = [];
  var source = box.getAttribute('data-source') || '';                  // the ./ path of the html file this box shows (a file page), else ''
  aDOM.noteline = function(file, line){ ctx.emit('noteline', {file: String(file), line: +line, source: source}); };
  aDOM.noteselect = function(note){ ctx.emit('noteselect', {file: String(note.file), line: +note.line, code: String(note.code), text: String(note.text), who: String(note.who || ''), source: source}); };
  aDOM.notes = function(file, fn){
    ctx.verb('note_list', file === undefined ? {source: source} : {file: String(file), source: source}).then(function(r){ fn(r.ok ? r.notes : [], r.ok ? '' : (r.error || 'refused')); })
       .catch(function(e){ fn([], e.message); });
  };
  aDOM.onnotesaved = function(fn){ saved.push(fn); };
  // maths: a page that writes formulas as \( ... \) (inline) or $$ ... $$ (display) asks for them to be set: aDOM.typeset() loads MathJax (the one script, from cdnjs, the main
  // page's own) the first time, and sets the formulas of this box. A page that never calls it loads nothing.
  var MATHJAX_URL = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-svg.js';
  function typeset(){
    if (!box.offsetParent){ window.setTimeout(typeset, 400); return; }        // a box that is not shown (a tab behind) is set when it is: MathJax measures the text it sets in
    if (window.MathJax && window.MathJax.typesetPromise){ window.MathJax.typesetPromise([box]).catch(function(e){ console.error('rs3 doc: mathjax:', e); }); return; }
    if (!window.MathJax) window.MathJax = {tex: {inlineMath: [['\\(', '\\)']], displayMath: [['$$', '$$']]}, svg: {fontCache: 'global'}, startup: {typeset: false}};
    if (document.getElementById('rs3mathjax')) { window.setTimeout(typeset, 300); return; }         // loading: try again
    var s = document.createElement('script');
    s.id = 'rs3mathjax'; s.src = MATHJAX_URL; s.async = true; s.onload = function(){ window.setTimeout(typeset, 50); };
    document.head.appendChild(s);
  }
  aDOM.typeset = typeset;
  // a picture of the page (a data: image) in a browser tab of its own at full size: a data: address cannot be opened as a page, so it is made a blob first
  aDOM.opentab = function(src){
    var s = String(src), m = /^data:([^;,]+);base64,(.*)$/.exec(s);
    if (!m) return;
    var bin = window.atob(m[2]), bytes = new Uint8Array(bin.length), k;
    for (k = 0; k < bin.length; k++) bytes[k] = bin.charCodeAt(k);
    window.open(window.URL.createObjectURL(new Blob([bytes], {type: m[1]})), '_blank');
  };
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
    if (own(t) && t.tHead && t.tHead.rows.length && t.tBodies.length && !t.querySelector('.sortbtn')) RS.table.make(t);
  });

  // ---- the layouts of blocks that the html holds (div.rslayout, made by the server) take the height the window has left ----
  // One measure for every case: a layout is as high as the space from its top to the bottom of the element the box scrolls in,
  // at least 200 px (the css), less what follows it in the box (a margin, another element); the box's own bottom padding is given up while a layout is shown. The panes inside it then scroll by themselves,
  // and the box scrolls only when what comes before a layout is taller than the window. It is made when the box is set up, when the scrolling element changes size, and when
  // something inside the box is shown or hidden (a tab, a panel); a layout that is not displayed is left until it is. No part of
  // the html is marked, so a table, a grid or a panel that starts hidden need no case of their own.
  function scroller(){
    for (var el = box.parentNode; el && el !== document.body; el = el.parentNode){
      var overflow = window.getComputedStyle(el).overflowY;
      if (overflow === 'auto' || overflow === 'scroll') return el;
    }
    return document.documentElement;
  }
  var LEAST = 200, fitting = false;
  function fit(){
    fitting = false;
    var holder = scroller(), room = holder.clientHeight, seen = holder.getBoundingClientRect().top;
    var shown = Array.prototype.filter.call(box.querySelectorAll('.rslayout'), function(place){
      return place.offsetParent;                                          // not displayed: the next show makes it
    });
    box.style.paddingBottom = shown.length ? '0px' : '';                // a page that ends in a layout has no empty strip under it; one that shows none keeps its own
    shown.forEach(function(place){
      var top = place.getBoundingClientRect().top - seen + (holder === document.documentElement ? 0 : holder.scrollTop);
      place.style.height = Math.max(LEAST, Math.floor(room - top)) + 'px';
    });
    var last = shown[shown.length - 1], over = last ? holder.scrollHeight - holder.clientHeight : 0;
    if (over > 0) last.style.height = Math.max(LEAST, last.offsetHeight - over) + 'px';     // what follows the layout (the box's padding, a margin) is left room
  }
  function refit(){ if (!fitting){ fitting = true; window.requestAnimationFrame(fit); } }
  if (box.querySelector('.rslayout')){
    fit();
    new ResizeObserver(refit).observe(scroller());
    new MutationObserver(refit).observe(box, {attributes: true, attributeFilter: ['hidden', 'class'], subtree: true});
  }

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
      if (tag !== 'SCRIPT' && tag !== 'STYLE' && tag !== 'TEMPLATE' && n.nodeValue.trim() && own(n.parentNode)) out.push(n);
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
    onNotesaved: function(d){ saved.forEach(function(fn){ try { fn(d); } catch (e) { console.error('rs3 doc:', e); } }); },
    onSearchnext: function(d){ if (d.mode === 'text') show(at + 1); },
    onSearchprev: function(d){ if (d.mode === 'text') show(at - 1); },
    onSearchhome: function(d){ if (d.mode === 'text' && home !== null) cell.scrollTop = home; }
  };
});
