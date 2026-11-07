// Motion graphics for the finale film. Every scene is a pure function of time, drawn in a 1920x1080 design space,
// so the same code renders at 540p for the prototype and at 1080p/4K for the final without quality loss.
// All numbers come from the project's reports; see reports/finale_video/FAKTENCHECK.md.
const C = { bg: '#05080D', ink: '#EEF3F6', dim: '#8FA0AE', faint: '#1E2A36', sig: '#FF8A2A', cold: '#5CC8FF', white: '#FFFFFF', bad: '#FF5A5F' };
const F = { t: 'Bahnschrift', m: 'Cascadia Mono', s: 'Segoe UI', l: 'Segoe UI Light' };
const cv = document.getElementById('c'), g = cv.getContext('2d');
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ease = x => { x = clamp(x); return x * x * x * (x * (6 * x - 15) + 10); };
const seg = (t, a, b) => ease((t - a) / (b - a));
const inout = (t, a, b, c, d) => seg(t, a, b) * (1 - seg(t, c, d));
const de = (x, n = 2) => x.toFixed(n).replace('.', ',');
const lerp = (a, b, k) => a + (b - a) * k;
function rng(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }

function text(s, x, y, size, o = {}) {
  const a = o.a ?? 1; if (a <= 0.004) return;
  g.save(); g.globalAlpha = a; g.fillStyle = o.c || C.ink; g.textAlign = o.al || 'left'; g.textBaseline = o.bl || 'alphabetic';
  g.font = `${o.w || 400} ${size}px "${o.f || F.s}"`; if (o.sp) g.letterSpacing = o.sp + 'px';
  if (o.glow) { g.shadowColor = o.glowc || o.c || C.sig; g.shadowBlur = o.glow; }
  g.fillText(s, x, y); g.restore();
}
function line(x0, y0, x1, y1, c, w = 1, a = 1) { g.save(); g.globalAlpha = a; g.strokeStyle = c; g.lineWidth = w; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke(); g.restore(); }
function dot(x, y, r, c, a = 1, glow = 0) { g.save(); g.globalAlpha = a; g.fillStyle = c; if (glow) { g.shadowColor = c; g.shadowBlur = glow; } g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); g.restore(); }
function ringc(x, y, r, c, w = 1, a = 1, dash) { g.save(); g.globalAlpha = a; g.strokeStyle = c; g.lineWidth = w; if (dash) g.setLineDash(dash); g.beginPath(); g.arc(x, y, r, 0, 7); g.stroke(); g.restore(); }
function bg() { g.fillStyle = C.bg; g.fillRect(0, 0, 1920, 1080); }
function vignette(s = .75) { const r = g.createRadialGradient(960, 540, 320, 960, 540, 1150); r.addColorStop(0, 'rgba(0,0,0,0)'); r.addColorStop(1, `rgba(0,0,0,${s})`); g.fillStyle = r; g.fillRect(0, 0, 1920, 1080); }
function chapter(num, title, t, dur) {
  const a = inout(t, .15, .7, dur - .6, dur - .15), w = 300 * seg(t, .15, .9);
  text(`PROBLEM ${num} / 05`, 96, 92, 20, { f: F.m, c: C.sig, a, sp: 3 });
  text(title, 96, 132, 30, { f: F.t, a, sp: 1 });
  line(96, 150, 96 + w, 150, C.sig, 1.5, a * .7);
}
function foot(s, a = 1) { text(s, 96, 1020, 19, { c: C.dim, a, f: F.s }); }

// ---------- real terrain as hidden-line ridges ----------
const Z = DATA.twin.grid, ZR = Z.length, ZC = Z[0].length; let zMin = 1e9, zMax = -1e9;
for (const r of Z) for (const v of r) { zMin = Math.min(zMin, v); zMax = Math.max(zMax, v); }
function terrainProj(cam) {
  const cy = Math.cos(cam.yaw), sy = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
  return (u, v, h) => { // u,v in -1..1, h in world units
    const X = u * cam.zoom, Y = v * cam.zoom, x1 = X * cy - Y * sy, y1 = X * sy + Y * cy, z1 = h * cam.zoom;
    const yc = y1 * cp - z1 * sp, zc = y1 * sp + z1 * cp, d = 2.6 + yc;
    return [cam.cx + 900 * x1 / d, cam.cy + 900 * zc / d * -1 - 0, d];
  };
}
function drawRidges(cam, opt = {}) {
  const P = terrainProj(cam), step = opt.step || 2, exag = opt.exag || .5, reveal = opt.reveal ?? 1;
  const rows = []; for (let r = 0; r < ZR; r += step) rows.push(r);
  // Far to near so each row hides what lies behind it.
  const order = Math.cos(cam.yaw) >= 0 ? rows.slice().reverse() : rows;
  g.lineJoin = 'round';
  for (const r of order) {
    const v = (r / (ZR - 1)) * 2 - 1, pts = [];
    for (let c = 0; c < ZC; c += step) {
      const u = (c / (ZC - 1)) * 2 - 1, h = ((Z[r][c] - zMin) / (zMax - zMin)) * exag;
      pts.push(P(u, v, h));
    }
    const k = (r / ZR); if (k > reveal) continue;
    const fade = clamp((reveal - k) * 8);
    g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]));
    g.lineTo(pts[pts.length - 1][0], 1300); g.lineTo(pts[0][0], 1300); g.closePath();
    g.fillStyle = C.bg; g.fill();
    g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]));
    const fog = clamp(1.6 - pts[pts.length >> 1][2] * .42);
    g.strokeStyle = opt.color || `rgba(150,195,225,${(.14 + .55 * fog) * fade})`; g.lineWidth = opt.lw || 1.3; g.stroke();
  }
  return P;
}
function zAt(u, v, exag) { const c = clamp(Math.round((u + 1) / 2 * (ZC - 1)), 0, ZC - 1), r = clamp(Math.round((v + 1) / 2 * (ZR - 1)), 0, ZR - 1); return ((Z[r][c] - zMin) / (zMax - zMin)) * exag; }

// ---------- scenes (t in s, d = scene duration) ----------
const S = {};
const HALF = DATA.twin.half_m;

// The frozen film frame is scanned into real terrain; title reveal.
S.title = (t, d) => {
  bg();
  const cam = { yaw: .55 + t * .022, pitch: 1.0, zoom: 1.28, cx: 960, cy: 560 };
  const scan = seg(t, .2, 3.0);
  const P = drawRidges(cam, { reveal: .02 + scan * 1.1 });
  if (typeof FREEZE !== 'undefined' && FREEZE.complete && FREEZE.naturalWidth) {
    const yEdge = 1080 * (1 - scan) ;
    g.save(); g.beginPath(); g.rect(0, 0, 1920, yEdge); g.clip(); g.filter = `saturate(${1 - scan * .6})`; g.drawImage(FREEZE, 0, 0, 1920, 1080); g.restore();
    if (scan > 0 && scan < 1) { line(0, yEdge, 1920, yEdge, C.sig, 3, .95); g.fillStyle = 'rgba(255,138,42,.12)'; g.fillRect(0, yEdge, 1920, 70); }
  }
  // The one slope and its neighbours.
  const u = .1, v = -.55, h = zAt(u, v, .5), p = P(u, v, h);
  const a = seg(t, 3.0, 3.8);
  if (a > 0) {
    ringc(p[0], p[1], 16 + 80 * ((t * .35) % 1), C.sig, 2, a * (1 - ((t * .35) % 1)));
    dot(p[0], p[1], 8, C.sig, a, 30);
  }
  const ta = inout(t, 4.0, 5.2, d - .7, d - .1), z = 1 + .03 * (t - 4) / d;
  g.save(); g.translate(960, 540); g.scale(z, z); g.translate(-960, -540);
  text('TALWACHT', 960, 548, 168, { f: F.t, al: 'center', sp: 26, a: ta, glow: 40, glowc: 'rgba(120,190,240,.45)', w: 600 });
  text('WO ZUERST HINSCHAUEN, WENN DER STARKREGEN KOMMT', 960, 620, 25, { f: F.m, al: 'center', c: C.sig, sp: 5, a: ta * seg(t, 5.0, 5.8) });
  g.restore(); vignette(.8);
};

// Overlay plates (screen-blended over film): evidence for the climate claim.
S.climate = (t, d) => {
  g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 1080);
  const r = rng(11); for (let i = 0; i < 260; i++) { const x = r() * 2100 - 90, sp = 900 + r() * 900, L = 40 + r() * 70, y = ((r() * 1300 + t * sp) % 1300) - 110; line(x, y, x - L * .14, y + L, C.cold, 1, .1 + r() * .16); }
  const a1 = inout(t, .3, 1.1, d * .5, d * .5 + .6), v = 15 * seg(t, .5, 2.4);
  text(`+${Math.round(v)} %`, 960, 590, 250, { f: F.t, al: 'center', a: a1, glow: 45, glowc: 'rgba(92,200,255,.6)', w: 600 });
  text('STARKREGEN IN ÖSTERREICH · IN 40 JAHREN', 960, 660, 28, { f: F.m, al: 'center', c: C.cold, sp: 4, a: a1 * seg(t, 1.2, 2) });
  text('Quelle: GeoSphere Austria, 2025', 960, 706, 20, { al: 'center', c: C.dim, a: a1 * seg(t, 1.2, 2) });
  const a2 = seg(t, d * .5 + .5, d * .5 + 1.3) * (1 - seg(t, d - .5, d - .1));
  text('Regen, der Muren auslösen kann:', 960, 470, 44, { f: F.l, al: 'center', a: a2 });
  text('WAHRSCHEINLICHER · GRÖSSERE FLÄCHEN', 960, 560, 58, { f: F.t, al: 'center', c: C.sig, sp: 4, a: a2, glow: 26 });
  text('Projektion für Österreich, regional ungleich verteilt · Kaitna et al., Communications Earth & Environment, 2025', 960, 640, 22, { al: 'center', c: C.dim, a: a2 });
};

// Chapter label as a screen-blend plate over film.
S.ch2 = (t, d) => { g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 1080); chapter('02', 'GEGENBEISPIELE', t, d); };
S.five = (t, d) => {
  bg();
  const names = ['DATEN', 'GEGENBEISPIELE', 'SELBSTTÄUSCHUNG', 'WETTER', 'MELDEBIAS'];
  text('FÜNF PROBLEME', 960, 300, 26, { f: F.m, c: C.dim, al: 'center', sp: 8, a: inout(t, .2, .8, d - .5, d - .1) });
  names.forEach((n, i) => {
    const a = inout(t, .5 + i * .28, 1.0 + i * .28, d - .5, d - .1), x = 192 + i * 384, ly = 520 + (1 - seg(t, .5 + i * .28, 1.1 + i * .28)) * 30;
    text('0' + (i + 1), x, ly, 92, { f: F.t, al: 'center', c: i === 1 ? C.sig : C.ink, a, w: 300 });
    text(n, x, ly + 56, 21, { f: F.m, al: 'center', c: C.dim, a, sp: 2 });
    if (i) line(x - 384 + 96, 490, x - 96, 490, C.faint, 2, a);
  });
  vignette(.6);
};

// Real inventory points fall onto the real outline, the filter leaves the real 423.
function austria() {
  const R = DATA.austria; let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (const [x, y] of R) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  const k = Math.cos(47.6 * Math.PI / 180), sc = Math.min(1520 / ((x1 - x0) * k), 720 / (y1 - y0));
  const ox = 960 - sc * k * (x1 + x0) / 2, oy = 570 + sc * (y1 + y0) / 2;
  return { m: (x, y) => [ox + sc * k * x, oy - sc * y], R };
}
const AT = austria();
S.data = (t, d) => {
  bg(); chapter('01', 'DATEN', t, d);
  const a0 = seg(t, .1, 1.0);
  g.save(); g.globalAlpha = a0; g.beginPath(); AT.R.forEach(([x, y], i) => { const p = AT.m(x, y); i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]); }); g.closePath();
  g.fillStyle = '#0A1119'; g.fill(); g.strokeStyle = 'rgba(150,195,225,.65)'; g.lineWidth = 1.6; g.stroke(); g.restore();
  const I = DATA.inventory, n = I.length / 2, r = rng(7), rise = seg(t, .7, d * .34), scanT = seg(t, d * .4, d * .72), sx = 100 + 1720 * scanT;
  let shown = 0;
  g.fillStyle = C.cold;
  for (let i = 0; i < n; i++) {
    const del = r(); const k = clamp((rise - del * .85) / .15); if (k <= 0) continue;
    const p = AT.m(I[2 * i], I[2 * i + 1]), y = p[1] - (1 - ease(k)) * 90; shown++;
    if (p[0] < sx) continue;
    g.globalAlpha = .5 * k; g.fillRect(p[0], y, 2, 2);
  }
  g.globalAlpha = 1;
  if (scanT > 0 && scanT < 1) { line(sx, 170, sx, 960, C.sig, 3, .9); const gr = g.createLinearGradient(sx - 160, 0, sx, 0); gr.addColorStop(0, 'rgba(255,138,42,0)'); gr.addColorStop(1, 'rgba(255,138,42,.14)'); g.fillStyle = gr; g.fillRect(sx - 160, 170, 160, 790); }
  const Q = DATA.positives; for (let i = 0; i < Q.length / 2; i++) { const p = AT.m(Q[2 * i], Q[2 * i + 1]); if (p[0] < sx) dot(p[0], p[1], 3.2, C.sig, .95, 9); }
  const count = scanT > 0 ? Math.round(lerp(25609, 423, ease(scanT))) : Math.round(25609 * Math.min(1, rise / .9));
  text(count.toLocaleString('de-AT').replace(/ /g, ' '), 1824, 150, 104, { f: F.m, al: 'right', c: scanT >= 1 ? C.sig : C.ink, glow: scanT >= 1 ? 26 : 0, a: seg(t, .5, 1) });
  text(scanT >= 1 ? 'gesicherte Ereignisse: Datum, Prozess, Lage' : 'Einträge, alle Naturgefahren', 1824, 196, 23, { al: 'right', c: C.dim, a: seg(t, .5, 1) });
  foot('Daten: GeoSphere Austria, Naturgefahren-Inventar; Auswahl V0.4', seg(t, 1, 2));
};

// Real twin search: the real candidate pool of the Tamsweg event (05.07.2023).
S.twin = (t, d) => {
  bg(); chapter('02', 'GEGENBEISPIELE', t, d);
  const zoomIn = seg(t, 0, d * .9);
  const cam = { yaw: .25 + t * .012, pitch: .95 - .1 * zoomIn, zoom: 1.5, cx: 960, cy: 610 };
  const P = drawRidges(cam, { exag: .36, step: 2 });
  const tw = DATA.twin, toP = (x, y) => { const u = clamp(x / HALF, -1, 1), v = clamp(-y / HALF, -1, 1); return P(u, v, zAt(u, v, .36)); };
  const c0 = toP(0, 0);
  dot(c0[0], c0[1], 9, C.sig, seg(t, .2, .8), 30);
  text('Ereignis · Tamsweg', c0[0] + 22, c0[1] - 16, 24, { f: F.m, c: C.sig, a: inout(t, .4, 1, d - .7, d - .2) });
  // Ring 10 km
  const rg = seg(t, 1, 3);
  if (rg > 0) { g.save(); g.globalAlpha = .7 * rg; g.strokeStyle = C.cold; g.lineWidth = 2; g.setLineDash([9, 8]); g.beginPath(); for (let i = 0; i <= 90; i++) { const a = i / 90 * 6.283, q = toP(Math.cos(a) * 10000 * rg, Math.sin(a) * 10000 * rg); i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]); } g.stroke(); g.restore(); }
  // Candidates flicker, then real calipers remove them one by one.
  const P0 = tw.pool, N = P0.x.length, F1 = seg(t, 3.6, 4.4), F2 = seg(t, 5.0, 5.8), F3 = seg(t, 6.4, 7.2);
  const appear = seg(t, 1.6, 3.4), r = rng(5); let alive = 0;
  for (let i = 0; i < N; i++) {
    const del = r(); if (del > appear) continue;
    const sd = P0.slope_difference_deg[i], ed = P0.elevation_difference_m[i], ad = P0.aspect_difference_deg[i];
    const gone = Math.max(sd > 5 ? F1 : 0, ed > 150 ? F2 : 0, ad > 45 ? F3 : 0);
    if (gone < 1) alive++;
    if (gone >= 1) continue;
    const q = toP(P0.x[i], P0.y[i]);
    dot(q[0], q[1], 2.1, '#CFE2F0', .6 * (1 - gone));
  }
  const filters = [['NEIGUNG', '± 5°', 3.6], ['HÖHE', '± 150 m', 5.0], ['AUSRICHTUNG', '± 45°', 6.4]];
  filters.forEach(([a, b, s], i) => { const al = inout(t, s - .3, s + .2, d - .6, d - .2); text(a, 1520, 290 + i * 86, 20, { f: F.m, c: C.dim, sp: 3, a: al }); text(b, 1824, 296 + i * 86, 42, { f: F.t, al: 'right', a: al }); line(1520, 310 + i * 86, 1824, 310 + i * 86, C.faint, 1.5, al); });
  text(alive.toLocaleString('de-AT'), 1824, 190, 52, { f: F.m, al: 'right', a: inout(t, 2, 2.6, 8.6, 9.2) }); text('Kandidaten im Umkreis', 1824, 224, 20, { al: 'right', c: C.dim, a: inout(t, 2, 2.6, 8.6, 9.2) });
  // The real five stored controls.
  const five = seg(t, 8.0, 9.2);
  tw.controls.x.forEach((x, i) => {
    const q = toP(x, tw.controls.y[i]), k = seg(t, 8.0 + i * .22, 8.5 + i * .22);
    line(c0[0], c0[1], lerp(c0[0], q[0], k), lerp(c0[1], q[1], k), C.white, 1.4, .45 * k);
    dot(q[0], q[1], 8, C.white, k, 18); ringc(q[0], q[1], 17, C.white, 1.5, k * .6);
  });
  const a5 = inout(t, 9.2, 10, d - .6, d - .2);
  text('5', 1824, 200, 110, { f: F.t, al: 'right', c: C.ink, a: a5, glow: 20, glowc: '#9fd' });
  text('Zwillinge: nur ohne Meldung, nicht garantiert stabil', 1824, 240, 22, { al: 'right', c: C.dim, a: a5 });
  text('STICHTAG FÜR ALLE: 05.07.2023', 1824, 590, 24, { f: F.m, al: 'right', c: C.sig, sp: 2, a: a5 });
  foot('Echte Kandidaten und gespeicherte Kontrollen aus V0.4 · Umkreis 750 m bis 10 km', seg(t, 1, 2) * (1 - seg(t, d - .5, d - .1)));
  vignette(.55);
  // The slopes from the preceding film shot are scanned away into the real terrain model.
  if (typeof FREEZE2 !== 'undefined' && FREEZE2.complete && FREEZE2.naturalWidth && t < 1.6) {
    const yEdge = 1080 * (1 - seg(t, .05, 1.5));
    g.save(); g.beginPath(); g.rect(0, 0, 1920, yEdge); g.clip(); g.drawImage(FREEZE2, 0, 0, 1920, 1080); g.restore();
    line(0, yEdge, 1920, yEdge, C.sig, 3, .95); g.fillStyle = 'rgba(255,138,42,.12)'; g.fillRect(0, yEdge, 1920, 70);
  }
};

// Beat times in scene seconds, taken from the measured narration takes (see build_film.py).
const QT = { q1: 3.2, q2: 5.5 };
// Rain plate, screen-blended over the debris-flow stills.
S.rain = (t, d) => { g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 1080); const r = rng(31); for (let i = 0; i < 420; i++) { const x = r() * 2200 - 140, sp = 1500 + r() * 1100, L = 50 + r() * 90, y = ((r() * 1400 + t * sp) % 1400) - 150; line(x, y, x - L * .16, y + L, '#C9DCE8', 1.4, .1 + r() * .22); } };
const TIMES = {
  rules: { future: 3.3, gate: 6.7, tested: 10.2, group: 12.0, plan: 16.0, seal: 18.5, once: 21.3 },
  result: { pair: 7.5, curve: 14.5, proof: 22.9 },
  weather: { bars: 8.0, sameDay: 11.4, turn: 15.0, define: 20.7, chance: 26.2, measured: 29.6 },
  bias: { second: 17.8 },
  spuren: { count: 2.3, listen: 3.3, dark: 5.9 },
};
function lock(x, y, s, c, a) {
  g.save(); g.globalAlpha = a; g.strokeStyle = c; g.fillStyle = c; g.lineWidth = s * .13;
  g.beginPath(); g.arc(x, y - s * .25, s * .32, Math.PI, 0); g.stroke();
  g.fillRect(x - s * .5, y - s * .25, s, s * .8); g.restore();
}
function crossMark(x, y, r, c, a) { line(x - r, y - r, x + r, y + r, c, 9, a); line(x - r, y + r, x + r, y - r, c, 9, a); }
function cluster(cx, cy, a, split) {
  dot(cx, cy, 13, C.sig, a, 14);
  if (split) return;
  for (let i = 0; i < 5; i++) { const an = i / 5 * 6.283 - 1.57; dot(cx + Math.cos(an) * 42, cy + Math.sin(an) * 42, 9, C.white, a * .85); }
}
function potBox(x, y, w, h, label, a) {
  g.save(); g.globalAlpha = a; g.strokeStyle = C.dim; g.lineWidth = 2; g.strokeRect(x, y, w, h); g.restore();
  text(label, x + w / 2, y - 14, 20, { f: F.m, al: 'center', c: C.dim, sp: 3, a });
}

S.rules = (t, d) => {
  bg(); chapter('03', 'SELBSTTÄUSCHUNG', t, d);
  const T = TIMES.rules;
  // Beat 1: the real rain of one real event; the event day is a wall.
  const a1 = inout(t, .2, .7, T.group - .5, T.group);
  if (a1 > 0) {
    const R = DATA.rain, n = R.mm.length, x0 = 170, x1 = 1180, y0 = 760, H = 400, top = Math.max(...R.mm), w = (x1 - x0) / n;
    text('Regen pro Tag am Ereignisort · Tamsweg', x0, 262, 26, { a: a1 * seg(t, .5, 1), c: C.ink });
    line(x0, y0, 1780, y0, C.dim, 2, a1);
    [0, 10, 20, 30, 40].filter(v => v <= top).forEach(v => { const y = y0 - v / top * H; line(x0 - 8, y, x0, y, C.dim, 1.5, a1); text(v + ' mm', x0 - 16, y + 6, 18, { f: F.m, al: 'right', c: C.dim, a: a1 }); });
    for (let i = 0; i < n; i++) { const k = seg(t, .6 + i * .04, 1.0 + i * .04); g.save(); g.globalAlpha = a1 * k; g.fillStyle = C.cold; const h = R.mm[i] / top * H * k; g.fillRect(x0 + i * w + 2, y0 - h, w - 4, h); g.restore(); }
    [0, 30, 60].forEach(i => { const q = R.dates[i]; text(`${q.slice(8, 10)}.${q.slice(5, 7)}.`, x0 + i * w + w / 2, y0 + 34, 20, { f: F.m, al: 'center', c: C.dim, a: a1 }); });
    const af = a1 * seg(t, T.future, T.future + .5), al = a1 * seg(t, T.gate, T.gate + .5);
    if (af > 0) {
      g.save(); g.beginPath(); g.rect(x1, y0 - H - 30, 600, H + 30); g.clip(); g.globalAlpha = af * .35; g.strokeStyle = C.bad; g.lineWidth = 2;
      for (let i = -20; i < 40; i++) { g.beginPath(); g.moveTo(x1 + i * 34, y0); g.lineTo(x1 + i * 34 + H + 30, y0 - H - 30); g.stroke(); } g.restore();
      text('DIE ZEIT DANACH', 1480, 470, 34, { f: F.t, al: 'center', sp: 2, a: af * (1 - seg(t, T.gate, T.gate + .4)) });
      text('Wer sie kennt, sieht immer gut aus', 1480, 516, 25, { al: 'center', c: C.dim, a: af * (1 - seg(t, T.gate, T.gate + .4)) });
    }
    lock(1480, 440, 96, C.bad, al);
    text('GESPERRT', 1480, 556, 40, { f: F.t, al: 'center', c: C.bad, sp: 4, a: al });
    text('keine Daten ab dem Ereignis', 1480, 598, 25, { al: 'center', a: al });
    line(x1, y0 + 8, x1, y0 - H - 44, C.white, 4, a1 * seg(t, .3, .8));
    text('EREIGNISTAG t₀', x1, y0 - H - 92, 30, { f: F.t, al: 'center', sp: 2, a: a1 * seg(t, .5, 1), c: C.white });
    text('05.07.2023', x1, y0 - H - 58, 24, { f: F.m, al: 'center', c: C.dim, a: a1 * seg(t, .5, 1) });
    text('DAS DARF DAS MODELL SEHEN: 60 TAGE DAVOR', (x0 + x1) / 2, y0 + 84, 26, { f: F.t, al: 'center', c: C.cold, sp: 1.5, a: al });
    text('✓ automatisch getestet: jedes Merkmal endet vor t₀', 960, 940, 30, { f: F.t, al: 'center', c: C.ink, a: a1 * seg(t, T.tested, T.tested + .5) });
    foot('Echte INCA-Tageswerte aus dem V0.4-Cache', a1 * seg(t, 1, 2));
  }
  // Beat 2: wrong against right, because a twin in training lets the model recognise the place.
  const a2 = inout(t, T.group, T.group + .5, T.plan - .4, T.plan);
  if (a2 > 0) {
    const pan = (x, ok) => {
      const b = x + 40, y = 330, w = 320, h = 320, kx = x + 420;
      potBox(b, y, w, h, 'TRAINING', a2); potBox(kx, y, w, h, 'TEST', a2);
      if (ok) {
        cluster(b + 90, y + 95, a2); cluster(b + 230, y + 225, a2); cluster(kx + 160, y + 160, a2);
      } else {
        cluster(kx + 160, y + 160, a2, true);
        for (let i = 0; i < 5; i++) { const q = [b + 70 + i * 45, y + 90 + (i % 2) * 130]; line(q[0], q[1], kx + 160, y + 160, C.bad, 2, a2 * .7); dot(q[0], q[1], 9, C.white, a2 * .85); }
        crossMark(x + 390, y + h + 60, 26, C.bad, a2);
      }
    };
    pan(90, false); pan(1010, true);
    text('FALSCH', 490, 262, 34, { f: F.t, al: 'center', c: C.bad, sp: 4, a: a2 });
    text('RICHTIG', 1410, 262, 34, { f: F.t, al: 'center', c: C.cold, sp: 4, a: a2 });
    text('Zwilling im Training, Hang im Test: Das Modell erkennt nur den Ort wieder.', 490, 800, 25, { al: 'center', a: a2, c: C.dim });
    text('Ein Hang und seine Zwillinge bleiben immer im selben Teil.', 1410, 800, 25, { al: 'center', a: a2 });
    dot(790, 912, 12, C.sig, a2); text('betroffener Hang', 815, 920, 23, { a: a2, c: C.dim });
    dot(1040, 912, 9, C.white, a2); text('Zwillinge', 1062, 920, 23, { a: a2, c: C.dim });
  }
  // Beat 3: real time stamps of the registration, the freeze and the single scoring.
  const a3 = seg(t, T.plan - .1, T.plan + .4) * (1 - seg(t, d - .35, d - .05));
  if (a3 > 0) {
    const yb = 280, opened = seg(t, T.once, T.once + .6);
    potBox(280, yb, 560, 270, 'ENTWICKLUNG: DAMIT DURFTE ICH ARBEITEN', a3);
    text('123', 560, yb + 140, 96, { f: F.m, al: 'center', a: a3 }); text('Ereignisse · 19 Einheiten', 560, yb + 196, 25, { al: 'center', c: C.dim, a: a3 });
    potBox(1080, yb, 560, 270, 'VERSIEGELTER TEST', a3 * seg(t, T.seal, T.seal + .4));
    const as = a3 * seg(t, T.seal, T.seal + .4);
    text('300', 1360, yb + 140, 96, { f: F.m, al: 'center', a: as * opened }); text('Ereignisse · 11 Einheiten', 1360, yb + 196, 25, { al: 'center', c: C.dim, a: as * opened });
    lock(1360, yb + 120, 100, C.sig, as * (1 - opened));
    const X = [360, 960, 1560], yl = 730, labels = [['Plan festgeschrieben', '13:23', T.plan], ['Modell eingefroren', '15:39:31', T.seal], ['Test genau einmal ausgewertet', '15:39:41', T.once]];
    line(X[0], yl, lerp(X[0], X[2], seg(t, T.plan, T.once)), yl, C.sig, 3, a3);
    labels.forEach(([s, h, st], i) => { const k = a3 * seg(t, st, st + .4); dot(X[i], yl, 13, C.sig, k, 18); text(s, X[i], yl + 58, 28, { f: F.t, al: 'center', a: k }); text(h, X[i], yl + 94, 24, { f: F.m, al: 'center', c: C.dim, a: k }); });
    foot('Alle Zeiten 14.10.2026, UTC · eine Planänderung vor dem Test ist dokumentiert (Amendment 1)', a3);
  }
  vignette(.45);
};

S.result = (t, d) => {
  bg();
  const T = TIMES.result, a = seg(t, .2, .7), k = seg(t, .3, 2.0), v = lerp(.5, .751, k);
  // Beat 1: the number with its unit.
  const ab = 1 - seg(t, T.pair - .3, T.pair);
  text('ERGEBNIS · VERSIEGELTER TEST', 960, 210, 24, { f: F.m, al: 'center', c: C.dim, sp: 6, a: a * ab });
  text('AUC', 960, 310, 64, { f: F.t, al: 'center', c: C.sig, sp: 8, a: a * ab });
  text(de(v), 960, 620, 300, { f: F.m, al: 'center', a: a * ab, glow: 50, glowc: 'rgba(255,138,42,.55)' });
  text('Fläche unter der Kurve', 960, 770, 38, { f: F.l, al: 'center', a: a * ab * seg(t, 1.2, 1.8) });
  // Header that stays after the big reveal.
  const ah = seg(t, T.pair, T.pair + .4);
  text('AUC', 96, 118, 30, { f: F.t, c: C.sig, sp: 4, a: ah }); text('0,75', 178, 118, 44, { f: F.m, a: ah });
  // Beat 2: what is being counted. Eight example pairs (schema), then 100 comparisons.
  const a2 = inout(t, T.pair, T.pair + .4, T.curve - .4, T.curve);
  if (a2 > 0) {
    text('EIN BETROFFENER HANG GEGEN EINEN ZWILLING', 500, 240, 25, { f: F.t, al: 'center', sp: 1.5, a: a2 });
    text('Wen reiht das Modell weiter vorne?', 500, 280, 24, { al: 'center', c: C.dim, a: a2 });
    const won = [1, 1, 0, 1, 1, 1, 0, 1];
    won.forEach((ok, i) => {
      const c = i % 2, r = i >> 1, x = 110 + c * 400, y = 400 + r * 138, s = T.pair + .3 + i * .7, ka = a2 * seg(t, s, s + .3), kr = seg(t, s + .3, s + .6);
      slopeIcon(x + 40, y + 40, 86, 62, C.sig, ka); slopeIcon(x + 150, y + 40, 86, 62, '#DDE6EC', ka);
      if (kr > 0) { const wx = ok ? x + 40 : x + 150; text('VORNE', wx, y + 68, 16, { f: F.m, al: 'center', c: C.ink, a: a2 * kr }); text(ok ? '✓' : '✗', x + 262, y + 42, 50, { f: F.t, al: 'center', c: ok ? C.sig : C.dim, a: a2 * kr }); }
    });
    text('Schema', 500, 960, 20, { al: 'center', c: C.dim, a: a2 });
    const shown = Math.round(75 * seg(t, T.pair + 2.5, T.curve - .6));
    for (let i = 0; i < 100; i++) { const x = 1080 + (i % 10) * 58, y = 300 + (i / 10 | 0) * 58, on = i < shown; g.save(); g.globalAlpha = a2 * (on ? 1 : .22); g.fillStyle = on ? C.sig : '#40505E'; if (on) { g.shadowColor = C.sig; g.shadowBlur = 8; } g.fillRect(x, y, 44, 44); g.restore(); }
    text('100 SOLCHE VERGLEICHE', 1341, 240, 28, { f: F.t, al: 'center', sp: 1.5, a: a2 * seg(t, T.pair + 2.5, T.pair + 3) });
    text('orange: betroffener Hang vorne', 1341, 930, 26, { al: 'center', c: C.dim, a: a2 * seg(t, T.pair + 2.5, T.pair + 3) });
  }
  // Beat 3: the curve. y = x^(1/3) has an area of exactly 0.75.
  const a3 = inout(t, T.curve, T.curve + .4, T.proof - .4, T.proof);
  if (a3 > 0) {
    const x0 = 980, y0 = 900, S0 = 640, P = (u, w) => [x0 + u * S0, y0 - w * S0], grow = seg(t, T.curve + .3, T.curve + 4.5);
    g.save(); g.globalAlpha = a3 * .3; g.fillStyle = C.sig; g.beginPath(); g.moveTo(...P(0, 0));
    for (let i = 0; i <= 120; i++) { const u = i / 120 * grow; g.lineTo(...P(u, Math.cbrt(u))); } g.lineTo(...P(grow, 0)); g.closePath(); g.fill(); g.restore();
    g.save(); g.globalAlpha = a3; g.strokeStyle = C.sig; g.lineWidth = 5; g.beginPath(); for (let i = 0; i <= 120; i++) { const u = i / 120 * grow, p = P(u, Math.cbrt(u)); i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]); } g.stroke(); g.restore();
    g.save(); g.globalAlpha = a3; g.strokeStyle = C.cold; g.lineWidth = 3; g.setLineDash([12, 10]); g.beginPath(); g.moveTo(...P(0, 0)); g.lineTo(...P(1, 1)); g.stroke(); g.restore();
    g.save(); g.globalAlpha = a3; g.strokeStyle = C.dim; g.lineWidth = 2; g.strokeRect(x0, y0 - S0, S0, S0); g.restore();
    text('Fläche = 0,75', x0 + S0 * .62, y0 - S0 * .3, 38, { f: F.m, al: 'center', a: a3 * seg(t, T.curve + 4.5, T.curve + 5) });
    text('Münzwurf: Diagonale, Fläche 0,5', x0 + S0 * .5, y0 + 44, 22, { al: 'center', c: C.cold, a: a3 });
    text('Schema, nicht die gemessene Kurve', x0 + S0 * .5, y0 - S0 - 18, 21, { al: 'center', c: C.dim, a: a3 });
    const sc = (lab, sub, y, c, s) => { const q = a3 * seg(t, s, s + .4); text(lab, 150, y, 110, { f: F.m, c, a: q }); text(sub, 490, y - 16, 36, { f: F.l, a: q }); };
    sc('0,5', 'wie ein Münzwurf', 380, C.cold, T.curve + .2);
    sc('1,0', 'immer richtig', 560, C.ink, T.curve + 2.4);
    sc('0,75', 'rund 3 von 4 Vergleichen', 740, C.sig, T.curve + 4.5);
  }
  // Beat 4: how solid the number is.
  const a4 = seg(t, T.proof, T.proof + .5) * (1 - seg(t, d - .35, d - .05));
  if (a4 > 0) {
    const X = x => lerp(360, 1560, (x - .4) / .6), yS = 370, ci = seg(t, T.proof + .3, T.proof + 1.1);
    line(X(.4), yS, X(1), yS, C.faint, 3, a4);
    [.5, .6, .7, .8, .9, 1].forEach(q => { line(X(q), yS - 8, X(q), yS + 8, C.dim, 1.5, a4); text(de(q, 1), X(q), yS + 40, 20, { f: F.m, al: 'center', c: C.dim, a: a4 }); });
    text('Münzwurf', X(.5), yS - 24, 22, { al: 'center', c: C.cold, a: a4 }); line(X(.5), yS - 14, X(.5), yS + 8, C.cold, 3, a4);
    line(X(.751), yS, X(lerp(.751, .633, ci)), yS, C.sig, 9, a4); line(X(.751), yS, X(lerp(.751, .866, ci)), yS, C.sig, 9, a4);
    dot(X(.751), yS, 15, C.sig, a4, 24);
    text('0,75 · 95-%-Intervall [0,63; 0,87]', X(.751), yS - 34, 25, { f: F.m, al: 'center', c: C.sig, a: a4 * ci });
    text('11', 500, 620, 110, { f: F.m, al: 'center', a: a4 }); text('unabhängige Unwetterepisoden', 500, 668, 27, { al: 'center', c: C.dim, a: a4 });
    text('243 / 300', 960, 620, 88, { f: F.m, al: 'center', a: a4 }); text('Testereignisse aus einer Episode', 960, 668, 27, { al: 'center', c: C.dim, a: a4 });
    text('0,67', 1420, 620, 110, { f: F.m, al: 'center', a: a4 }); text('wenn jedes Ereignis gleich zählt', 1420, 668, 27, { al: 'center', c: C.dim, a: a4 });
    text('EINE RANGFOLGE, KEINE WAHRSCHEINLICHKEIT FÜR EINE RUTSCHUNG', 960, 830, 32, { f: F.t, al: 'center', sp: 2, a: a4 * seg(t, T.proof + .9, T.proof + 1.5) });
    text('Hangrutschungen allgemein · lokale AUC, jede Episode gleich gewichtet', 960, 884, 22, { al: 'center', c: C.dim, a: a4 });
  }
  vignette(.55);
};

function slopeIcon(x, y, w, h, c, a) { g.save(); g.globalAlpha = a; g.fillStyle = c; g.beginPath(); g.moveTo(x - w / 2, y); g.lineTo(x + w / 2, y); g.lineTo(x + w * .14, y - h); g.closePath(); g.fill(); g.restore(); }
S.weather = (t, d) => {
  bg(); chapter('04', 'WETTER', t, d);
  const T = TIMES.weather;
  // Beat 1: the expectation, unmistakably about data, not about the weather outside.
  const b1 = inout(t, .3, .9, T.bars - .4, T.bars);
  text('MEINE ERWARTUNG', 960, 370, 30, { f: F.m, al: 'center', c: C.cold, sp: 5, a: b1 });
  text('ZUSÄTZLICHE WETTERDATEN', 960, 490, 84, { f: F.t, al: 'center', sp: 2, a: b1 * seg(t, 3.3, 3.8), glow: 24, glowc: 'rgba(92,200,255,.5)' });
  text('↓', 960, 590, 70, { f: F.t, al: 'center', c: C.cold, a: b1 * seg(t, 4.6, 5) });
  text('BESSERE ERGEBNISSE DES MODELLS', 960, 690, 64, { f: F.t, al: 'center', sp: 2, a: b1 * seg(t, 5.4, 5.9) });
  // Beat 2: measured.
  const b2 = inout(t, T.bars, T.bars + .4, T.sameDay - .4, T.sameDay);
  if (b2 > 0) {
    const X = v => lerp(620, 1660, (v - .5) / .3), kb = i => seg(t, T.bars + .3 + i * .5, T.bars + .9 + i * .5);
    text('GEMESSEN IM VERSIEGELTEN TEST · AUC', 960, 240, 26, { f: F.m, al: 'center', c: C.dim, sp: 3, a: b2 });
    text('Balken beginnen bei 0,5 = Münzwurf', 620, 276, 20, { c: C.dim, a: b2 });
    [['Gelände allein', .702, '#DDE6EC'], ['Gelände + Wetterdaten', .751, C.sig]].forEach(([n, v, c], i) => { const y = 340 + i * 110, q = kb(i); text(n, 590, y + 12, 32, { al: 'right', a: b2 * q }); g.save(); g.globalAlpha = b2 * q; g.fillStyle = c; g.fillRect(620, y - 32, (X(v) - 620) * q, 60); g.restore(); text(de(v), X(v) + 20, y + 14, 38, { f: F.m, a: b2 * q }); });
    text('Zuwachs +0,05 [−0,00; +0,11]', 960, 600, 42, { f: F.m, al: 'center', c: C.cold, a: b2 * kb(2) });
    text('Das Intervall berührt die Null', 960, 650, 28, { al: 'center', c: C.dim, a: b2 * kb(2) });
    text('NICHT BELEGT', 960, 770, 76, { f: F.t, al: 'center', sp: 6, c: C.sig, a: b2 * kb(3), glow: 22 });
  }
  // Beat 3: why. Same day, nearly the same rain over all six slopes.
  const a1 = inout(t, T.sameDay, T.sameDay + .4, T.turn - .4, T.turn);
  if (a1 > 0) {
    const r = rng(9); for (let i = 0; i < 280; i++) { const x = 240 + r() * 1440, sp = 700 + r() * 500, y = 230 + ((r() * 420 + t * sp) % 420); line(x, y, x - 4, y + 22, C.cold, 1.2, a1 * .4); }
    for (let i = 0; i < 6; i++) { const x = 400 + i * 224; slopeIcon(x, 770, 200, 110, i === 0 ? C.sig : '#DDE6EC', a1); }
    text('GLEICHER TAG, FAST DASSELBE WETTER', 960, 870, 36, { f: F.t, al: 'center', sp: 3, a: a1 });
  }
  // Beat 4: same place, different times. The 5 % is a definition, not a guess.
  const a2 = seg(t, T.turn, T.turn + .5) * (1 - seg(t, d - .4, d - .1));
  if (a2 > 0) {
    text('WAR ES VOR DER RUTSCHUNG NASSER ALS SONST AN DIESEM ORT?', 960, 200, 34, { f: F.t, al: 'center', sp: 3, a: a2 });
    text('Extrem nass = die nassesten 5 von 100 Zeiträumen (je 3 Tage) an diesem Ort, zu dieser Jahreszeit, 1991 bis 2025', 960, 244, 25, { al: 'center', c: C.dim, a: a2 * seg(t, T.define, T.define + .5) });
    const G = (x0, n, lab, big, s) => { for (let i = 0; i < 100; i++) { const c = i % 10, ro = i / 10 | 0, x = x0 + c * 44, y = 290 + ro * 44, on = i < n && t > s + i * .05; g.save(); g.globalAlpha = a2 * (on ? 1 : .18); g.fillStyle = on ? (big ? C.cold : '#DDE6EC') : '#40505E'; if (on && big) { g.shadowColor = C.cold; g.shadowBlur = 16; } g.fillRect(x, y, 33, 33); g.restore(); } const q = a2 * seg(t, s, s + .5); text(lab[0], x0 + 203, 800, 64, { f: F.m, al: 'center', c: big ? C.cold : C.ink, a: q }); text(lab[1], x0 + 203, 846, 25, { al: 'center', c: C.dim, a: q }); };
    G(320, 5, ['5 von 100', 'wenn der Regen egal wäre'], false, T.chance); G(1160, 25, ['rund 25 von 100', 'gemessen vor dokumentierten Rutschungen'], true, T.measured);
    text('24,6 % [11,8; 38,2] · 35 Episoden · explorativ, vorab festgelegter Haupttest knapp nicht erfüllt, Meldebias möglich', 960, 960, 22, { al: 'center', c: C.dim, a: a2 * seg(t, T.measured, T.measured + .8) });
  }
  vignette(.5);
};

S.bias = (t, d) => {
  bg(); chapter('05', 'MELDEBIAS', t, d);
  const H = DATA.roads_half_m, sc = 960 / (2 * H), M = (x, y) => [1370 + (x) * sc * .98, 560 - y * sc * .98], draw = seg(t, .5, d * .42), ev = DATA.stanz_events, sw = TIMES.bias.second;
  g.save(); g.beginPath(); g.rect(860, 100, 1020, 900); g.clip(); g.strokeStyle = 'rgba(255,200,130,.85)'; g.lineWidth = 1.7; const nR = DATA.roads.length;
  for (let i = 0; i < nR * draw; i++) { const L = DATA.roads[i]; g.beginPath(); for (let j = 0; j < L.length; j += 2) { const p = M(L[j], L[j + 1]); j ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]); } g.stroke(); }
  const ak = seg(t, d * .2, d * .4); for (let i = 0; i < ev.length / 2; i++) { const p = M(ev[2 * i], ev[2 * i + 1]); dot(p[0], p[1], 4.6, C.sig, ak, 12); }
  g.restore();
  const a1 = inout(t, 3.2, 3.8, sw - .5, sw);
  text('AUC', 120, 300, 40, { f: F.t, c: C.sig, sp: 6, a: a1 });
  text('0,93', 120, 490, 200, { f: F.m, a: a1, glow: 30, glowc: 'rgba(255,190,110,.5)' });
  text('nur Abstand zu Straßen und Häusern', 120, 566, 32, { a: a1 });
  text('In 93 von 100 Vergleichen steht der', 120, 626, 27, { c: C.dim, a: a1 * seg(t, 9.9, 10.4) });
  text('gemeldete Hang vor einem Umgebungspunkt,', 120, 662, 27, { c: C.dim, a: a1 * seg(t, 9.9, 10.4) });
  text('ohne jedes Wissen über den Berg.', 120, 698, 27, { c: C.dim, a: a1 * seg(t, 9.9, 10.4) });
  text('GEMELDET WIRD, WAS MENSCHEN SEHEN.', 120, 770, 30, { f: F.t, c: C.sig, sp: 1.5, a: a1 * seg(t, 15.4, 15.9) });
  text('Vergleichspunkte hier ungematcht, keine Zwillinge · explorativ', 120, 816, 21, { c: C.dim, a: a1 });
  const a2 = seg(t, sw, sw + .6) * (1 - seg(t, d - .4, d - .1));
  text('AUC', 120, 300, 40, { f: F.t, c: C.sig, sp: 6, a: a2 });
  text('0,78', 120, 490, 200, { f: F.m, c: C.sig, a: a2, glow: 34 });
  text('Gelände, nur Hänge ähnlich nah an Straßen', 120, 566, 29, { a: a2 });
  text('und Gebäuden', 120, 604, 29, { a: a2 });
  text('[0,68; 0,89] · 173 Gruppen, 10 Einheiten · explorativ', 120, 654, 21, { f: F.m, c: C.dim, a: a2 });
  text('EIN TEIL DES SIGNALS BLEIBT MELDEVERHALTEN.', 120, 730, 27, { f: F.t, sp: 1, a: a2 * seg(t, d - 4.3, d - 3.8) });
  foot('Echte Straßen (OpenStreetMap, heutiger Stand) und Ereignisse (V0.4) um Stanz im Mürztal', seg(t, 1, 2) * (1 - seg(t, d - .5, d - .1)));
};

// Words of the closing quote, screen-blended over the film shots.
const quoteLine = (s, y, a) => text(s, 960, y, 62, { f: F.l, al: 'center', a, glow: 18, glowc: 'rgba(0,0,0,.9)' });
S.q1 = (t, d) => {
  g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 1080);
  const end = 1 - seg(t, d - .5, d - .1);
  quoteLine('Der Berg warnt nicht.', 500, seg(t, QT.q1, QT.q1 + .5) * end);
  quoteLine('Der Berg erklärt nichts.', 590, seg(t, QT.q2, QT.q2 + .5) * end);
};
S.q2 = (t, d) => {
  g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 1080);
  quoteLine('Aber er hat Spuren hinterlassen.', 540, seg(t, .2, .7) * (1 - seg(t, d - .35, d - .05)));
};
// The real 423 events light up on the real outline, then everything falls quiet before the title.
S.spuren = (t, d) => {
  bg();
  const T = TIMES.spuren, Q = DATA.positives, n = Q.length / 2, r = rng(23), order = Array.from({ length: n }, (_, i) => [r(), i]).sort((a, b) => a[0] - b[0]);
  const fall = 1 - seg(t, T.dark, T.dark + .6), hush = 1 - .55 * seg(t, T.listen, T.listen + 1);
  g.save(); g.globalAlpha = seg(t, 0, .4) * fall; g.beginPath(); AT.R.forEach(([x, y], i) => { const p = AT.m(x, y); i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]); }); g.closePath();
  g.fillStyle = '#0A1119'; g.fill(); g.strokeStyle = 'rgba(150,195,225,.6)'; g.lineWidth = 1.6; g.stroke(); g.restore();
  const lit = Math.round(n * ease(clamp(t / T.count)));
  for (let j = 0; j < lit; j++) { const i = order[j][1], p = AT.m(Q[2 * i], Q[2 * i + 1]), age = t - j / n * T.count; dot(p[0], p[1], 4.4 + 8 * Math.exp(-age * 3), C.sig, fall * hush, 14); }
  text(String(lit), 1824, 190, 120, { f: F.m, al: 'right', c: C.sig, glow: 30, a: fall * hush * seg(t, .1, .4) });
  text('Mal', 1824, 240, 34, { f: F.l, al: 'right', a: fall * hush * seg(t, T.count - .4, T.count) });
  for (let i = 0; i < 3; i++) { const u = ((t - T.listen) / 2.6 + i / 3) % 1; if (t > T.listen) ringc(960, 560, 60 + u * 760, C.cold, 1.5, (1 - u) * .35 * fall); }
  text('Ich habe angefangen zuzuhören.', 960, 950, 58, { f: F.l, al: 'center', a: seg(t, T.listen, T.listen + .5) * fall });
  vignette(.6);
};

S.fazit = (t, d) => {
  g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 1080);
  const a1 = inout(t, .1, .7, d - .7, d - .1);
  text('WAS TALWACHT KANN', 460, 330, 24, { f: F.m, c: C.sig, sp: 4, al: 'center', a: a1 });
  text('Hänge ordnen', 460, 410, 54, { f: F.t, al: 'center', a: a1 * seg(t, .3, .9) });
  text('zeigen, wo man zuerst hinschaut', 460, 470, 30, { f: F.l, al: 'center', a: a1 * seg(t, .3, .9) });
  const k = d * .35;
  text('WAS ES NICHT KANN', 1400, 330, 24, { f: F.m, c: C.cold, sp: 4, al: 'center', a: a1 * seg(t, k, k + .5) });
  ['nicht warnen', 'keine Wahrscheinlichkeit nennen', 'nicht markiert heißt nicht sicher', 'reine Hangmuren: 0,54 [0,41; 0,67]'].forEach((s, i) => text(s, 1400, 410 + i * 58, i < 1 ? 42 : 30, { f: i < 1 ? F.t : F.l, al: 'center', a: a1 * seg(t, k + .3 + i * .5, k + .8 + i * .5) }));
};
S.next = (t, d) => {
  g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 1080);
  const a = inout(t, .2, .9, d - .5, d - .1);
  text('NÄCHSTER SCHRITT', 960, 450, 24, { f: F.m, c: C.sig, sp: 5, al: 'center', a });
  text('EIN TEST MIT EREIGNISSEN, DIE NOCH NICHT PASSIERT SIND', 960, 530, 46, { f: F.t, al: 'center', sp: 1, a: a * seg(t, .4, 1.1) });
  text('vorab festgelegt · einmal ausgewertet', 960, 590, 26, { f: F.l, al: 'center', a: a * seg(t, .8, 1.5) });
};
S.end = (t, d) => {
  bg();
  const cam = { yaw: .55 + (t + 12) * .022, pitch: 1.0, zoom: 1.28, cx: 960, cy: 620 };
  const P = drawRidges(cam, { reveal: 1.1 });
  const p = P(.1, -.55, zAt(.1, -.55, .5)), a = seg(t, .2, .8);
  ringc(p[0], p[1], 16 + 80 * ((t * .35) % 1), C.sig, 2, a * (1 - ((t * .35) % 1))); dot(p[0], p[1], 8, C.sig, a, 30);
  g.fillStyle = 'rgba(5,8,13,.55)'; g.fillRect(0, 0, 1920, 1080);
  const ta = seg(t, 0, .12), z = 1.05 - .05 * seg(t, 0, d);
  g.save(); g.translate(960, 500); g.scale(z, z); g.translate(-960, -500);
  text('TALWACHT', 960, 500, 168, { f: F.t, al: 'center', sp: 26, a: ta, glow: 40 + 60 * (1 - seg(t, 0, 1.5)), glowc: 'rgba(120,190,240,.55)', w: 600 });
  g.restore();
  text('WO ZUERST HINSCHAUEN, WENN DER STARKREGEN KOMMT', 960, 572, 25, { f: F.m, al: 'center', c: C.sig, sp: 5, a: seg(t, 1.2, 2) });
  const af = seg(t, 2.6, 3.4);
  text('Daten: GeoSphere Austria (Inventar, INCA, SPARTACUS, SNOWGRID) · Skadi/SRTM · CORINE · OpenStreetMap · Klima: GeoSphere 2025; Kaitna et al. 2025', 960, 950, 19, { al: 'center', c: C.dim, a: af });
  text('Forschungsprototyp, kein Warnsystem · Filmaufnahmen: KI-generierte Illustrationen', 960, 984, 19, { al: 'center', c: C.dim, a: af });
  vignette(.7);
};

// Scenes that hold still for a while get a very slow push-in so the picture never stands completely still.
const PUSH = { rules: .012, result: .012, weather: .012, bias: .02, spuren: .03 };
window.drawScene = (name, t, d) => {
  const k = cv.width / 1920, z = 1 + (PUSH[name] || 0) * t / d;
  g.setTransform(k * z, 0, 0, k * z, k * 960 * (1 - z), k * 540 * (1 - z));
  g.globalAlpha = 1; g.filter = 'none'; S[name](t, d);
};
window.sceneNames = Object.keys(S);
