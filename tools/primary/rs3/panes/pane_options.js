// pane_options.js -- the option box (see pane_options.py for its signals).
RS.pane('options', function(ctx){
  var lines = ctx.el.querySelector('.olines'), wrap = ctx.el.querySelector('.owrap'), cfg = ctx.config || {};
  RS.doors(ctx.el.querySelector('.doors'));
  lines.checked = cfg.linenos !== false;
  wrap.checked = !!cfg.wrap;
  function keep(change){ ctx.verb('config', {change: change}).catch(function(){}); }
  lines.onchange = function(){ ctx.emit('withlineno', {on: lines.checked}); keep({linenos: lines.checked}); };
  wrap.onchange = function(){ ctx.emit('withwrap', {on: wrap.checked}); keep({wrap: wrap.checked}); };
  if (!lines.checked) ctx.emit('withlineno', {on: false});
  if (!wrap.checked) ctx.emit('withwrap', {on: false});
  return {};
});
