// b_rs3page.js -- the test code of tests/b_rs3page.py, shipped to the js test manager (tests/jstest.html) in a bundle with the code
// to be tested (the filter language of html/table.js, pie() of pane_methods.js) and DATA: {CASES: {filter, pie, route}, MANAGER: the
// text of html/manager.js}. The manager makes one function of the source texts and this text; it must define RUNS, an object of
// functions, each run on the real code, each returning JSON-able results that the Python suite judges.
function element(){
  return {classList: {contains: function(){ return false; }, toggle: function(){}, add: function(){}, remove: function(){}}, dataset: {},
          style: {setProperty: function(){}}, appendChild: function(){}, querySelector: function(){ return null; },
          querySelectorAll: function(){ return []; }, innerHTML: '', className: ''};
}
function Socket(){}
Socket.prototype.send = function(){};

function runRoute(one){                 // the manager of manager.js, on a page of just these panes (a stand-in document)
  var log = [], tabs = [], ctxs = {}, blocks = {};
  var doc = {querySelector: function(){ return element(); }, querySelectorAll: function(){ return []; }, createElement: element,
             documentElement: element(), addEventListener: function(){}, title: ''};
  var win = {addEventListener: function(){}, setInterval: function(){}, setTimeout: function(){}, close: function(){},
             open: function(url){ tabs.push(url); return {closed: false, focus: function(){}, close: function(){}}; }};
  var page = {panes: one.panes, routed: ['commentline', 'commentselect', 'saved'], hash: 'h', config: {}, port: 1, address: '/x'};
  var make = new Function('PAGE', 'document', 'window', 'WebSocket', 'location', 'fetch', DATA.MANAGER + '\nreturn RS;');
  var RS = make(page, doc, win, Socket, {pathname: '/', search: ''}, function(){ return Promise.resolve({ok: true}); });
  one.panes.forEach(function(p){ blocks[p.block] = true; });
  Object.keys(blocks).forEach(function(block){
    RS.pane(block, function(ctx){
      var h = {};
      ctxs[ctx.loc] = ctx;
      (one.listens[ctx.loc] || []).forEach(function(name){
        h['on' + name.charAt(0).toUpperCase() + name.slice(1)] = function(data){ log.push([ctx.loc, name, JSON.parse(JSON.stringify(data))]); };
      });
      return h;
    });
  });
  RS.start();
  log.length = 0;                       // what start announces is not what is tested
  tabs.length = 0;
  one.steps.forEach(function(step){
    if (step.from) ctxs[step.from].emit(step.name, step.data || {});
    else RS.emit(step.name, step.data || {});
  });
  return {log: log, tabs: tabs};
}

var RUNS = {
  filter: function(){                   // the filter language of table.js: true, false, or "error: message"
    return DATA.CASES.filter.map(function(c){
      try { var test = parseFilter(c[0], c[1]); return test ? !!test(c[2]) : true; } catch (e) { return 'error: ' + e.message; }
    });
  },
  pie: function(){                      // pie() of pane_methods.js: the svg of each case
    return DATA.CASES.pie.map(function(c){ return pie(c[0], c[1]); });
  },
  route: function(){ return DATA.CASES.route.map(runRoute); }
};
