// pane_serverstatus.js -- the server's state (see pane_serverstatus.py for its signals).
RS.pane('serverstatus', function(ctx){
  var box = ctx.el.querySelector('.srv'), msg = box.querySelector('.srvmsg');
  function cell(k){ return box.querySelector('td[data-k="' + k + '"]'); }
  function clock(s){ s = Math.floor(s); var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60); return h + 'h ' + m + 'm ' + (s % 60) + 's'; }
  function buttons(on){ Array.prototype.forEach.call(box.querySelectorAll('.srvbtn button'), function(b){ b.disabled = !on; }); }
  if (!ctx.page.admin) box.querySelector('.srvbtn').style.display = 'none';
  box.querySelector('.stop').onclick = function(){ if (confirm('Stop the report server?')) ctx.verb('stop', {}); };
  box.querySelector('.restart').onclick = function(){ ctx.verb('restart', {}); };
  return {
    onStatus: function(st){
      if (st.stopped){
        msg.className = 'srvmsg bad';
        msg.innerHTML = 'Server stopped - you can close this page.<br>To open it again, double-click reportserver.bat or a .result file.';
        buttons(false); return;
      }
      if (st.lost){ msg.className = 'srvmsg bad'; msg.textContent = st.restarting ? 'Restarting...' : 'Connection lost - trying again...'; buttons(false); return; }
      msg.className = 'srvmsg'; msg.textContent = 'running'; buttons(true);
      cell('port').textContent = st.port; cell('pid').textContent = st.pid; cell('boot').textContent = st.boot;
      cell('started by').textContent = st.by || ''; cell('up for').textContent = clock(st.uptime);
      cell('pages open').textContent = st.pages; cell('connections').textContent = st.connections;
      cell('pages known').textContent = st.known; cell('version').textContent = st.version;
      cell('time').textContent = new Date().toLocaleTimeString();
    }
  };
});
