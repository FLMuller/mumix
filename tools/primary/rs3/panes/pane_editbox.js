// pane_editbox.js -- the comment box (see pane_editbox.py for its signals).
RS.pane('editbox', function(ctx){
  var box = ctx.el.querySelector('.editbox'), target = box.querySelector('.etarget'), text = box.querySelector('.etext'),
      user = box.querySelector('.euser'), state = box.querySelector('.estate'), save = box.querySelector('.esave'),
      remove = box.querySelector('.eremove'), job = null, timer = null, flying = false, dirty = false;
  var AFTER = 600;                      // ms of no typing before the comment is saved
  function initials(){ return (ctx.config && ctx.config.initials) || 'user'; }       // the settings menu's
  function shown(){ user.textContent = job ? job.tag : initials(); }
  shown();
  function idle(){ job = null; save.disabled = remove.disabled = true; text.disabled = true; shown(); }
  function say(t, bad){
    state.textContent = t || ''; state.style.color = bad ? '#c0392b' : '';
    ctx.emit('notice', {text: t || '', bad: !!bad});        // the status bar shows it too
  }
  function label(j){ return j.mode === 'update' ? 'comment on lines ' + j.first + '-' + j.last + ' of ' + j.path
                                                : 'new comment above line ' + j.line + ' of ' + j.path; }
  function flush(){ if (timer){ clearTimeout(timer); timer = null; send(false); } }     // typed, not yet saved: save it first
  function begin(next, body, who){
    flush();
    next.tag = who || initials(); next.own = !who;              // a comment of another keeps its tag; a new one follows the settings
    job = next; text.disabled = false; save.disabled = false; remove.disabled = next.mode !== 'update';
    target.textContent = label(next); text.value = body || ''; shown(); say('');
    text.focus();
  }
  function send(empty){
    var mine = job;
    if (!mine) return;
    if (flying){ dirty = true; return; }                                  // typed on while it saves: again afterwards
    if (!empty && mine.mode === 'insert' && !text.value.trim()) return;   // nothing written yet: no comment
    var f = {filename: mine.path, base: mine.base, tag: mine.tag, text: empty ? '' : text.value};
    if (mine.mode === 'update'){ f.first = mine.first; f.last = mine.last; } else f.line = mine.line;
    flying = true; say('saving...');
    ctx.verb(mine.mode, f).then(function(r){
      flying = false;
      if (!r.ok){ dirty = false; say(r.error || 'the server refused it', true); return; }
      if (job === mine){
        if (r.removed){ idle(); target.textContent = 'removed'; text.value = ''; }
        else {                                                            // from now on its lines are known: the next save changes them
          mine.mode = 'update'; mine.first = r.first; mine.last = r.last; mine.base = r.base;
          remove.disabled = false; target.textContent = label(mine);
        }
      }
      say(r.removed ? 'removed' : 'saved');
      ctx.emit('saved', {path: mine.path});
      if (dirty && job === mine){ dirty = false; send(false); } else dirty = false;
    }).catch(function(e){ flying = false; dirty = false; say(e.message, true); });
  }
  save.onclick = function(){ if (timer){ clearTimeout(timer); timer = null; } send(false); };
  remove.onclick = function(){ if (timer){ clearTimeout(timer); timer = null; } send(true); };
  text.addEventListener('input', function(){          // the comment saves itself when typing stops
    if (!job) return;
    clearTimeout(timer);
    timer = setTimeout(function(){ timer = null; send(false); }, AFTER);
  });
  text.addEventListener('keydown', function(e){ if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) save.onclick(); });
  idle();
  return {
    onCommentline: function(d){ begin({mode: 'insert', path: d.path, base: d.base, line: d.line}, '', ''); },
    onCommentselect: function(d){ begin({mode: 'update', path: d.path, base: d.base, first: d.first, last: d.last}, d.text, d.tag); },
    onWithconfig: function(){ if (job && job.own) job.tag = initials(); shown(); },      // the user id was changed in the menu
    onShowcode: function(d){
      if (!d.on && job && job.path === d.path){ flush(); idle(); target.textContent = 'no comment selected'; text.value = ''; }
    }
  };
});
