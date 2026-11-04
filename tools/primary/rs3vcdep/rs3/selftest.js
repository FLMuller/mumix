// selftest.js -- added to a page only when its address has ?selftest=1. It plays the signals a
// user would cause (the page's own code does it: nothing drives the mouse or keyboard), checks
// what the blocks did, and writes one line to the console:  SELFTEST <page> ok|FAIL {results}
RS.selftest = function(){
  var sleep = function(ms){ return new Promise(function(r){ setTimeout(r, ms); }); };
  var q = function(sel){ return document.querySelector(sel); };
  var qa = function(sel){ return document.querySelectorAll(sel); };
  var res = {};
  function check(name, ok){ res[name] = !!ok; }
  async function until(fn, ms){
    var end = Date.now() + (ms || 4000);
    while (Date.now() < end){ try { if (fn()) return true; } catch (e) {} await sleep(50); }
    return false;
  }
  async function viewer(){
    check('code shows lines', await until(function(){ return qa('.clines .ln').length > 0; }));
    check('methods listed', await until(function(){ return qa('.mrow').length > 0; }));
    var rows = qa('.mrow'), lastLine = rows.length ? +rows[rows.length - 1].querySelector('.mline').textContent : 1;
    RS.emit('linenoClicked', {lineno: lastLine + 1, where: 1});
    check('methods marks a method', await until(function(){ return q('.mrow.cur'); }));
    RS.emit('selectfunk', {lineno: lastLine, where: 1});
    await sleep(100);
    check('code scrolled', q('.clines').scrollTop > 0 || lastLine < 30);
    RS.emit('searchtext', {text: 'def', mode: 'text', where: 1});
    check('search counts', await until(function(){ return /\d+ \/ \d+/.test(q('.scount').textContent); }));
    RS.emit('commentline', {path: PAGE.panes.length ? q('.codeview .cpath').title : '', base: 'x', line: 3, where: 1});
    check('editbox ready', await until(function(){ return /new comment above line 3/.test(q('.etarget').textContent); }));
    RS.emit('withlineno', {on: false});
    check('line numbers off', !!q('.codeview.nonos'));
    RS.emit('closefile', {path: q('.codeview .cpath').title, where: 1});
    check('wiped on closefile', await until(function(){ return qa('.clines .ln').length === 0; }));
  }
  async function monitor(){
    check('status shows the port', await until(function(){ return q('td[data-k="port"]').textContent == PAGE.port; }));
    check('log has lines', await until(function(){ return qa('.lrow').length > 0; }));
    check('tree has files', await until(function(){ return qa('.ftree a.ff').length > 0; }));
    var before = qa('.ftree a.ff').length;
    RS.emit('searchtext', {text: 'rs3', mode: 'files', where: 1});
    await sleep(100);
    check('tree filtered', qa('.ftree a.ff').length < before && qa('.ftree a.ff').length > 0);
    RS.emit('searchtext', {text: '', mode: 'files', where: 1});
    RS.emit('searchtext', {text: 'started', mode: 'log', where: 1});
    await sleep(100);
    check('log filtered', qa('.lrow:not([hidden])').length > 0 && qa('.lrow:not([hidden])').length <= qa('.lrow').length);
  }
  async function tabs(){
    check('tree has files', await until(function(){ return qa('.ftree a.ff.code').length > 1; }));
    var a = qa('.ftree a.ff.code'), p0 = a[0].dataset.p, p1 = a[1].dataset.p;
    RS.emit('openfile', {path: p0, where: 1});
    check('first tab opens', await until(function(){ return qa('.ttab').length === 1 && qa('.clines .ln').length > 0; }));
    RS.emit('openfile', {path: p1, where: 1});
    check('second tab opens', await until(function(){ return qa('.ttab').length === 2; }));
    check('tree marks both', await until(function(){ return qa('.ftree a.ff.on').length === 2; }));
    RS.emit('openfile', {path: p0, where: 1});
    check('switch back to the first', await until(function(){ return q('.ttab.on').title === p0; }));
    check('methods follow the tab', await until(function(){ return qa('.mrow').length > 0; }));
    RS.emit('closefile', {path: p0, where: 1});
    check('tab removed', await until(function(){ return qa('.ttab').length === 1; }));
    check('tree unmarks it', await until(function(){ return qa('.ftree a.ff.on').length === 1; }));
    q('.ttx').click();
    check('close button removes the last tab', await until(function(){ return qa('.ttab').length === 0; }));
    check('tree has no marks left', await until(function(){ return qa('.ftree a.ff.on').length === 0; }));
  }
  (PAGE.address === '/reportserver' ? monitor() : PAGE.panes.some(function(p){ return p.block === 'toptabs'; }) ? tabs() : viewer()).then(function(){
    var bad = Object.keys(res).filter(function(k){ return !res[k]; });
    var line = 'SELFTEST ' + PAGE.address + ' ' + (bad.length ? 'FAIL ' + bad.join(', ') : 'ok') + ' ' + JSON.stringify(res);
    console.log(line);
    document.title = line;
  }).catch(function(e){ console.log('SELFTEST ' + PAGE.address + ' ERROR ' + e); document.title = 'SELFTEST ERROR ' + e; });
};
