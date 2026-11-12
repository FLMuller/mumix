// page.js  tabs, size sliders and sortable tables of a fitting report; no server needed.
// Written inside the subset of the report server's script guard (rs3jsguard: no this, no .parentNode, no .closest, no arrow functions),
// so the report server can show the page in its own layout (with the status bar) and not only as a page of its own.
// Each handler is attached to its element when the page is ready; nothing looks upward in the tree.

// A click on a tab button (class btab, data-go) shows that panel of the group "run" and hides the others (the convention of runbench).
function showPanel(go) {
  var buttons = document.querySelectorAll('.btab'), panels = document.querySelectorAll('.bpanel');
  for (var i = 0; i < buttons.length; i++) {
    if (buttons[i].getAttribute('data-go')) {
      if (buttons[i].getAttribute('data-go') === go) buttons[i].classList.add('on'); else buttons[i].classList.remove('on');
    }
  }
  for (var j = 0; j < panels.length; j++) {
    if (panels[j].getAttribute('data-group') === 'run') panels[j].hidden = panels[j].id !== go;
  }
}

function addTabs() {
  var items = document.querySelectorAll('[data-go]');
  for (var i = 0; i < items.length; i++) {
    (function (item) {
      item.addEventListener('click', function () { showPanel(item.getAttribute('data-go')); });
    })(items[i]);
  }
}

// Every figure gets a size slider (50-400 % of the width of the figure's frame); the figure scrolls sideways when wider.
function addZoomSliders() {
  var figs = document.querySelectorAll('figure');
  for (var i = 0; i < figs.length; i++) {
    (function (fig) {
      var svg = fig.querySelector('svg');
      if (!svg) return;
      var base = 0;
      fig.classList.add('zoomable');
      var bar = document.createElement('div'), label = document.createElement('span');
      var slider = document.createElement('input');
      bar.className = 'zoombar'; slider.type = 'range'; slider.min = 50; slider.max = 400; slider.step = 10; slider.value = 100;
      label.textContent = 'size 100 %';
      bar.appendChild(label); bar.appendChild(slider);
      fig.insertBefore(bar, fig.firstChild);
      slider.addEventListener('input', function () {
        if (!base) base = fig.clientWidth || 800;      // the width at the first move: the frame at 100 %
        svg.style.width = (base * slider.value / 100) + 'px';
        svg.style.height = 'auto';
        label.textContent = 'size ' + slider.value + ' %';
      });
    })(figs[i]);
  }
}

// A click on a column header of a table.grid sorts the table by that column (numbers as numbers).
function addSorts() {
  var tables = document.querySelectorAll('table.grid');
  for (var t = 0; t < tables.length; t++) {
    (function (table) {
      if (!table.tHead || !table.tBodies.length) return;
      var heads = table.tHead.rows[0].cells;
      for (var c = 0; c < heads.length; c++) {
        (function (index) {
          heads[index].addEventListener('click', function () {
            var body = table.tBodies[0], rows = Array.prototype.slice.call(body.rows);
            var up = heads[index].getAttribute('data-sort') !== 'up';
            rows.sort(function (a, b) {
              var x = a.cells[index].textContent.trim(), y = b.cells[index].textContent.trim();
              var fx = parseFloat(x.replace(/[^0-9eE+\-.]/g, '')), fy = parseFloat(y.replace(/[^0-9eE+\-.]/g, ''));
              var r = (!isNaN(fx) && !isNaN(fy)) ? fx - fy : x.localeCompare(y);
              return up ? r : -r;
            });
            for (var k = 0; k < heads.length; k++) heads[k].removeAttribute('data-sort');
            heads[index].setAttribute('data-sort', up ? 'up' : 'down');
            for (var m = 0; m < rows.length; m++) body.appendChild(rows[m]);
          });
        })(c);
      }
    })(tables[t]);
  }
}

function startPage() { addTabs(); addZoomSliders(); addSorts(); }
// run now only if the page is already complete (a script loaded late); else when the page (or the server's box) says it is ready
if (document.readyState === 'complete') startPage(); else document.addEventListener('DOMContentLoaded', startPage);
