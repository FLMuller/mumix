// rs3route.js -- the harness of tests/b_rs3.py for the routing of html/manager.js: node rs3route.js manager.js cases.json
// Each case is {panes: [{loc, block, at, to, takes, holds, hosted}], listens: {loc: [signal, ...]}, steps: [{from, name, data}]}.
// The manager is run with a page of just those panes, each pane a block that listens to the signals named for it and
// writes every signal it gets to the log as [loc, name, data]. A step is a signal sent by the pane `from`.
// The answer is [{log: [...], tabs: [path, ...]}] for each case: tabs are the browser tabs the manager opened.
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync(process.argv[2], 'utf8');
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

function element() {
  return {classList: {contains() { return false; }, toggle() {}, add() {}, remove() {}}, dataset: {}, style: {setProperty() {}},
          appendChild() {}, querySelector() { return null; }, querySelectorAll() { return []; }, innerHTML: '', className: ''};
}

function run(one) {
  const log = [], tabs = [], ctxs = {};
  const document = {querySelector() { return element(); }, querySelectorAll() { return []; }, createElement: element,
                    documentElement: element(), addEventListener() {}, title: ''};
  class WebSocket { constructor() {} send() {} }
  const window = {addEventListener() {}, setInterval() {}, setTimeout() {}, close() {},
                  open(url) { tabs.push(url); return {closed: false, focus() {}, close() {}}; }};
  const PAGE = {panes: one.panes, routed: ['commentline', 'commentselect', 'saved'], hash: 'h', config: {}, port: 1, address: '/x'};
  const context = vm.createContext({document, window, WebSocket, PAGE, console, JSON, Promise, Object, Array, location: {pathname: '/', search: ''},
                                    setTimeout() {}, fetch() { return Promise.resolve({ok: true}); }});
  vm.runInContext(source + '\n;this.RS = RS;', context);
  const RS = context.RS;
  new Set(one.panes.map((p) => p.block)).forEach((block) => {
    RS.pane(block, (ctx) => {
      ctxs[ctx.loc] = ctx;
      const h = {};
      (one.listens[ctx.loc] || []).forEach((name) => {
        h['on' + name[0].toUpperCase() + name.slice(1)] = (data) => { log.push([ctx.loc, name, JSON.parse(JSON.stringify(data))]); };
      });
      return h;
    });
  });
  RS.start();
  log.length = 0;                       // what start announces is not what is tested
  tabs.length = 0;
  one.steps.forEach((step) => {
    if (step.from) ctxs[step.from].emit(step.name, step.data || {});
    else RS.emit(step.name, step.data || {});
  });
  return {log, tabs};
}

process.stdout.write(JSON.stringify(cases.map(run)));
