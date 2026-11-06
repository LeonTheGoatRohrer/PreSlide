// Render motion-graphics scenes frame by frame (Canvas 2D in headless Chromium, deterministic, resolution independent).
// Usage: node scripts/finale_video/render_mg.mjs <width> scene:duration[,scene:duration...] [--still=t]
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const out = path.join(root, 'deliverables/finale_video');
const require = createRequire(path.join(out, 'tools/package.json'));
const { chromium } = require('playwright-core');
const CHROME = `${process.env.LOCALAPPDATA}/ms-playwright/chromium-1243/chrome-win64/chrome.exe`;

const width = Number(process.argv[2]);
const height = Math.round(width * 9 / 16);
const scenes = process.argv[3].split(',').map((s) => s.split(':')).map(([n, d]) => [n, Number(d)]);
const stillArg = process.argv.find((a) => a.startsWith('--still='));
const still = stillArg ? Number(stillArg.slice(8)) : null;
const FPS = 25;

const freeze = path.join(out, 'mg/freeze.png');
const freeze2 = path.join(out, 'mg/freeze2.png');
const html = `<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#000}canvas{display:block}</style>
<canvas id="c" width="${width}" height="${height}"></canvas>
${fs.existsSync(freeze) ? `<script>const FREEZE=new Image();FREEZE.src=${JSON.stringify(pathToFileURL(freeze).href)};</script>` : ''}
${fs.existsSync(freeze2) ? `<script>const FREEZE2=new Image();FREEZE2.src=${JSON.stringify(pathToFileURL(freeze2).href)};</script>` : ''}
<script src="${pathToFileURL(path.join(out, 'mg/data.js')).href}"></script>
<script src="${pathToFileURL(path.join(here, 'mg/scenes.js')).href}"></script>`;
const page_file = path.join(out, 'mg/index.html');
fs.writeFileSync(page_file, html);

const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width, height } });
page.on('pageerror', (e) => { console.error('PAGE ERROR', e.message); process.exit(1); });
await page.goto(pathToFileURL(page_file).href);
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(400);

fs.mkdirSync(path.join(out, 'mgclips'), { recursive: true });
for (const [name, dur] of scenes) {
  if (still !== null) {
    await page.evaluate(([n, t, d]) => window.drawScene(n, t, d), [name, still, dur]);
    await page.screenshot({ path: path.join(out, 'mgclips', `${name}_${still}.png`) });
    continue;
  }
  const file = path.join(out, 'mgclips', `${name}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', file], { stdio: ['pipe', 'inherit', 'inherit'] });
  const frames = Math.round(dur * FPS);
  for (let i = 0; i < frames; i++) {
    await page.evaluate(([n, t, d]) => window.drawScene(n, t, d), [name, i / FPS, dur]);
    const jpg = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(jpg)) await new Promise((r) => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  console.log('rendered', name, dur);
}
await browser.close();
