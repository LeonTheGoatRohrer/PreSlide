// Record the Talwacht Hang-Check (Gasteiner Tal) in phone format for the V5 finale montage, 390x844 at 3x.
// Copied from video-pitch-script/scripts/pitch/record_app.mjs, only the Gastein scene, mobile viewport.
// Usage: node scripts/finale_video/record_app_mobile.mjs <base-url> <out-dir>
// Needs playwright-core (PW_CORE = path to its package dir) and a Chromium build (PW_CHROME = chrome.exe).
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_CORE);
const base = process.argv[2] || 'http://localhost:8012';
const outDir = path.resolve(process.argv[3] || 'deliverables/finale_video/app_mobile');
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({
  executablePath: process.env.PW_CHROME,
  headless: true,
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'],
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const W = 390, H = 844, SCALE = 3;

const context = await browser.newContext({
  viewport: { width: W, height: H },
  deviceScaleFactor: SCALE,
  isMobile: true,
  hasTouch: true,
  recordVideo: { dir: outDir, size: { width: W, height: H } },  // larger sizes only pad the page into the top-left corner
  locale: 'de-AT',
});
const page = await context.newPage();
const t0 = Date.now();
await page.goto(base + '/#/check?lon=13.11000&lat=47.11000&ort=Gasteiner+Tal+%28Salzburg%29&r=2000', { waitUntil: 'networkidle' });
await page.getByText(/Prüfpunkt 1/).first().waitFor({ timeout: 180000 });
const ready = (Date.now() - t0) / 1000;
await sleep(1500);
await page.screenshot({ path: path.join(outDir, 'ready.png') });
// zoom toward the review points: pinch is not available headless, so use the map's own + control or the wheel
await page.mouse.move(W / 2, H * 0.3);
for (let i = 0; i < 12; i++) {
  await page.mouse.wheel(0, -40);
  await sleep(120);
}
await sleep(4000);
await page.screenshot({ path: path.join(outDir, 'zoomed.png') });
const video = page.video();
await context.close();
fs.renameSync(await video.path(), path.join(outDir, 'app_02_hangcheck_gastein_mobile.webm'));
fs.writeFileSync(path.join(outDir, 'marks.json'), JSON.stringify({ ready_s: ready }, null, 1));
console.log('recorded, ready at', ready, 's');
await browser.close();
