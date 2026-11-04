// pane_editbox.js -- the comment box (see pane_editbox.py for its signals).
RS.pane('editbox', function(ctx){
  var box = ctx.el.querySelector('.editbox'), target = box.querySelector('.etarget'), text = box.querySelector('.etext'),
      tag = box.querySelector('.etag'), state = box.querySelector('.estate'), save = box.querySelector('.esave'),
      remove = box.querySelector('.eremove'), job = null;
  tag.value = (ctx.config && ctx.config.initials) || 'user';
  function idle(){ job = null; save.disabled = remove.disabled = true; text.disabled = true; }
  function say(t, bad){ state.textContent = t || ''; state.style.color = bad ? '#c0392b' : ''; }
  function begin(next, label, body, who){
    job = next; text.disabled = false; save.disabled = false; remove.disabled = next.mode !== 'update';
    target.textContent = label; text.value = body || ''; if (who) tag.value = who; say('');
    text.focus();
  }
  function send(empty){
    if (!job) return;
    var f = {filename: job.path, base: job.base, tag: tag.value.trim(), text: empty ? '' : text.value};
    if (job.mode === 'update'){ f.first = job.first; f.last = job.last; } else f.line = job.line;
    say('saving...');
    ctx.verb(job.mode, f).then(function(r){
      if (!r.ok){ say(r.error || 'the server refused it', true); return; }
      var path = job.path;
      say('saved');
      idle(); target.textContent = 'saved';
      ctx.emit('saved', {path: path, where: ctx.where});
    }).catch(function(e){ say(e.message, true); });
  }
  save.onclick = function(){ send(false); };
  remove.onclick = function(){ send(true); };
  text.addEventListener('keydown', function(e){ if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) send(false); });
  idle();
  return {
    onCommentline: function(d){ begin({mode: 'insert', path: d.path, base: d.base, line: d.line}, 'new comment above line ' + d.line + ' of ' + d.path, '', ''); },
    onCommentselect: function(d){
      begin({mode: 'update', path: d.path, base: d.base, first: d.first, last: d.last},
            'comment on lines ' + d.first + '-' + d.last + ' of ' + d.path, d.text, d.tag);
    },
    onClosefile: function(d){ if (job && job.path === d.path){ idle(); target.textContent = 'no comment selected'; text.value = ''; } }
  };
});
