/* Page behaviour: charts, the four interactive panels, the clip grid, section rail and hero drawing.
   Plain JavaScript, no libraries. All numbers come from data.js. */
(function () {
  'use strict';
  var D = window.EMG;
  var NS = 'http://www.w3.org/2000/svg';
  var C = { blue: '#3987e5', orange: '#d95926', aqua: '#199e70', quiet: '#5a7ba3', glow: '#86d0ff', ink: '#e9f1fb', ink2: '#a8bcd6', ink3: '#7990ae', surface: '#0b1d33', line: '#1f3d61', soft: '#16304f' };
  var REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function $(s, r) { return (r || document).querySelector(s); }
  function $all(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }

  /* ---------- small helpers ---------- */
  function svgEl(tag, attrs, parent, text) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    if (text !== undefined) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function newSvg(host, w, h, label) {
    host.innerHTML = '';
    var s = svgEl('svg', { viewBox: '0 0 ' + w + ' ' + h, width: w, height: h, role: 'img', 'aria-label': label || '' }, host);
    return s;
  }
  function mulberry(seed) {
    var a = seed >>> 0;
    return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  function gauss(r) { var u = 0, v = 0; while (u === 0) u = r(); v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
  function median(a) { var s = a.slice().sort(function (x, y) { return x - y; }); var n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : NaN; }
  function quantile(a, q) { var s = a.slice().sort(function (x, y) { return x - y; }); var p = (s.length - 1) * q, b = Math.floor(p), r = p - b; return s[b + 1] !== undefined ? s[b] + r * (s[b + 1] - s[b]) : s[b]; }
  function fmt(v, d) { return v.toFixed(d === undefined ? 2 : d); }
  function sign(v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v); }
  /* bar with a rounded data end and a square baseline */
  function barPath(x, y, w, h, r) {
    w = Math.max(w, 1); r = Math.min(r, w, h / 2);
    return 'M' + x + ' ' + y + 'h' + (w - r) + 'a' + r + ' ' + r + ' 0 0 1 ' + r + ' ' + r + 'v' + (h - 2 * r) + 'a' + r + ' ' + r + ' 0 0 1 ' + (-r) + ' ' + r + 'h' + (-(w - r)) + 'z';
  }

  /* ---------- tooltip ---------- */
  var tip = $('#tip');
  function tipShow(html, ev) {
    tip.innerHTML = html; tip.classList.add('show');
    var x = ev.clientX + 14, y = ev.clientY + 14, r = tip.getBoundingClientRect();
    if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - 14;
    if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - 14;
    tip.style.left = Math.max(8, x) + 'px'; tip.style.top = Math.max(8, y) + 'px';
  }
  function tipHide() { tip.classList.remove('show'); }
  function hover(node, html) {
    node.addEventListener('pointermove', function (ev) { tipShow(typeof html === 'function' ? html() : html, ev); });
    node.addEventListener('pointerleave', tipHide);
  }

  /* ---------- responsive chart registry ---------- */
  var charts = [];
  function chart(id, draw) {
    var host = document.getElementById(id); if (!host) return { redraw: function () {} };
    var c = { host: host, w: 0, redraw: function () { c.w = Math.max(260, Math.floor(host.clientWidth)); draw(host, c.w); } };
    charts.push(c); c.redraw(); return c;
  }
  var rT;
  window.addEventListener('resize', function () {
    clearTimeout(rT); rT = setTimeout(function () { charts.forEach(function (c) { if (Math.floor(c.host.clientWidth) !== c.w && c.host.clientWidth > 0) c.redraw(); }); }, 120);
  });

  /* ---------- horizontal bars ---------- */
  function hbars(host, w, rows, o) {
    o = o || {};
    var stacked = w < 470;
    var labelW = stacked ? 0 : Math.min(o.labelW || 250, w * 0.46);
    var rowH = stacked ? 54 : (o.rowH || 40), top = 6, valW = 62;
    var h = top + rows.length * rowH + (o.axis ? 24 : 4);
    var s = newSvg(host, w, h, o.label);
    var x0 = labelW, x1 = w - valW, max = o.max || Math.max.apply(null, rows.map(function (r) { return r.v; })) * 1.05;
    function X(v) { return x0 + (x1 - x0) * v / max; }
    if (o.ticks) o.ticks.forEach(function (t) {
      svgEl('line', { x1: X(t), x2: X(t), y1: top, y2: h - 22, class: 'grid' }, s);
      svgEl('text', { x: X(t), y: h - 6, 'text-anchor': 'middle', class: 'muted' }, s, o.tickFmt ? o.tickFmt(t) : t);
    });
    svgEl('line', { x1: x0, x2: x0, y1: top, y2: top + rows.length * rowH, class: 'axis' }, s);
    rows.forEach(function (r, i) {
      var y = top + i * rowH, by = stacked ? y + 34 : y + rowH / 2 - 6;
      if (stacked) {
        svgEl('text', { x: 0, y: y + 14, class: r.hi ? 'val' : '' }, s, r.name);
        if (r.who) svgEl('text', { x: 0, y: y + 28, class: 'muted' }, s, r.who);
      } else {
        svgEl('text', { x: labelW - 12, y: y + rowH / 2 + (r.who ? -3 : 4), 'text-anchor': 'end', class: r.hi ? 'val' : '' }, s, r.name);
        if (r.who) svgEl('text', { x: labelW - 12, y: y + rowH / 2 + 12, 'text-anchor': 'end', class: 'muted' }, s, r.who);
      }
      var p = svgEl('path', { d: barPath(x0, by, X(r.v) - x0, 12, 4), fill: r.color || C.quiet, opacity: r.opacity || 1, class: 'mk' }, s);
      svgEl('text', { x: X(r.v) + 8, y: by + 10.5, class: 'val' }, s, o.fmt ? o.fmt(r.v) : r.v);
      var hit = svgEl('rect', { x: 0, y: y, width: w, height: rowH, class: 'hit' }, s);
      hover(hit, '<b>' + r.name + '</b>' + (r.who ? '<br>' + r.who : '') + '<br>' + (o.fmt ? o.fmt(r.v) : r.v) + (r.tip ? '<br>' + r.tip : ''));
      hit.addEventListener('pointerenter', function () { p.classList.add('on'); }); hit.addEventListener('pointerleave', function () { p.classList.remove('on'); });
    });
  }

  /* ---------- line chart ---------- */
  function lines(host, w, o) {
    var h = o.h || 230, m = { l: 44, r: 18, t: 14, b: 40 };
    var s = newSvg(host, w, h, o.label);
    var n = o.x.length, xs = function (i) { return m.l + (w - m.l - m.r) * (n === 1 ? 0.5 : i / (n - 1)); };
    var ys = function (v) { return m.t + (h - m.t - m.b) * (1 - (v - o.yMin) / (o.yMax - o.yMin)); };
    o.yTicks.forEach(function (t) {
      svgEl('line', { x1: m.l, x2: w - m.r, y1: ys(t), y2: ys(t), class: 'grid' }, s);
      svgEl('text', { x: m.l - 8, y: ys(t) + 4, 'text-anchor': 'end', class: 'muted' }, s, (o.tickFmt || o.yFmt)(t));
    });
    o.x.forEach(function (lab, i) { svgEl('text', { x: xs(i), y: h - 20, 'text-anchor': i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle', class: 'muted' }, s, lab); });
    if (o.xTitle) svgEl('text', { x: (m.l + w - m.r) / 2, y: h - 3, 'text-anchor': 'middle', class: 'muted' }, s, o.xTitle);
    var cross = svgEl('line', { y1: m.t, y2: h - m.b, stroke: C.line, 'stroke-width': 1, visibility: 'hidden' }, s);
    if (o.sel !== undefined && o.sel !== null) svgEl('line', { x1: xs(o.sel), x2: xs(o.sel), y1: m.t, y2: h - m.b, stroke: C.glow, 'stroke-width': 1, opacity: .5 }, s);
    o.series.forEach(function (se) {
      var d = se.y.map(function (v, i) { return (i ? 'L' : 'M') + xs(i + (se.offset || 0)) + ' ' + ys(v); }).join('');
      svgEl('path', { d: d, fill: 'none', stroke: se.color, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, s);
      se.y.forEach(function (v, i) {
        var xi = i + (se.offset || 0), on = o.sel === xi;
        svgEl('circle', { cx: xs(xi), cy: ys(v), r: on ? 6 : 4, fill: se.color, stroke: C.surface, 'stroke-width': 2 }, s);
        if (on || o.labelAll) svgEl('text', { x: xs(xi) + (xi === n - 1 ? -9 : 9), y: ys(v) + (se.labelDy || -9), 'text-anchor': xi === n - 1 ? 'end' : 'start', class: 'val' }, s, o.yFmt(v));
      });
    });
    var hit = svgEl('rect', { x: m.l - 10, y: m.t, width: w - m.l - m.r + 20, height: h - m.t - m.b, class: 'hit' }, s);
    hit.addEventListener('pointermove', function (ev) {
      var r = s.getBoundingClientRect(), px = (ev.clientX - r.left) * w / r.width, best = 0, bd = 1e9;
      for (var i = 0; i < n; i++) { var dd = Math.abs(xs(i) - px); if (dd < bd) { bd = dd; best = i; } }
      cross.setAttribute('x1', xs(best)); cross.setAttribute('x2', xs(best)); cross.setAttribute('visibility', 'visible');
      var html = '<b>' + (o.tipX ? o.tipX(best) : o.x[best]) + '</b>';
      o.series.forEach(function (se) { var v = se.y[best - (se.offset || 0)]; if (v !== undefined) html += '<br><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:' + se.color + ';margin-right:6px"></span>' + se.name + ': ' + o.yFmt(v); });
      tipShow(html, ev);
    });
    hit.addEventListener('pointerleave', function () { cross.setAttribute('visibility', 'hidden'); tipHide(); });
  }

  /* ---------- segmented buttons ---------- */
  function seg(id, onPick) {
    var box = document.getElementById(id); if (!box) return;
    box.addEventListener('click', function (ev) {
      var b = ev.target.closest('button'); if (!b) return;
      $all('button', box).forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      onPick(b.getAttribute('data-v'));
    });
  }

  /* =====================================================================
     1. Onset leads explorer (real data)
     ===================================================================== */
  (function () {
    var subj = 9, sess = 'all', box = $('#leadSubj'); if (!box) return;
    for (var i = 1; i <= 12; i++) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = i; b.setAttribute('data-v', i);
      b.setAttribute('aria-pressed', i === subj ? 'true' : 'false'); b.setAttribute('aria-label', 'Person ' + i + (i > 10 ? ', amputee' : ''));
      box.appendChild(b);
    }
    function rowsFor(s) { return D.leads[s].filter(function (r) { return sess === 'all' || r[0] < 3; }); }
    var LIM = 1000;
    var main = chart('leadChart', function (host, w) {
      var rows = rowsFor(subj), top = 26, rowH = 30, mL = w < 520 ? 26 : 150, mR = 14, h = top + 9 * rowH + 26;
      var s = newSvg(host, w, h, 'Onset lead of every repetition for person ' + subj + ', by movement');
      var X = function (v) { return mL + (w - mL - mR) * (Math.max(-LIM, Math.min(LIM, v)) + LIM) / (2 * LIM); };
      [-1000, -500, 0, 500, 1000].forEach(function (t) {
        svgEl('line', { x1: X(t), x2: X(t), y1: top - 4, y2: top + 9 * rowH, class: t === 0 ? 'axis' : 'grid', stroke: t === 0 ? C.ink3 : undefined }, s);
        if (w < 520 && Math.abs(t) === 500) return;
        svgEl('text', { x: X(t), y: top + 9 * rowH + 16, 'text-anchor': t === -1000 ? 'start' : t === 1000 ? 'end' : 'middle', class: 'muted' }, s, (t > 0 ? '+' : '') + t + ' ms');
      });
      svgEl('text', { x: X(-500), y: 12, 'text-anchor': 'middle', class: 'muted' }, s, w < 520 ? '← glove first' : '← glove hand moved first');
      svgEl('text', { x: X(500), y: 12, 'text-anchor': 'middle', class: 'muted' }, s, w < 520 ? 'EMG first →' : 'EMG arm fired first →');
      var rnd = mulberry(subj * 77 + 5);
      for (var m = 1; m <= 9; m++) {
        var y = top + (m - 1) * rowH + rowH / 2;
        svgEl('text', { x: w < 520 ? 0 : mL - 12, y: y + 4, 'text-anchor': w < 520 ? 'start' : 'end' }, s, w < 520 ? m : D.movements[m - 1]);
        var vals = rows.filter(function (r) { return r[1] === m; });
        vals.forEach(function (r) {
          var c = svgEl('circle', { cx: X(r[2]), cy: y + (rnd() - 0.5) * 16, r: 3.6, fill: r[0] === 3 ? C.orange : C.blue, 'fill-opacity': .78, stroke: C.surface, 'stroke-width': 1 }, s);
          hover(c, '<b>' + D.movements[m - 1] + '</b><br>session ' + r[0] + '<br>' + (r[2] >= 0 ? 'EMG first by ' + r[2] : 'glove first by ' + (-r[2])) + ' ms');
        });
        if (vals.length) { var md = median(vals.map(function (r) { return r[2]; })); svgEl('line', { x1: X(md), x2: X(md), y1: y - 11, y2: y + 11, stroke: '#fff', 'stroke-width': 2, 'stroke-linecap': 'round' }, s); }
      }
      host.insertAdjacentHTML('beforeend', '<ul class="legend" style="margin:2px 0 0"><li><i style="background:' + C.blue + ';border-radius:50%"></i>sessions 1 and 2</li>' + (sess === 'all' ? '<li><i style="background:' + C.orange + ';border-radius:50%"></i>session 3</li>' : '') + '<li><i style="background:#fff;width:3px;height:14px;border-radius:2px;vertical-align:-3px"></i>median for that movement</li></ul>');
      if (w < 520) host.insertAdjacentHTML('beforeend', '<p class="note" style="margin-top:6px">Rows 1 to 9: ' + D.movements.join(', ') + '.</p>');
    });
    var over = chart('leadOverview', function (host, w) {
      var top = 24, rowH = 19, mL = w < 520 ? 26 : 150, mR = 14, h = top + 12 * rowH + 22;
      var s = newSvg(host, w, h, 'Median and middle half of onset leads for all 12 people');
      var X = function (v) { return mL + (w - mL - mR) * (Math.max(-LIM, Math.min(LIM, v)) + LIM) / (2 * LIM); };
      svgEl('text', { x: 0, y: 12, class: 'val' }, s, 'All 12 people: median and middle half. Select a row.');
      svgEl('line', { x1: X(0), x2: X(0), y1: top, y2: top + 12 * rowH, stroke: C.ink3, 'stroke-width': 1 }, s);
      for (var p = 1; p <= 12; p++) (function (p) {
        var v = rowsFor(p).map(function (r) { return r[2]; }), y = top + (p - 1) * rowH + rowH / 2, on = p === subj;
        svgEl('text', { x: w < 520 ? 0 : mL - 12, y: y + 4, 'text-anchor': w < 520 ? 'start' : 'end', class: on ? 'val' : '' }, s, w < 520 ? p : 'Person ' + p + (p > 10 ? ' (amputee)' : ''));
        svgEl('line', { x1: X(quantile(v, .25)), x2: X(quantile(v, .75)), y1: y, y2: y, stroke: on ? C.glow : C.quiet, 'stroke-width': 6, 'stroke-linecap': 'round', opacity: on ? .55 : .7 }, s);
        svgEl('circle', { cx: X(median(v)), cy: y, r: 5, fill: on ? '#fff' : C.ink2, stroke: C.surface, 'stroke-width': 2 }, s);
        var hit = svgEl('rect', { x: 0, y: y - rowH / 2, width: w, height: rowH, class: 'hit', style: 'cursor:pointer' }, s);
        hover(hit, '<b>Person ' + p + '</b><br>median ' + sign(Math.round(median(v))) + ' ms<br>middle half ' + sign(Math.round(quantile(v, .25))) + ' to ' + sign(Math.round(quantile(v, .75))) + ' ms');
        hit.addEventListener('click', function () { pick(p); });
      })(p);
    });
    function read() {
      var v = rowsFor(subj).map(function (r) { return r[2]; });
      var first = Math.round(100 * v.filter(function (x) { return x > 0; }).length / v.length);
      $('#leadRead').innerHTML = '<li><b>' + sign(Math.round(median(v))) + ' ms</b>median lead</li><li><b>' + sign(Math.round(quantile(v, .25))) + ' to ' + sign(Math.round(quantile(v, .75))) + ' ms</b>middle half of repetitions</li><li><b>' + first + '%</b>of repetitions with EMG first</li><li><b>' + v.length + '</b>repetitions detected</li>';
    }
    function pick(p) { subj = +p; $all('button', box).forEach(function (x) { x.setAttribute('aria-pressed', +x.getAttribute('data-v') === subj ? 'true' : 'false'); }); main.redraw(); over.redraw(); read(); }
    seg('leadSubj', pick);
    seg('leadSess', function (v) { sess = v; main.redraw(); over.redraw(); read(); });
    read();
  })();

  /* =====================================================================
     2. Envelope window demo (synthetic, computed in the browser)
     ===================================================================== */
  (function () {
    var slider = $('#envW'); if (!slider) return;
    var FS = 1000, N = 3200, ON = 1000, OFF = 2200, r = mulberry(20261116), x = new Float32Array(N), cs = new Float64Array(N + 1);
    var K = Math.sqrt(2 / Math.PI); /* mean |x| of unit noise */
    for (var i = 0; i < N; i++) { var a = (i >= ON && i < OFF) ? 1 : 0.07; x[i] = Math.abs(a * gauss(r)) / K; cs[i + 1] = cs[i] + x[i]; }
    function env(W) { var e = new Float32Array(N); for (var i = 0; i < N; i++) { var lo = Math.max(0, i + 1 - W); e[i] = (cs[i + 1] - cs[lo]) / W; } return e; }
    var c = chart('envChart', function (host, w) {
      var W = +slider.value, e = env(W), h = 250, m = { l: 8, r: 8, t: 10, b: 30 };
      var s = newSvg(host, w, h, 'Synthetic EMG, its moving-average envelope for a ' + W + ' millisecond window, and the true effort');
      var X = function (i) { return m.l + (w - m.l - m.r) * i / (N - 1); }, Y = function (v) { return m.t + (h - m.t - m.b) * (1 - Math.min(v, 2.6) / 2.6); };
      [0, 1, 2, 3].forEach(function (t) { svgEl('line', { x1: X(t * FS), x2: X(t * FS), y1: m.t, y2: h - m.b, class: 'grid' }, s); svgEl('text', { x: X(t * FS) + (t === 0 ? 0 : 0), y: h - 10, 'text-anchor': t === 0 ? 'start' : 'middle', class: 'muted' }, s, t + ' s'); });
      /* rectified EMG, one min/max column per pixel */
      var cols = Math.floor(w - m.l - m.r), d = '';
      for (var p = 0; p < cols; p++) { var a = Math.floor(p * N / cols), b = Math.floor((p + 1) * N / cols), mx = 0; for (var j = a; j < b; j++) if (x[j] > mx) mx = x[j]; d += 'M' + (m.l + p) + ' ' + Y(0) + 'V' + Y(mx); }
      svgEl('path', { d: d, stroke: C.quiet, 'stroke-width': 1, opacity: .55 }, s);
      svgEl('path', { d: 'M' + X(0) + ' ' + Y(0.07) + 'H' + X(ON) + 'V' + Y(1) + 'H' + X(OFF) + 'V' + Y(0.07) + 'H' + X(N - 1), fill: 'none', stroke: C.orange, 'stroke-width': 2, 'stroke-linejoin': 'round' }, s);
      var de = '', step = Math.max(1, Math.floor(N / (cols * 1.5)));
      for (var k = 0; k < N; k += step) de += (k ? 'L' : 'M') + X(k).toFixed(1) + ' ' + Y(e[k]).toFixed(1);
      svgEl('path', { d: de, fill: 'none', stroke: C.glow, 'stroke-width': 2, 'stroke-linejoin': 'round' }, s);
      /* half-rise marker */
      var half = ON; while (half < N && e[half] < 0.535) half++;
      svgEl('line', { x1: X(ON), x2: X(half), y1: Y(0.535), y2: Y(0.535), stroke: '#fff', 'stroke-width': 2 }, s);
      svgEl('circle', { cx: X(half), cy: Y(0.535), r: 4.5, fill: '#fff', stroke: C.surface, 'stroke-width': 2 }, s);
      svgEl('text', { x: X(half) + 10, y: Y(0.535) + 4, class: 'val' }, s, (half - ON) + ' ms late at half height');
      var mean = 0, sd = 0, n = 0; for (var q = ON + W; q < OFF; q++) { mean += e[q]; n++; } mean /= n; for (q = ON + W; q < OFF; q++) sd += (e[q] - mean) * (e[q] - mean); sd = Math.sqrt(sd / n);
      $('#envRead').innerHTML = '<li><b>' + W + ' ms</b>window</li><li><b>' + (half - ON) + ' ms</b>delay at half height (W/2 = ' + (W / 2) + ')</li><li><b>±' + (100 * sd / mean).toFixed(0) + '%</b>jitter while the effort is steady</li>';
    });
    slider.addEventListener('input', c.redraw);
  })();

  /* =====================================================================
     3. Model-section charts
     ===================================================================== */
  chart('bvChart', function (host, w) {
    var b = D.biasVar, rows = [{ n: 'No penalty', bias: b.bias2Tuned, v: b.varNoPenalty }, { n: 'Strongest penalty', bias: b.bias2Strong, v: b.varStrong }];
    var h = 132, s = newSvg(host, w, h, 'Bias squared and variance of the ridge model with no penalty and with the strongest penalty');
    var x0 = 0, x1 = w - 10, max = 400, X = function (v) { return x0 + (x1 - x0) * v / max; };
    rows.forEach(function (r, i) {
      var y = 10 + i * 50;
      svgEl('text', { x: 0, y: y + 10 }, s, r.n);
      svgEl('path', { d: barPath(x0, y + 18, X(r.bias) - 2, 12, 0), fill: C.blue }, s);
      svgEl('path', { d: barPath(X(r.bias) + 1, y + 18, Math.max(X(r.v), 2), 12, 4), fill: C.orange }, s);
      svgEl('text', { x: w - 4, y: y + 10, 'text-anchor': 'end', class: 'val' }, s, 'bias² ' + r.bias + ' + variance ' + r.v);
    });
    svgEl('rect', { x: 0, y: h - 14, width: 10, height: 10, rx: 3, fill: C.blue }, s); svgEl('text', { x: 16, y: h - 5, class: 'muted' }, s, 'bias² (deg²), includes label noise');
    svgEl('rect', { x: Math.min(250, w - 110), y: h - 14, width: 10, height: 10, rx: 3, fill: C.orange }, s); svgEl('text', { x: Math.min(266, w - 94), y: h - 5, class: 'muted' }, s, 'variance');
  });
  chart('corrChart', function (host, w) {
    hbars(host, w, D.corr.map(function (r, i) { return { name: r.label, v: r.v, color: i < 2 ? C.orange : C.blue, hi: i < 2, tip: i < 2 ? 'a copy created by our feature design' : 'between two different sensors' }; }),
      { max: 1.0, fmt: function (v) { return v.toFixed(2); }, labelW: 240, rowH: 30, label: 'Correlation between pairs of model inputs' });
    host.insertAdjacentHTML('beforeend', '<ul class="legend" style="margin-top:8px"><li><i style="background:' + C.orange + '"></i>copies our features created</li><li><i style="background:' + C.blue + '"></i>between different sensors</li></ul>');
  });
  chart('histChart', function (host, w) {
    lines(host, w, { h: 200, x: D.history.map(function (r) { return r.label; }), xTitle: 'how far back the model can see', yMin: 0.35, yMax: 0.6, yTicks: [0.4, 0.5, 0.6], yFmt: function (v) { return v.toFixed(2); },
      series: [{ name: 'R²', color: C.blue, y: D.history.map(function (r) { return r.r2; }) }], labelAll: true, label: 'R squared of the ridge model against history length' });
  });
  chart('leakChart', function (host, w) {
    var taus = [0.05, 0.15, 0.5, 1.5, 4], cols = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf'], T = 6, dt = 0.01, n = T / dt, h = 190, m = { l: 6, r: 6, t: 8, b: 26 };
    var s = newSvg(host, w, h, 'Response of five leaky integrators to a short burst of muscle activity');
    var X = function (t) { return m.l + (w - m.l - m.r) * t / T; }, Y = function (v) { return m.t + (h - m.t - m.b) * (1 - v); };
    svgEl('rect', { x: X(0.5), y: m.t, width: X(1.1) - X(0.5), height: h - m.t - m.b, fill: C.orange, opacity: .16 }, s);
    svgEl('text', { x: X(0.5), y: h - 8, class: 'muted' }, s, 'burst');
    [2, 4, 6].forEach(function (t) { svgEl('text', { x: X(t), y: h - 8, 'text-anchor': t === 6 ? 'end' : 'middle', class: 'muted' }, s, t + ' s'); });
    svgEl('line', { x1: m.l, x2: w - m.r, y1: Y(0), y2: Y(0), class: 'axis' }, s);
    taus.forEach(function (tau, k) {
      var y = 0, d = '', a = dt / tau;
      for (var i = 0; i <= n; i++) { var t = i * dt, u = (t >= 0.5 && t < 1.1) ? 1 : 0; y += Math.min(1, a) * (u - y); if (i % 2 === 0) d += (i ? 'L' : 'M') + X(t).toFixed(1) + ' ' + Y(y).toFixed(1); }
      svgEl('path', { d: d, fill: 'none', stroke: cols[k], 'stroke-width': 2, 'stroke-linejoin': 'round' }, s);
    });
    host.insertAdjacentHTML('beforeend', '<ul class="legend" style="margin-top:6px">' + taus.map(function (t, k) { return '<li><i class="ln" style="background:' + cols[k] + '"></i>' + t + ' s</li>'; }).join('') + '</ul>');
  });
  chart('holdChart', function (host, w) {
    var h = 250, m = { l: w < 520 ? 4 : 96, r: 12 }, T = 7, s = newSvg(host, w, h, 'Sketch: muscle activity, the true finger angle and a linear estimate over one repetition');
    var X = function (t) { return m.l + (w - m.l - m.r) * t / T; };
    var ph = [[0, 1.2, 'Rest', C.blue], [1.2, 2.0, 'Moving', C.aqua], [2.0, 4.6, 'Hold', C.orange], [4.6, 5.4, 'Moving', C.aqua], [5.4, 7, 'Rest', C.blue]];
    ph.forEach(function (p) { svgEl('rect', { x: X(p[0]) + 1, y: 6, width: X(p[1]) - X(p[0]) - 2, height: 6, rx: 3, fill: p[3] }, s); svgEl('text', { x: (X(p[0]) + X(p[1])) / 2, y: 28, 'text-anchor': 'middle', class: 'muted' }, s, p[2]); });
    function emg(t) { return t < 1.2 ? 0.06 : t < 2.0 ? 0.06 + 0.94 * Math.sin((t - 1.2) / 0.8 * Math.PI / 2) : t < 4.6 ? 0.32 + 0.68 * Math.exp(-(t - 2.0) / 0.35) : t < 5.0 ? 0.32 + 0.25 * Math.sin((t - 4.6) / 0.4 * Math.PI) : Math.max(0.06, 0.32 * Math.exp(-(t - 5.0) / 0.18)); }
    function ang(t) { return t < 1.2 ? 0 : t < 2.0 ? 0.5 - 0.5 * Math.cos((t - 1.2) / 0.8 * Math.PI) : t < 4.6 ? 1 : t < 5.4 ? 0.5 + 0.5 * Math.cos((t - 4.6) / 0.8 * Math.PI) : 0; }
    function est(t) { return t < 1.2 ? 0 : t < 2.0 ? ang(t) * 0.97 : t < 4.6 ? 0.63 + 0.34 * Math.exp(-(t - 2.0) / 0.45) : t < 5.4 ? ang(t) * 0.63 : 0; }
    function path(f, y0, hh) { var d = ''; for (var t = 0; t <= T + 0.001; t += 0.02) d += (d ? 'L' : 'M') + X(t).toFixed(1) + ' ' + (y0 + hh * (1 - f(t))).toFixed(1); return d; }
    var e0 = 44, eh = 62, a0 = 138, ah = 78;
    svgEl('path', { d: path(emg, e0, eh) + 'L' + X(T) + ' ' + (e0 + eh) + 'L' + X(0) + ' ' + (e0 + eh) + 'Z', fill: C.glow, opacity: .12 }, s);
    svgEl('path', { d: path(emg, e0, eh), fill: 'none', stroke: C.glow, 'stroke-width': 2 }, s);
    svgEl('path', { d: path(ang, a0, ah), fill: 'none', stroke: '#fff', 'stroke-width': 2 }, s);
    svgEl('path', { d: path(est, a0, ah), fill: 'none', stroke: C.orange, 'stroke-width': 2.5, 'stroke-dasharray': '1 6', 'stroke-linecap': 'round' }, s);
    svgEl('line', { x1: X(3.5), x2: X(3.5), y1: a0 + 4, y2: a0 + ah * (1 - 0.63) - 5, stroke: C.ink3, 'stroke-width': 1 }, s);
    svgEl('text', { x: X(3.5) + 8, y: a0 + ah * 0.2 + 4, class: 'val' }, s, 'the sag');
    if (w >= 520) { svgEl('text', { x: m.l - 12, y: e0 + eh / 2 + 4, 'text-anchor': 'end' }, s, 'Muscle effort'); svgEl('text', { x: m.l - 12, y: a0 + ah / 2 + 4, 'text-anchor': 'end' }, s, 'Finger angle'); }
    host.insertAdjacentHTML('beforeend', '<ul class="legend" style="margin-top:2px"><li><i class="ln" style="background:' + C.glow + '"></i>EMG envelope</li><li><i class="ln" style="background:#fff"></i>true angle</li><li><i class="ln" style="background:' + C.orange + '"></i>linear estimate from EMG</li></ul>');
  });
  chart('journeyChart', function (host, w) {
    var t = D.task1.able, rows = [
      { name: 'Ridge, current envelope only', who: 'no memory', v: D.history[0].mae },
      { name: 'Ridge + 1.5 s of history', who: 'memory, linear', v: t[0].v[3] },
      { name: 'Ridge on leaky integrators', who: 'longer memory, still linear', v: t[1].v[3] },
      { name: 'Neural net on leaky integrators', who: 'memory + nonlinear', v: t[3].v[3] },
      { name: 'Boosted trees on leaky integrators', who: 'memory + nonlinear', v: t[2].v[3] },
      { name: 'Net + trees averaged', who: 'the chosen model', v: t[4].v[3], color: C.orange, hi: true }
    ];
    hbars(host, w, rows, { max: 11.5, fmt: function (v) { return v.toFixed(2) + '°'; }, labelW: 290, axis: true, ticks: [0, 2, 4, 6, 8, 10], tickFmt: function (t) { return t + '°'; }, label: 'Mean absolute error of each Task 1 model on the test session' });
  });
  (function () {
    var tb = $('#aucTable tbody'); if (!tb) return;
    tb.innerHTML = D.auc.map(function (r) { return '<tr><td>' + r[0] + (r[0] > 10 ? ' (amputee)' : '') + '</td><td class="num">' + r[1].toFixed(2) + '</td><td class="num">' + r[2].toFixed(2) + '</td></tr>'; }).join('');
  })();

  /* =====================================================================
     4. Results: literature, phases, horizon
     ===================================================================== */
  function litRows(list) { return list.map(function (r) { return { name: r.name, who: r.who, v: r.v, color: r.ours ? C.orange : C.quiet, opacity: r.base ? .5 : 1, hi: r.ours && !r.base }; }); }
  var legendLit = '<ul class="legend" style="margin-top:8px"><li><i style="background:' + C.orange + '"></i>this project</li><li><i style="background:' + C.quiet + '"></i>published</li></ul>';
  chart('litMae', function (host, w) { hbars(host, w, litRows(D.litMAE), { max: 10.5, fmt: function (v) { return v.toFixed(2) + '°'; }, labelW: 215, rowH: 44, label: 'Mean absolute error of published DB8 models and ours' }); host.insertAdjacentHTML('beforeend', legendLit); });
  chart('litR2', function (host, w) { hbars(host, w, litRows(D.litR2), { max: 1.0, fmt: function (v) { return v.toFixed(2); }, labelW: 215, rowH: 44, label: 'R squared of published DB8 models and ours' }); host.insertAdjacentHTML('beforeend', legendLit); });

  (function () {
    var task = 'task1', group = 'able', view = 'chart', names = ['Rest', 'Hold', 'Moving'], cols = [C.blue, C.orange, C.aqua];
    var notes = {
      task1: 'Task 1 decodes posture from EMG alone. Holds were the worst phase for ridge; memory and a nonlinear readout cut that error by 44%. For the able-bodied group, rest error sits at the 4.3° resting-posture floor. Integrator rows use the same calibration as the chosen model.',
      task2: 'Task 2 knows the current angle and forecasts 100 ms ahead. When nothing moves, doing nothing is nearly perfect. During movement, momentum (no EMG) beats every EMG model. Rows come from two runs with slightly different EMG features (see the integrity notes).'
    };
    var c = chart('phaseChart', function (host, w) {
      var rows = D[task][group], max = 0; rows.forEach(function (r) { for (var i = 0; i < 3; i++) if (r.v[i] > max) max = r.v[i]; });
      var rowH = 70, top = 4, valW = 58, h = top + rows.length * rowH;
      var s = newSvg(host, w, h, 'Mean absolute error by phase for each model');
      var x0 = 0, x1 = w - valW, X = function (v) { return x0 + (x1 - x0) * v / (max * 1.02); };
      rows.forEach(function (r, i) {
        var y = top + i * rowH;
        svgEl('text', { x: 0, y: y + 15, class: r.chosen ? 'val' : '' }, s, r.name);
        svgEl('text', { x: w, y: y + 15, 'text-anchor': 'end', class: 'muted' }, s, 'overall ' + r.v[3].toFixed(2) + '°');
        for (var k = 0; k < 3; k++) (function (k) {
          var by = y + 24 + k * 11;
          var p = svgEl('path', { d: barPath(x0, by, X(r.v[k]) - x0, 9, 3), fill: cols[k], class: 'mk' }, s);
          svgEl('text', { x: X(r.v[k]) + 7, y: by + 8.5, class: 'val', style: 'font-size:11.5px' }, s, r.v[k].toFixed(2) + '°');
          var hit = svgEl('rect', { x: 0, y: by - 1, width: w, height: 11, class: 'hit' }, s);
          hover(hit, '<b>' + r.name + '</b><br>' + names[k] + ': ' + r.v[k].toFixed(2) + '°<br>overall: ' + r.v[3].toFixed(2) + '°');
          hit.addEventListener('pointerenter', function () { p.classList.add('on'); }); hit.addEventListener('pointerleave', function () { p.classList.remove('on'); });
        })(k);
        if (i) svgEl('line', { x1: 0, x2: w, y1: y - 4, y2: y - 4, class: 'grid' }, s);
      });
    });
    function table() {
      var rows = D[task][group];
      $('#phaseTable').innerHTML = '<table><thead><tr><th>Model</th><th class="num">Rest</th><th class="num">Hold</th><th class="num">Moving</th><th class="num">Overall</th></tr></thead><tbody>' +
        rows.map(function (r) { return '<tr' + (r.chosen ? ' class="ours"' : '') + '><td>' + r.name + '</td>' + r.v.map(function (v) { return '<td class="num">' + v.toFixed(2) + '°</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table>';
    }
    function sync() { $('#phaseChart').hidden = view !== 'chart'; $('#phaseTable').hidden = view !== 'table'; $('#phaseNote').textContent = notes[task] + (group === 'amputee' ? ' Two people only: read as case studies.' : ''); table(); if (view === 'chart') c.redraw(); }
    seg('phTask', function (v) { task = v; sync(); }); seg('phGroup', function (v) { group = v; sync(); }); seg('phView', function (v) { view = v; sync(); });
    sync();
  })();

  (function () {
    if (!$('#horSel')) return;
    var sel = 1, H = D.horizon, dl = D.delay, total = dl.filter + dl.envelope + dl.inferMedian, shown = 45; /* quoted as about 45 ms */
    function read() {
      var h = H.h[sel], net = Math.round(h - shown), extra = H.all.mae[sel] - H.all.mae[0];
      $('#horRead').innerHTML = '<li><b>' + H.all.mae[sel].toFixed(2) + '°</b>error, all 12 people (R² ' + H.all.r2[sel].toFixed(2) + ')</li>' +
        '<li><b>' + (sel ? '+' + extra.toFixed(2) + '°' : 'baseline') + '</b>' + (sel ? 'cost of looking ahead' : 'predicting the present') + '</li>' +
        '<li><b>' + (net > 0 ? '+' : net < 0 ? '−' : '') + Math.abs(net) + ' ms</b>nominal lead (horizon − estimated delay)</li>';
    }
    var b = chart('budgetChart', function (host, w) {
      var h = 150, mL = w < 520 ? 0 : 150, mR = 16, s = newSvg(host, w, h, 'Decoder delay compared with the prediction horizon');
      var MAX = 160, X = function (v) { return mL + (w - mL - mR) * v / MAX; }, hz = H.h[sel];
      svgEl('rect', { x: X(30), y: 22, width: X(100) - X(30), height: 84, fill: C.aqua, opacity: .1 }, s);
      svgEl('text', { x: X(65), y: 16, 'text-anchor': 'middle', class: 'muted' }, s, w < 520 ? 'EMG-to-force delay' : 'body’s own EMG-to-force delay, 30–100 ms');
      [0, 50, 100, 150].forEach(function (t) { svgEl('line', { x1: X(t), x2: X(t), y1: 22, y2: 110, class: t === 100 ? 'axis' : 'grid', stroke: t === 100 ? C.ink3 : undefined }, s); svgEl('text', { x: X(t), y: 126, 'text-anchor': t === 0 ? 'start' : 'middle', class: 'muted' }, s, t + ' ms'); });
      svgEl('text', { x: X(100) + 5, y: 142, class: 'muted' }, s, w < 520 ? '↑ practical limit' : '↑ practical limit, 100–125 ms');
      var y1 = 36, y2 = 76;
      if (w >= 520) { svgEl('text', { x: mL - 12, y: y1 + 11, 'text-anchor': 'end' }, s, 'Processing delay'); svgEl('text', { x: mL - 12, y: y2 + 11, 'text-anchor': 'end' }, s, 'Horizon'); }
      var parts = [['envelope window', dl.envelope, C.blue], ['inference', dl.inferMedian, '#6da7ec'], ['filters', dl.filter, '#cde2fb']], x = 0;
      parts.forEach(function (p, i) {
        var r = svgEl('path', { d: barPath(X(x) + (i ? 1 : 0), y1, X(x + p[1]) - X(x) - (i ? 1 : 0) - 1, 14, i === parts.length - 1 ? 4 : 0), fill: p[2], class: 'mk' }, s);
        hover(r, '<b>' + p[0] + '</b><br>' + (p[0] === 'filters' ? '1 to 3' : p[1]) + ' ms'); x += p[1];
      });
      svgEl('text', { x: X(total) + 8, y: y1 + 11, class: 'val' }, s, 'about 45 ms');
      if (hz > 0) { svgEl('path', { d: barPath(X(0), y2, X(hz) - X(0), 14, 4), fill: C.orange }, s); svgEl('text', { x: X(hz) + 8, y: y2 + 11, class: 'val' }, s, hz + ' ms ahead'); }
      else svgEl('text', { x: X(0) + 8, y: y2 + 11, class: 'muted' }, s, 'none: about 45 ms of processing delay is not covered');
      host.insertAdjacentHTML('beforeend', '<ul class="legend" style="margin-top:4px"><li><i style="background:' + C.blue + '"></i>envelope window, 25 ms</li><li><i style="background:#6da7ec"></i>inference, 16.5 ms</li><li><i style="background:#cde2fb"></i>filters, 1 to 3 ms</li><li><i style="background:' + C.orange + '"></i>prediction horizon</li></ul>');
    });
    var c1 = chart('horChart', function (host, w) {
      lines(host, w, { h: 220, x: ['0', '50', '100', '150 ms'], sel: sel, yMin: 5.5, yMax: 8.5, yTicks: [6, 7, 8], tickFmt: function (v) { return v + '°'; }, yFmt: function (v) { return v.toFixed(2) + '°'; }, tipX: function (i) { return H.h[i] + ' ms ahead'; },
        series: [{ name: 'Able-bodied', color: C.blue, y: H.able.mae, labelDy: 18 }, { name: 'Amputees', color: C.orange, y: H.amputee.mae }], label: 'Error of the final decoder against prediction horizon' });
    });
    var c2 = chart('t2Chart', function (host, w) {
      var t = D.task2Moving;
      lines(host, w, { h: 220, x: ['0', '50', '100', '150 ms'], sel: sel || null, yMin: 0, yMax: 4.5, yTicks: [0, 2, 4], tickFmt: function (v) { return v + '°'; }, yFmt: function (v) { return v.toFixed(2) + '°'; }, tipX: function (i) { return H.h[i] + ' ms ahead'; },
        series: [{ name: 'Persistence', color: C.quiet, y: t.pers, offset: 1 }, { name: 'Current angle + EMG', color: C.aqua, y: t.emg, offset: 1, labelDy: 18 }], label: 'Error during movement with the current angle known' });
    });
    seg('horSel', function (v) { sel = +v; read(); b.redraw(); c1.redraw(); c2.redraw(); });
    read();
  })();

  /* ---------- small squiggle in the window diagram ---------- */
  (function () {
    var p = $('#winTrace'); if (!p) return; var r = mulberry(7), d = '';
    for (var x = 24; x <= 460; x += 2.2) { var a = x < 170 ? 3 : 4 + 24 * Math.pow((x - 170) / 290, 1.6); d += (d ? 'L' : 'M') + x.toFixed(1) + ' ' + (85 + gauss(r) * a * 0.42).toFixed(1); }
    p.setAttribute('d', d);
  })();

  /* ---------- simulated-hand clips: a tile appears only if its file exists ---------- */
  (function () {
    var box = $('#clips'), grid = $('#clipGrid'), list = D.clips || []; if (!box || !grid || !list.length) return;
    var cap = $('#clipsCaption'); if (cap) cap.textContent = D.clipsCaption || '';
    var toggle = $('#clipsToggle'), viewer = $('#clipViewer'), big = viewer ? $('video', viewer) : null, bigCap = $('#clipViewerCap');
    var vids = [], userPaused = REDUCED, inView = false;
    function sync() {
      var run = inView && !userPaused && !document.hidden && !(viewer && viewer.open);
      vids.forEach(function (v) { if (run) { var p = v.play(); if (p && p.catch) p.catch(function () {}); } else v.pause(); });
      if (toggle) { toggle.textContent = userPaused ? 'Play all' : 'Pause all'; toggle.setAttribute('aria-pressed', String(userPaused)); }
    }
    function enlarge(c, v) {
      var url = 'assets/media/' + c.file;
      if (!viewer || !viewer.showModal) { window.open(url, '_blank'); return; }
      bigCap.textContent = c.title; big.src = url; big.currentTime = 0; viewer.showModal(); sync();
      var p = big.play(); if (p && p.catch) p.catch(function () {});
    }
    list.forEach(function (c, i) {
      var fig = document.createElement('figure'), btn = document.createElement('button'), v = document.createElement('video'), fc = document.createElement('figcaption');
      fig.className = 'clip'; fig.hidden = true;
      btn.type = 'button'; btn.setAttribute('aria-label', 'Enlarge clip ' + (i + 1) + ': ' + c.title);
      v.muted = true; v.loop = true; v.playsInline = true; v.preload = 'metadata';
      v.setAttribute('muted', ''); v.setAttribute('playsinline', '');
      var num = document.createElement('b'); num.textContent = String(i + 1); fc.appendChild(num);
      fc.appendChild(document.createTextNode(c.title));
      if (c.note) { var nt = document.createElement('span'); nt.textContent = c.note; fc.appendChild(nt); }
      v.addEventListener('loadedmetadata', function () {
        if (v.videoWidth) v.style.aspectRatio = v.videoWidth + ' / ' + v.videoHeight;
        fig.hidden = false; box.hidden = false; var w = $('#watchLink'); if (w) w.hidden = false;
        vids.push(v); sync();
      }, { once: true });
      v.addEventListener('error', function () { if (fig.parentNode) fig.parentNode.removeChild(fig); }, { once: true });
      btn.addEventListener('click', function () { enlarge(c, v); });
      btn.appendChild(v); fig.appendChild(btn); fig.appendChild(fc); grid.appendChild(fig);
      v.src = 'assets/media/' + c.file + '#t=0.1';
    });
    if (toggle) toggle.addEventListener('click', function () { userPaused = !userPaused; sync(); });
    if (viewer) {
      viewer.addEventListener('close', function () { big.pause(); big.removeAttribute('src'); big.load(); sync(); });
      viewer.addEventListener('click', function (ev) { if (ev.target === viewer) viewer.close(); });
    }
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { inView = es[0].isIntersecting; sync(); }, { rootMargin: '120px 0px' }).observe(grid);
    else inView = true;
    document.addEventListener('visibilitychange', sync);
  })();

  /* ---------- section rail: a neuron whose axon lights up as you scroll ----------
     Cell body and dendrites sit above the list; the axon runs down past every section, with a short
     side branch ending in a synapse beside each label. A bright copy of the same drawing is revealed
     from the top down to the reading position. */
  (function () {
    var links = $all('#rail a'), wrap = $('.railwrap'), ol = $('#rail'), svg = $('#railNeuron'); if (!links.length) return;
    var secs = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
    var AX = 15, BX = 33, nodeY = [], somaY = 0, endY = 0, clipRect = null, halo = null, built = false;
    function f1(v) { return v.toFixed(1); }
    function build() {
      built = false; if (!svg || !wrap || getComputedStyle(svg).display === 'none') return;
      var r = mulberry(21), H = wrap.offsetHeight, top = ol.offsetTop, thick = '', thin = '', dots = [];
      nodeY = links.map(function (a) { var li = a.parentNode; return top + li.offsetTop + li.offsetHeight / 2; });
      somaY = top - 28; endY = nodeY[nodeY.length - 1] + 26;
      /* dendrites: short random walks fanning up and out from the cell body, each with one side twig */
      [-2.85, -2.3, -1.75, -1.2, -0.7, -0.2].forEach(function (a0) {
        var a = a0 + (r() - 0.5) * 0.3, x = AX + Math.cos(a) * 6, y = somaY + Math.sin(a) * 5, n = 5 + Math.floor(r() * 2);
        thick += 'M' + f1(x) + ' ' + f1(y);
        for (var i = 0; i < n; i++) {
          a += (r() - 0.5) * 0.7; x += Math.cos(a) * 6.4; y += Math.sin(a) * 5.4; thick += 'L' + f1(x) + ' ' + f1(y);
          if (i === 1 || (i === 3 && r() < 0.5)) { var b = a + (r() < 0.5 ? -0.8 : 0.8), bx = x, by = y; thin += 'M' + f1(bx) + ' ' + f1(by); for (var k = 0; k < 2; k++) { b += (r() - 0.5) * 0.5; bx += Math.cos(b) * 5.5; by += Math.sin(b) * 5; thin += 'L' + f1(bx) + ' ' + f1(by); } }
        }
      });
      /* axon, with a slight wander between sections */
      var y0 = somaY + 5; thick += 'M' + AX + ' ' + f1(y0);
      nodeY.concat([endY]).forEach(function (y1) { var w = (r() - 0.5) * 5, g = (y1 - y0) / 3; thick += 'C' + f1(AX + w) + ' ' + f1(y0 + g) + ' ' + f1(AX - w) + ' ' + f1(y0 + 2 * g) + ' ' + AX + ' ' + f1(y1); y0 = y1; });
      /* one synapse beside each section label */
      nodeY.forEach(function (y) { thin += 'M' + AX + ' ' + f1(y - 4) + 'Q' + (AX + 3) + ' ' + f1(y) + ' ' + (BX - 4) + ' ' + f1(y); dots.push([BX, y, 3.6]); });
      /* axon terminals */
      [[-9, 13], [1, 17], [10, 12]].forEach(function (t) { thin += 'M' + AX + ' ' + f1(endY) + 'Q' + f1(AX + t[0] * 0.3) + ' ' + f1(endY + t[1] * 0.75) + ' ' + f1(AX + t[0]) + ' ' + f1(endY + t[1]); dots.push([AX + t[0], endY + t[1], 2.1]); });
      svg.innerHTML = ''; svg.setAttribute('viewBox', '0 0 60 ' + H); svg.setAttribute('width', 60); svg.setAttribute('height', H);
      function layer(parent, stroke, fill, somaFill) {
        var g = svgEl('g', { fill: 'none', stroke: stroke, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, parent);
        svgEl('path', { d: thick, 'stroke-width': 1.7 }, g); svgEl('path', { d: thin, 'stroke-width': 1 }, g);
        dots.forEach(function (c) { svgEl('circle', { cx: f1(c[0]), cy: f1(c[1]), r: c[2], fill: fill, 'stroke-width': 1.2 }, g); });
        svgEl('ellipse', { cx: AX, cy: f1(somaY), rx: 7.4, ry: 6.2, fill: somaFill, stroke: 'none' }, g);
        return g;
      }
      layer(svg, '#254a74', '#0d2340', '#254a74');
      var defs = svgEl('defs', {}, svg), cp = svgEl('clipPath', { id: 'railLit', clipPathUnits: 'userSpaceOnUse' }, defs);
      clipRect = svgEl('rect', { x: -40, y: -20, width: 160, height: 0 }, cp);
      var glow = svgEl('g', { class: 'lit' }, svg), lit = svgEl('g', { 'clip-path': 'url(#railLit)' }, glow);
      layer(lit, '#86d0ff', '#d6efff', '#e6f5ff');
      halo = svgEl('g', { class: 'halo' }, svg);
      svgEl('circle', { cx: BX, cy: 0, r: 9, fill: '#86d0ff', opacity: 0.16 }, halo);
      svgEl('circle', { cx: BX, cy: 0, r: 4.6, fill: '#ffffff' }, halo);
      built = true;
    }
    function update() {
      var y = window.scrollY + window.innerHeight * 0.35, cur = -1;
      secs.forEach(function (s, i) { if (s && s.offsetTop <= y) cur = i; });
      links.forEach(function (a, i) { a.classList.toggle('here', i === cur); a.classList.toggle('passed', i < cur); if (i === cur) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
      if (!built) return;
      if (cur < 0) { clipRect.setAttribute('height', 0); halo.style.opacity = 0; return; }
      var s = secs[cur], next = cur + 1 < nodeY.length ? nodeY[cur + 1] : endY + 22;
      var f = Math.max(0, Math.min(1, (y - s.offsetTop) / Math.max(1, s.offsetHeight)));
      if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4) f = 1;
      clipRect.setAttribute('height', f1(20 + nodeY[cur] + 6 + f * (next - nodeY[cur] - 8)));
      halo.style.opacity = 1; halo.style.transform = 'translate(0px,' + f1(nodeY[cur]) + 'px)';
    }
    var tick = false;
    window.addEventListener('scroll', function () { if (!tick) { tick = true; requestAnimationFrame(function () { update(); tick = false; }); } }, { passive: true });
    var rT; window.addEventListener('resize', function () { clearTimeout(rT); rT = setTimeout(function () { build(); update(); }, 150); });
    build(); update();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { build(); update(); });
  })();

  /* =====================================================================
     Hero: a drawn neuron and a scrolling EMG trace. Drawn once to an offscreen
     layer; only a few pulses and one trace are redrawn, at about 30 frames a second,
     and only while the hero is on screen.
     ===================================================================== */
  (function () {
    var cv = $('#heroCanvas'); if (!cv || !cv.getContext) return;
    var ctx = cv.getContext('2d'), layer = document.createElement('canvas'), lctx = layer.getContext('2d');
    var W = 0, H = 0, dpr = 1, paths = [], pulses = [], visible = true, raf = 0, last = 0, off = 0;
    var SIG = 2600, sig = new Float32Array(SIG), envl = new Float32Array(SIG);
    (function () { var r = mulberry(99), e = 0; for (var i = 0; i < SIG; i++) { var ph = (i % 650) / 650, target = ph > 0.28 && ph < 0.62 ? (ph < 0.36 ? 1 : 0.55) : 0.06; e += (target - e) * 0.03; envl[i] = e; sig[i] = gauss(r) * e; } })();

    function tone(a) { a = Math.max(0, Math.min(1, a)); return 'rgb(' + Math.round(14 + (158 - 14) * a) + ',' + Math.round(40 + (218 - 40) * a) + ',' + Math.round(72 + (255 - 72) * a) + ')'; }
    function branch(g, r, x, y, ang, len, wid, depth, alpha, pts, store) {
      var steps = Math.floor(len / 7);
      for (var i = 0; i < steps; i++) {
        ang += (r() - 0.5) * 0.42;
        var nx = x + Math.cos(ang) * 7, ny = y + Math.sin(ang) * 7, wd = Math.max(0.5, wid * (1 - i / steps * 0.55));
        g.beginPath(); g.moveTo(x, y); g.lineTo(nx, ny); g.lineWidth = wd; g.strokeStyle = tone(alpha); g.stroke();
        x = nx; y = ny; pts.push([x, y]);
        if (depth > 0 && i > 3 && r() < 0.085) branch(g, r, x, y, ang + (r() < 0.5 ? -1 : 1) * (0.45 + r() * 0.5), len * (0.45 + r() * 0.3), wd * 0.72, depth - 1, alpha * 0.9, pts.slice(), store);
      }
      if (depth > 0) for (var k = 0; k < 2; k++) branch(g, r, x, y, ang + (k ? 0.5 : -0.5) + (r() - 0.5) * 0.3, len * 0.55, wid * 0.45, depth - 1, alpha * 0.85, pts.slice(), store);
      else if (store && pts.length > 26) store.push(pts);
    }
    function neuron(g, seed, cx, cy, scale, alpha, store, axonTo) {
      var r = mulberry(seed), n = 6 + Math.floor(r() * 2), base = r() * 6.28;
      g.lineCap = 'round';
      for (var i = 0; i < n; i++) { var a = base + i * 6.283 / n + (r() - 0.5) * 0.5; if (axonTo && Math.abs(Math.sin(a) - 0.75) < 0.3 && Math.cos(a) < 0) continue; branch(g, r, cx + Math.cos(a) * 9 * scale, cy + Math.sin(a) * 9 * scale, a, (120 + r() * 110) * scale, 4.2 * scale, 3, alpha, [[cx, cy]], store); }
      if (axonTo) { /* one long axon heading down to the trace */
        var pts = [[cx, cy]], x = cx, y = cy, steps = 90;
        for (var s = 1; s <= steps; s++) { var t = s / steps, bx = cx + (axonTo[0] - cx) * (t * t * 0.6 + t * 0.4) + Math.sin(t * 9) * 14 * (1 - t), by = cy + (axonTo[1] - cy) * (1 - Math.pow(1 - t, 1.7)); g.beginPath(); g.moveTo(x, y); g.lineTo(bx, by); g.lineWidth = 2.6 * scale * (1 - t * 0.5); g.strokeStyle = tone(alpha * 0.95); g.stroke(); x = bx; y = by; pts.push([x, y]); }
        store.axon = pts;
      }
      var grd = g.createRadialGradient(cx - 3 * scale, cy - 3 * scale, 1, cx, cy, 20 * scale);
      grd.addColorStop(0, 'rgba(235,247,255,' + Math.min(1, alpha * 1.5) + ')'); grd.addColorStop(0.45, 'rgba(134,208,255,' + alpha + ')'); grd.addColorStop(1, 'rgba(60,130,200,0)');
      g.fillStyle = grd; g.beginPath(); g.ellipse(cx, cy, 17 * scale, 14 * scale, base, 0, 6.283); g.fill();
    }
    function build() {
      var r = cv.getBoundingClientRect(); W = Math.max(320, r.width); H = Math.max(320, r.height); dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      cv.width = layer.width = Math.round(W * dpr); cv.height = layer.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); lctx.setTransform(dpr, 0, 0, dpr, 0, 0); lctx.clearRect(0, 0, W, H);
      paths = []; var sc = Math.max(0.7, Math.min(1.5, W / 1100));
      /* Each neuron is drawn once into a scratch canvas, then composited: far ones through a single blur,
         the near one once blurred (its glow) and once sharp. One filtered draw per layer keeps this cheap. */
      function scratch(fn) { var c = document.createElement('canvas'); c.width = layer.width; c.height = layer.height; var g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); fn(g); return c; }
      var canBlur = typeof lctx.filter === 'string';
      var far = scratch(function (g) { neuron(g, 31, W * 0.58, H * 0.16, 0.8 * sc, canBlur ? 0.3 : 0.14, null, null); neuron(g, 12, W * 0.95, H * 0.64, 1.0 * sc, canBlur ? 0.26 : 0.12, null, null); });
      if (canBlur) lctx.filter = 'blur(' + (2.4 * sc).toFixed(1) + 'px)';
      lctx.drawImage(far, 0, 0, W, H);
      var cx = W < 760 ? W * 0.74 : W * 0.77, cy = W < 760 ? H * 0.2 : H * 0.34;
      var near = scratch(function (g) { neuron(g, 5, cx, cy, (W < 760 ? 0.85 : 1.25) * sc, W < 760 ? 0.5 : 0.72, paths, [W * 0.5, H - 62]); });
      if (canBlur) { lctx.filter = 'blur(' + (7 * sc).toFixed(1) + 'px)'; lctx.globalAlpha = 0.75; lctx.drawImage(near, 0, 0, W, H); lctx.filter = 'none'; lctx.globalAlpha = 1; }
      lctx.drawImage(near, 0, 0, W, H);
      pulses = [];
    }
    function along(p, t) { var f = t * (p.length - 1), i = Math.floor(f), a = p[i], b = p[Math.min(p.length - 1, i + 1)], u = f - i; return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]; }
    function trace(t) {
      var yb = H - 62, amp = 26, n = Math.floor(W / 2.5), step = 2.5, d0 = Math.floor(off);
      ctx.beginPath();
      for (var i = 0; i <= n; i++) { var k = (d0 + i) % SIG, y = yb + sig[k] * amp; if (i) ctx.lineTo(i * step, y); else ctx.moveTo(0, y); }
      ctx.lineWidth = 1; ctx.strokeStyle = 'rgba(134,208,255,.5)'; ctx.stroke();
      ctx.beginPath();
      for (i = 0; i <= n; i += 2) { k = (d0 + i) % SIG; y = yb - envl[k] * amp * 1.9; if (i) ctx.lineTo(i * step, y); else ctx.moveTo(0, y); }
      ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(233,241,251,.82)'; ctx.stroke();
    }
    function frame(now) {
      raf = 0; if (!visible) return;
      if (now - last < 32) { raf = requestAnimationFrame(frame); return; }
      var dt = Math.min(60, now - last || 33); last = now; off = (off + dt * 0.055) % SIG;
      ctx.clearRect(0, 0, W, H); ctx.drawImage(layer, 0, 0, W, H);
      if (paths.length && pulses.length < 5 && Math.random() < 0.035) { var useAxon = paths.axon && Math.random() < 0.4; pulses.push({ p: useAxon ? paths.axon : paths[Math.floor(Math.random() * paths.length)], t: useAxon ? 0 : 1, dir: useAxon ? 1 : -1, v: useAxon ? 0.00055 : 0.0009 }); }
      for (var i = pulses.length - 1; i >= 0; i--) {
        var q = pulses[i]; q.t += q.dir * q.v * dt; if (q.t < 0 || q.t > 1) { pulses.splice(i, 1); continue; }
        var xy = along(q.p, q.t), g = ctx.createRadialGradient(xy[0], xy[1], 0, xy[0], xy[1], 11);
        g.addColorStop(0, 'rgba(255,255,255,.95)'); g.addColorStop(0.3, 'rgba(160,220,255,.6)'); g.addColorStop(1, 'rgba(134,208,255,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(xy[0], xy[1], 11, 0, 6.283); ctx.fill();
      }
      trace();
      raf = requestAnimationFrame(frame);
    }
    function still() { ctx.clearRect(0, 0, W, H); ctx.drawImage(layer, 0, 0, W, H); trace(); }
    function start() { if (REDUCED) { still(); return; } if (!raf && visible) raf = requestAnimationFrame(frame); }
    build(); start();
    var bT; window.addEventListener('resize', function () { clearTimeout(bT); bT = setTimeout(function () { var r = cv.getBoundingClientRect(); if (Math.abs(r.width - W) > 2 || Math.abs(r.height - H) > 40) { build(); if (REDUCED) still(); } }, 200); });
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { visible = es[0].isIntersecting && !document.hidden; start(); }, { threshold: 0.02 }).observe(cv);
    document.addEventListener('visibilitychange', function () { visible = !document.hidden && cv.getBoundingClientRect().bottom > 0; start(); });
  })();
})();
