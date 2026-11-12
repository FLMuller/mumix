// pane_editbox.js -- the comment box (see pane_editbox.py for its signals).
RS.pane('editbox', function(ctx){
  var box = ctx.el.querySelector('.editbox'), target = box.querySelector('.etarget'), text = box.querySelector('.etext'),
      user = box.querySelector('.euser'), state = box.querySelector('.estate'), save = box.querySelector('.esave'),
      remove = box.querySelector('.eremove'), job = null, timer = null, flying = false, dirty = false;
  var AFTER = 600;                      // ms of no typing before the comment is saved
  function initials(){ return (ctx.config && ctx.config.initials) || 'user'; }       // the settings menu's
  function shown(){ user.textContent = job ? job.tag : initials(); }
  shown();
  function idle(){ job = null; box.classList.remove('active'); save.disabled = remove.disabled = true; text.disabled = true; shown(); }
  function say(t, bad){
    state.textContent = t || ''; state.style.color = bad ? '#c0392b' : '';
    ctx.emit('notice', {text: t || '', bad: !!bad});        // the status bar shows it too
  }
  function label(j){ if (j.mode === 'note') return 'note on line ' + j.line + ' of ' + j.file;
                     return j.mode === 'update' ? 'comment on lines ' + j.first + '-' + j.last + ' of ' + j.path
                                                : 'new comment above line ' + j.line + ' of ' + j.path; }
  function flush(){ if (timer){ clearTimeout(timer); timer = null; send(false); } }     // typed, not yet saved: save it first
  function begin(next, body, who){
    flush();
    next.tag = who || initials(); next.own = !who;              // a comment of another keeps its tag; a new one follows the settings
    job = next; box.classList.add('active'); text.disabled = false; save.disabled = false; remove.disabled = !(next.mode === 'update' || (next.mode === 'note' && next.code));
    target.textContent = label(next); text.value = body || ''; shown(); say('');
    text.focus();
  }
  function send(empty){
    var mine = job;
    if (!mine) return;
    if (flying){ dirty = true; return; }                                  // typed on while it saves: again afterwards
    if (!empty && mine.mode === 'insert' && !text.value.trim()) return;   // nothing written yet: no comment
    if (mine.mode === 'note'){ sendnote(mine, empty); return; }           // a note of a page (rs3microDB), not a comment of a file
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
      say(r.removed ? 'removed' : (r.note || 'saved'));
      ctx.emit('saved', {path: mine.path});
      if (dirty && job === mine){ dirty = false; send(false); } else dirty = false;
    }).catch(function(e){ flying = false; dirty = false; say(e.message, true); });
  }
  function sendnote(mine, empty){           // the notes of a page: a record appended to its .notes file; the code names the comment from the first save on
    if (!empty && !mine.code && !text.value.trim()) return;
    var f = {file: mine.file, line: mine.line, text: empty ? '' : text.value, who: mine.tag};
    if (mine.source) f.source = mine.source;
    if (mine.code) f.code = mine.code;
    flying = true; say('saving...');
    ctx.verb('note_add', f).then(function(r){
      flying = false;
      if (!r.ok){ dirty = false; say(r.error || 'the server refused it', true); return; }
      mine.code = r.code;
      if (job === mine && empty){ idle(); target.textContent = 'removed'; text.value = ''; }
      else if (job === mine){ remove.disabled = false; }
      say(empty ? 'removed' : 'saved');
      ctx.emit('notesaved', {file: mine.file, line: mine.line, code: r.code});
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
    onNoteline: function(d){ begin({mode: 'note', file: d.file, line: d.line, source: d.source || '', code: null}, '', ''); },        // a line of a page was clicked: a new note
    onNoteselect: function(d){ begin({mode: 'note', file: d.file, line: d.line, source: d.source || '', code: d.code}, d.text, d.who || ''); },   // a note was clicked: change it
    onWithconfig: function(){ if (job && job.own) job.tag = initials(); shown(); },      // the user id was changed in the menu
    onShowcode: function(d){
      if (!d.on && job && job.path === d.path){ flush(); idle(); target.textContent = 'no comment selected'; text.value = ''; }
    }
  };
});
