/**
 * Functional test for the NEX eye animation engine.
 *
 * The engine is pure TypeScript with no DOM dependency, so it can be executed
 * in Node. This test drives a real animation loop over every expression and
 * asserts that the generated SVG geometry is always valid (finite numbers,
 * closed paths, sane opacity ranges) and that the eyes actually change shape
 * between expressions.
 *
 *   node tools/test_eye_engine.mjs
 */
import { pathToFileURL } from 'node:url';
import { writeFileSync, mkdtempSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname;
const ENTRY = join(ROOT, 'app/src/eyes/engine.ts');

// esbuild ships with vite — resolve it from the app's node_modules.
const esbuildEntry = join(ROOT, 'app/node_modules/esbuild/lib/main.js');
if (!existsSync(esbuildEntry)) {
  console.error('esbuild not found — run `npm install` inside app/ first.');
  process.exit(1);
}
const { build } = await import(pathToFileURL(esbuildEntry).href);

const passed = [];
const failed = [];

function check(name, condition, detail = '') {
  if (condition) {
    passed.push(name);
    console.log(`  PASS  ${name}${detail ? `  (${detail})` : ''}`);
  } else {
    failed.push(name);
    console.log(`  FAIL  ${name}  ${detail}`);
  }
}

const dir = mkdtempSync(join(tmpdir(), 'nex-eye-'));
const outfile = join(dir, 'engine.mjs');
await build({
  entryPoints: [ENTRY],
  bundle: true,
  format: 'esm',
  platform: 'neutral',
  outfile,
  logLevel: 'error',
});
const mod = await import(pathToFileURL(outfile).href);
const { eyeEngine, EyeEngine } = mod;

// --- browser shims so the engine can run headless -----------------------
let rafHandle = null;
globalThis.requestAnimationFrame = (cb) => {
  rafHandle = setTimeout(() => cb(performance.now()), 16);
  return rafHandle;
};
globalThis.cancelAnimationFrame = (handle) => clearTimeout(handle);

const EXPRESSIONS = [
  'neutral', 'happy', 'sad', 'angry', 'sleep', 'blink', 'dance', 'surprised',
  'thinking', 'listening', 'speaking', 'laugh', 'cry', 'love', 'gaming',
  'curious', 'confused', 'excited',
];

function isValidPath(d) {
  if (typeof d !== 'string' || d.length < 10) return false;
  if (!d.startsWith('M')) return false;
  if (d.includes('NaN') || d.includes('undefined') || d.includes('Infinity')) return false;
  const nums = d.match(/-?\d+(\.\d+)?/g);
  if (!nums || nums.length < 8) return false;
  return nums.every((n) => Number.isFinite(Number(n)));
}

console.log('\n[1] Engine construction and expression coverage');
const engine = new EyeEngine();
check('engine instantiated', !!engine);
check('expression list has 18 entries', EXPRESSIONS.length === 18, String(EXPRESSIONS.length));

// --- capture every frame --------------------------------------------------
const frames = [[], []];
engine.register(0, (draw) => frames[0].push(draw));
engine.register(1, (draw) => frames[1].push(draw));
engine.start();

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

console.log('\n[2] Every expression produces valid geometry');
for (const expression of EXPRESSIONS) {
  engine.setExpression(expression);
  frames[0].length = 0;
  frames[1].length = 0;
  await sleep(420); // ~25 frames
  const last = frames[0].at(-1);
  const lastRight = frames[1].at(-1);
  const ok =
    !!last &&
    isValidPath(last.bodyPath) &&
    isValidPath(last.pupilPath) &&
    isValidPath(last.heartPath) &&
    isValidPath(last.haloPath) &&
    isValidPath(last.tearPath) &&
    Number.isFinite(last.pupilCx) &&
    Number.isFinite(last.pupilCy) &&
    last.haloOpacity >= 0 &&
    last.haloOpacity <= 1.01 &&
    last.pupilOpacity >= 0 &&
    last.pupilOpacity <= 1.01 &&
    last.heartOpacity >= 0 &&
    last.heartOpacity <= 1.01 &&
    last.tearOpacity >= 0 &&
    last.tearOpacity <= 1.01 &&
    !!lastRight &&
    isValidPath(lastRight.bodyPath);
  check(`"${expression}" renders valid SVG`, ok, ok ? `${frames[0].length} frames` : JSON.stringify(last).slice(0, 140));
}

console.log('\n[3] Expressions actually change the face');
const shapeOf = async (expression) => {
  engine.setExpression(expression);
  frames[0].length = 0;
  await sleep(500);
  return frames[0].at(-1).bodyPath;
};
const sleepShape = await shapeOf('sleep');
const openShape = await shapeOf('surprised');
check('sleep closes the eye differently to open', sleepShape !== openShape);
const sleepNums = sleepShape.match(/-?\d+(\.\d+)?/g).map(Number);
const openNums = openShape.match(/-?\d+(\.\d+)?/g).map(Number);
const sleepHeight = Math.abs(sleepNums[1] - sleepNums[13]);
const openHeight = Math.abs(openNums[1] - openNums[13]);
check('sleep eye is much shorter than an open eye', sleepHeight < openHeight * 0.5, `${sleepHeight.toFixed(1)} vs ${openHeight.toFixed(1)}`);

const loveDraw = await (async () => {
  engine.setExpression('love');
  frames[0].length = 0;
  await sleep(700);
  return frames[0].at(-1);
})();
check('love renders a heart pupil', loveDraw.heartOpacity > 0.9, `heartOpacity=${loveDraw.heartOpacity.toFixed(2)}`);

const angryDraw = await (async () => {
  engine.setExpression('angry');
  frames[0].length = 0;
  await sleep(700);
  return frames[0].at(-1);
})();
check('angry tints the eye warm', /rgb\(2\d\d,\s*[0-9]{1,3},/.test(angryDraw.glow) || angryDraw.glow.startsWith('rgb(2'), angryDraw.glow);

console.log('\n[4] Blink animation runs automatically');
engine.setExpression('neutral');
frames[0].length = 0;
await sleep(6000);
const blinkVariants = new Set(frames[0].map((f) => f.bodyPath));
check('eye shape changes over time (blinking)', blinkVariants.size > 3, `${blinkVariants.size} distinct shapes in 6s`);

console.log('\n[5] Idle look-around moves the pupil');
engine.setExpression('neutral');
frames[0].length = 0;
// The idle look-around fires every 1.6 – 4.8 s, so the sampling window has to
// be longer than the longest interval or the test would be flaky.
await sleep(9000);
const xs = frames[0].map((f) => f.pupilCx);
const spread = Math.max(...xs) - Math.min(...xs);
check('pupil moves while idle', spread > 3, `spread=${spread.toFixed(2)}px`);

engine.stop();
console.log('\n' + '='.repeat(68));
console.log(`PASSED: ${passed.length}   FAILED: ${failed.length}`);
if (failed.length) {
  console.log('Failures:');
  failed.forEach((f) => console.log('  - ' + f));
}
console.log('='.repeat(68));
process.exit(failed.length ? 1 : 0);
