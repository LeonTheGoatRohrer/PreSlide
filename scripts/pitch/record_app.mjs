// Record the Talwacht web app (Hang-Check) for the pitch film, 1920x1080.
// Usage: node scripts/pitch/record_app.mjs <base-url> <out-dir>
// Needs playwright-core (PW_CORE = path to its package dir) and a Chromium build (PW_CHROME = chrome.exe).
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_CORE);
const base = process.argv[2] || 'http://localhost:8012';
const outDir = path.resolve(process.argv[3] || 'deliverables/pitch/app');
const only = (process.argv[4] || '').split(',').filter(Boolean);
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({
  executablePath: process.env.PW_CHROME,
  headless: true,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function smoothScroll(page, totalPx, ms) {
  const steps = Math.round(ms / 40);
  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, totalPx / steps);
    await sleep(40);
  }
}

async function drag(page, x0, y0, dx, dy, ms, button = 'left', modifiers = []) {
  for (const m of modifiers) await page.keyboard.down(m);
  await page.mouse.move(x0, y0);
  await page.mouse.down({ button });
  const steps = Math.round(ms / 30);
  for (let i = 1; i <= steps; i++) {
    await page.mouse.move(x0 + (dx * i) / steps, y0 + (dy * i) / steps);
    await sleep(30);
  }
  await page.mouse.up({ button });
  for (const m of modifiers) await page.keyboard.up(m);
}

async function take(name, fn) {
  if (only.length && !only.includes(name)) return;
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: { dir: outDir, size: { width: 1920, height: 1080 } },
    locale: 'de-AT',
  });
  const page = await context.newPage();
  try {
    await fn(page);
  } finally {
    const video = page.video();
    await context.close();
    const src = await video.path();
    fs.renameSync(src, path.join(outDir, `${name}.webm`));
    console.log('recorded', name);
  }
}

await take('app_01_start', async (page) => {
  await page.goto(base + '/#/', { waitUntil: 'networkidle' });
  await sleep(3500);
  await smoothScroll(page, 2600, 14000);
  await sleep(1500);
});

await take('app_02_hangcheck_gastein', async (page) => {
  await page.goto(base + '/#/check?r=2000', { waitUntil: 'networkidle' });
  await sleep(2500);
  await page.getByRole('button', { name: 'Gasteiner Tal (Salzburg)' }).click();
  await sleep(9000);
  // slow 3D move: rotate and tilt the map (MapLibre: right-drag)
  await drag(page, 1300, 600, 260, -90, 6000, 'right');
  await sleep(2500);
  await drag(page, 1300, 600, -180, 0, 5000, 'right');
  await sleep(3000);
});

await take('app_03_fliessweg', async (page) => {
  await page.goto(base + '/#/check?lon=13.11000&lat=47.11000&ort=Gasteiner+Tal+%28Salzburg%29&r=2000', { waitUntil: 'networkidle' });
  await sleep(8000);
  const btn = page.getByRole('button', { name: /Wohin fließt es/ }).first();
  await btn.scrollIntoViewIfNeeded();
  await sleep(1000);
  await btn.click();
  await page.waitForTimeout(12000);
  await smoothScroll(page, 0, 100);
  await sleep(3000);
});

await take('app_04_starkregen', async (page) => {
  await page.goto(base + '/#/check?lon=13.11000&lat=47.11000&ort=Gasteiner+Tal+%28Salzburg%29&r=2000', { waitUntil: 'networkidle' });
  await sleep(8000);
  const sw = page.getByRole('switch').first();
  if (await sw.count()) {
    await sw.click();
  } else {
    await page.getByText(/Starkregen oder Unwetter erwartet/).first().click();
  }
  await sleep(14000);
  await drag(page, 1300, 600, 200, -60, 6000, 'right');
  await sleep(2500);
});

await take('app_05_belastbar', async (page) => {
  await page.goto(base + '/#/belastbar', { waitUntil: 'networkidle' });
  await sleep(3000);
  await smoothScroll(page, 2200, 14000);
  await sleep(1500);
});

await browser.close();
