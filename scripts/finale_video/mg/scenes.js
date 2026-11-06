// Motion graphics for the finale film. Every scene is a pure function of time, drawn in a 1920x1080 design space,
// so the same code renders at 540p for the prototype and at 1080p/4K for the final without quality loss.
// All numbers come from the project's reports; see reports/finale_video/FAKTENCHECK.md.
const C = { bg: '#05080D', ink: '#EEF3F6', dim: '#8FA0AE', faint: '#1E2A36', sig: '#FF8A2A', cold: '#5CC8FF', white: '#FFFFFF' };
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
};

S.rules = (t, d) => {
  bg(); chapter('03', 'SELBSTTÄUSCHUNG', t, d);
  const a1 = inout(t, .2, .8, d * .36, d * .36 + .5);
  if (a1 > 0) {
    const X = 1050; const r = rng(3);
    for (let i = 0; i < 240; i++) { const y = 240 + r() * 600, v = 200 + r() * 340, ph = r() * 6, life = 1100 / v, u = ((t + ph) % life) / life, xFree = 1860 - u * 1400; const hit = xFree < X; const x = hit ? X + (X - xFree) * .42 : xFree; const fade = hit ? clamp(1 - (X - xFree) / 520) : 1; dot(x, y + (hit ? (X - xFree) * (r() - .5) * .4 : 0), 4, C.cold, a1 * .9 * fade, 10); }
    for (let i = 0; i < 120; i++) { const y = 240 + r() * 600, u = (t * (.08 + r() * .12) + r()) % 1; dot(220 + u * 800, y, 4, C.sig, a1 * .85, 10); }
    line(X, 210, X, 870, C.white, 3, a1); g.save(); g.globalAlpha = a1 * .08; g.fillStyle = C.white; g.fillRect(X, 210, 22, 660); g.restore();
    text('t₀', X, 196, 38, { f: F.m, al: 'center', a: a1 });
    text('VOR DEM EREIGNIS: ERLAUBT', 620, 930, 24, { f: F.m, al: 'center', c: C.sig, sp: 2, a: a1 });
    text('AB DEM EREIGNIS: GESPERRT', 1490, 930, 24, { f: F.m, al: 'center', c: C.cold, sp: 2, a: a1 });
  }
  const a2 = inout(t, d * .345, d * .345 + .5, d * .66, d * .66 + .5);
  if (a2 > 0) {
    const k = seg(t, d * .345 + .4, d * .345 + 1.8), cols = 4; const y0 = 300;
    for (let c = 0; c < cols; c++) {
      const x0 = 300 + c * 340, w = 280, h = 200 + 0;
      for (let i = 0; i < 6; i++) { const r0 = rng(c * 13 + i + 3), fromX = x0 + r0() * 300 - 150, fromY = y0 + r0() * 400 - 150, tx = x0 + 42 + (i % 3) * 98, ty = y0 + 60 + (i >> 1 & 1 ? 110 : 0) + 0; const x = lerp(fromX, tx, k), y = lerp(fromY, ty + (i >= 3 ? 110 : 0) - (i >> 1 & 1 ? 110 : 0), k); dot(x, y, 15, i === 0 ? C.sig : C.white, a2 * (i === 0 ? 1 : .78), i === 0 ? 18 : 0); }
      g.save(); g.globalAlpha = a2 * seg(t, d * .345 + 1.6, d * .345 + 2.1); g.strokeStyle = C.ink; g.lineWidth = 2; g.strokeRect(x0, y0, w, 240); g.restore();
    }
    text('EIN HANG UND SEINE ZWILLINGE: IMMER IM SELBEN TEIL DER DATEN', 960, 720, 26, { f: F.m, al: 'center', sp: 1.5, a: a2 });
  }
  const a3 = seg(t, d * .69, d * .69 + .5) * (1 - seg(t, d - .35, d - .05));
  if (a3 > 0) {
    const close = seg(t, d * .71, d * .71 + 1.4), cx = 960, cy = 500, R = 190, spin = close * 2.4;
    for (let i = 0; i < 6; i++) { const an = i / 6 * 6.283 + spin, x0 = cx + Math.cos(an) * (R + (1 - close) * 90), y0 = cy + Math.sin(an) * (R + (1 - close) * 90); line(cx, cy, x0, y0, C.sig, 4, a3 * (.3 + .7 * close)); }
    ringc(cx, cy, R, C.sig, 5, a3); ringc(cx, cy, R + 20, C.sig, 1.5, a3 * .6); ringc(cx, cy, 44, C.sig, 5, a3);
    const lab = seg(t, d * .71 + 1, d * .71 + 1.6);
    text('VERSIEGELTER TEST', 960, 790, 58, { f: F.t, al: 'center', sp: 8, a: a3 * lab, glow: 22 });
    text('vorab festgeschrieben · genau einmal ausgewertet', 960, 842, 25, { c: C.dim, al: 'center', a: a3 * lab });
  }
  vignette(.55);
};

S.result = (t, d) => {
  bg();
  const k = seg(t, .3, 2.0), v = lerp(.5, .751, k), a = seg(t, .2, .7), lift = seg(t, d * .46, d * .46 + 1);
  text('ERGEBNIS · VERSIEGELTER TEST', 960, lerp(240, 150, lift), 24, { f: F.m, al: 'center', c: C.dim, sp: 6, a });
  text(de(v), 960, lerp(580, 370, lift), lerp(300, 200, lift), { f: F.m, al: 'center', a, glow: 50, glowc: 'rgba(255,138,42,.55)', c: C.ink });
  // scale 0.4..1
  const X = x => lerp(420, 1500, (x - .4) / .6), yS = lerp(720, 500, lift), aS = seg(t, 1.6, 2.4);
  line(X(.4), yS, X(1), yS, C.faint, 3, aS);
  [.5, .6, .7, .8, .9, 1].forEach(q => { line(X(q), yS - 8, X(q), yS + 8, C.dim, 1.5, aS); text(de(q, 1), X(q), yS + 40, 19, { f: F.m, al: 'center', c: C.dim, a: aS }); });
  text('Zufall', X(.5), yS - 22, 21, { al: 'center', c: C.cold, a: aS }); line(X(.5), yS - 14, X(.5), yS + 8, C.cold, 3, aS);
  const ci = seg(t, 2.2, 3); line(X(.633), yS, X(lerp(.633, .866, ci)), yS, C.sig, 8, aS);
  dot(X(.751), yS, 13, C.sig, aS, 22);
  text('95-%-Intervall [0,63; 0,87]', X(.751), yS - 26, 21, { f: F.m, al: 'center', c: C.sig, a: seg(t, 2.8, 3.4) });
  const bars = [['Gelände + Wetter', .751, C.sig], ['Gelände allein', .702, C.ink], ['Wetter allein', .604, C.cold]];
  bars.forEach(([n, b, c], i) => { const s = d * .46 + .6 + i * .3, kb = seg(t, s, s + .8), y = 640 + i * 62; text(n, 400, y + 8, 24, { al: 'right', a: kb }); g.save(); g.globalAlpha = kb; g.fillStyle = c; g.fillRect(420, y - 16, (X(b) - 420) * kb, 28); g.restore(); text(de(b), X(b) + 16, y + 8, 24, { f: F.m, a: kb }); });
  const af = seg(t, d * .46 + 1.5, d * .46 + 2.2);
  text('11 unabhängige Episoden · eine Episode stellt 243 von 300 Testereignissen', 960, 880, 26, { al: 'center', c: C.ink, a: af });
  text('Hangrutschungen allgemein · lokale AUC · Zusatz durch Wetter +0,05 [−0,00; +0,11]: nicht belegt', 960, 925, 21, { al: 'center', c: C.dim, a: af });
  vignette(.6);
};

function slopeIcon(x, y, w, h, c, a) { g.save(); g.globalAlpha = a; g.fillStyle = c; g.beginPath(); g.moveTo(x - w / 2, y); g.lineTo(x + w / 2, y); g.lineTo(x + w * .14, y - h); g.closePath(); g.fill(); g.restore(); }
S.weather = (t, d) => {
  bg(); chapter('04', 'WETTER', t, d);
  const sw = d * .43, a1 = inout(t, .2, .8, sw - .5, sw);
  if (a1 > 0) {
    const r = rng(9); for (let i = 0; i < 280; i++) { const x = 240 + r() * 1440, sp = 700 + r() * 500, y = 230 + ((r() * 420 + t * sp) % 420); line(x, y, x - 4, y + 22, C.cold, 1.2, a1 * .4); }
    for (let i = 0; i < 6; i++) { const x = 400 + i * 224; slopeIcon(x, 770, 200, 110, i === 0 ? C.sig : '#DDE6EC', a1); }
    text('GLEICHER TAG, FAST DASSELBE WETTER', 960, 860, 32, { f: F.t, al: 'center', sp: 3, a: a1 * seg(t, 1, 1.8) });
    text('Zusatznutzen des Wetters: nicht belegt', 960, 910, 25, { al: 'center', c: C.dim, a: a1 * seg(t, 1.8, 2.5) });
  }
  const a2 = seg(t, sw + .1, sw + .7) * (1 - seg(t, d - .4, d - .1));
  if (a2 > 0) {
    text('DERSELBE ORT, VERSCHIEDENE ZEITEN', 960, 228, 32, { f: F.t, al: 'center', sp: 3, a: a2 });
    const G = (x0, n, lab, big) => { for (let i = 0; i < 100; i++) { const c = i % 10, ro = i / 10 | 0, x = x0 + c * 46, y = 300 + ro * 46, on = i < n && t > sw + 1 + i * .035; g.save(); g.globalAlpha = a2 * (on ? 1 : .18); g.fillStyle = on ? (big ? C.cold : '#DDE6EC') : '#40505E'; if (on && big) { g.shadowColor = C.cold; g.shadowBlur = 16; } g.fillRect(x, y, 34, 34); g.restore(); } text(lab[0], x0 + 207, 830, 74, { f: F.m, al: 'center', c: big ? C.cold : C.ink, a: a2 * seg(t, sw + 1.4, sw + 2) }); text(lab[1], x0 + 207, 872, 23, { al: 'center', c: C.dim, a: a2 * seg(t, sw + 1.4, sw + 2) }); };
    G(320, 5, ['5 %', 'erwartet'], false); G(1160, 25, ['24,6 %', 'vor dokumentierten Episoden'], true);
    text('Extrem nasse 3 Tage · 35 Episoden · Intervall [11,8; 38,2] · explorativ, vorab festgelegter Haupttest knapp nicht erfüllt, Meldebias möglich', 960, 960, 21, { al: 'center', c: C.dim, a: a2 * seg(t, sw + 2, sw + 2.8) });
  }
  vignette(.5);
};

S.bias = (t, d) => {
  bg(); chapter('05', 'MELDEBIAS', t, d);
  const H = DATA.roads_half_m, sc = 960 / (2 * H), M = (x, y) => [1370 + (x) * sc * .98, 560 - y * sc * .98], draw = seg(t, .5, d * .42), ev = DATA.stanz_events;
  g.save(); g.beginPath(); g.rect(860, 100, 1020, 900); g.clip(); g.strokeStyle = 'rgba(255,200,130,.85)'; g.lineWidth = 1.7; const nR = DATA.roads.length;
  for (let i = 0; i < nR * draw; i++) { const L = DATA.roads[i]; g.beginPath(); for (let j = 0; j < L.length; j += 2) { const p = M(L[j], L[j + 1]); j ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]); } g.stroke(); }
  const ak = seg(t, d * .2, d * .4); for (let i = 0; i < ev.length / 2; i++) { const p = M(ev[2 * i], ev[2 * i + 1]); dot(p[0], p[1], 4.6, C.sig, ak, 12); }
  g.restore();
  const a1 = inout(t, d * .14, d * .14 + .6, d * .58, d * .58 + .5);
  text('0,93', 120, 520, 210, { f: F.m, a: a1, glow: 30, glowc: 'rgba(255,190,110,.5)' });
  text('nur Abstand zu Straßen und Gebäuden', 120, 610, 30, { a: a1 });
  text('GEMELDET WIRD, WAS MENSCHEN SEHEN.', 120, 680, 30, { f: F.t, c: C.sig, sp: 1.5, a: a1 * seg(t, d * .28, d * .34) });
  text('Design mit ungematchten Vergleichspunkten · explorativ', 120, 726, 21, { c: C.dim, a: a1 });
  const a2 = seg(t, d * .6, d * .6 + .6) * (1 - seg(t, d - .4, d - .1));
  text('0,78', 120, 520, 210, { f: F.m, c: C.sig, a: a2, glow: 34 });
  text('Gelände, nur Hänge ähnlich nah an Infrastruktur', 120, 610, 28, { a: a2 });
  text('[0,68; 0,89] · 173 Gruppen, 10 Einheiten · explorativ', 120, 654, 21, { f: F.m, c: C.dim, a: a2 });
  text('EIN TEIL DES SIGNALS BLEIBT MELDEVERHALTEN.', 120, 722, 27, { f: F.t, sp: 1, a: a2 * seg(t, d * .8, d * .86) });
  foot('Echte Straßen (OpenStreetMap, heutiger Stand) und Ereignisse (V0.4) um Stanz im Mürztal', seg(t, 1, 2) * (1 - seg(t, d - .5, d - .1)));
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
  const P = drawRidges(cam, { reveal: seg(t, 0, 2.2) * 1.1 });
  const p = P(.1, -.55, zAt(.1, -.55, .5)), a = seg(t, 1.4, 2);
  ringc(p[0], p[1], 16 + 80 * ((t * .35) % 1), C.sig, 2, a * (1 - ((t * .35) % 1))); dot(p[0], p[1], 8, C.sig, a, 30);
  g.fillStyle = `rgba(5,8,13,${.55 * seg(t, 1.5, 2.5)})`; g.fillRect(0, 0, 1920, 1080);
  const ta = seg(t, 1.8, 2.8);
  text('TALWACHT', 960, 500, 168, { f: F.t, al: 'center', sp: 26, a: ta, glow: 40, glowc: 'rgba(120,190,240,.45)', w: 600 });
  text('WO ZUERST HINSCHAUEN, WENN DER STARKREGEN KOMMT', 960, 572, 25, { f: F.m, al: 'center', c: C.sig, sp: 5, a: ta * seg(t, 2.4, 3.2) });
  const af = seg(t, 3.2, 4);
  text('Daten: GeoSphere Austria (Inventar, INCA, SPARTACUS, SNOWGRID) · Skadi/SRTM · CORINE · OpenStreetMap · Klima: GeoSphere 2025; Kaitna et al. 2025', 960, 950, 19, { al: 'center', c: C.dim, a: af });
  text('Forschungsprototyp, kein Warnsystem · Filmaufnahmen: KI-generierte Illustrationen', 960, 984, 19, { al: 'center', c: C.dim, a: af });
  vignette(.7);
};

window.drawScene = (name, t, d) => { g.setTransform(cv.width / 1920, 0, 0, cv.width / 1920, 0, 0); g.globalAlpha = 1; g.filter = 'none'; S[name](t, d); };
window.sceneNames = Object.keys(S);
