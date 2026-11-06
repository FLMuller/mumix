// pane_search.js -- the search box (see pane_search.py for its signals).
RS.pane('search', function(ctx){
  var mode = ctx.el.querySelector('.smode'), box = ctx.el.querySelector('.sbox'), count = ctx.el.querySelector('.scount'), last = mode.value;
  function fire(m, text){ ctx.emit('searchtext', {text: text, mode: m}); }
  box.addEventListener('input', function(){ count.textContent = ''; fire(mode.value, box.value); });
  box.addEventListener('keydown', function(e){
    if (e.key === 'Enter') ctx.emit(e.shiftKey ? 'searchprev' : 'searchnext', {mode: mode.value});
  });
  mode.addEventListener('change', function(){
    fire(last, '');                       // the mode we leave is cleared
    last = mode.value; count.textContent = '';
    if (box.value) fire(mode.value, box.value);
  });
  ctx.el.querySelector('.snext').onclick = function(){ ctx.emit('searchnext', {mode: mode.value}); };
  ctx.el.querySelector('.sprev').onclick = function(){ ctx.emit('searchprev', {mode: mode.value}); };
  return {
    onSearchcount: function(d){ count.textContent = d.total ? d.index + ' / ' + d.total : 'none'; }
  };
});
