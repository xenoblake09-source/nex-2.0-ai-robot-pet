/**
 * Renders NEX's face straight from the animation engine.
 *
 * The script runs the real eye engine, captures the SVG geometry it produces
 * and writes standalone SVG files — so what you see is exactly what the app
 * draws on the device.
 *
 *   node tools/render_face.mjs
 *
 * Output:
 *   docs/nex-face.svg          the main face (two eyes)
 *   docs/nex-expressions.svg   a grid of every expression
 */
import { pathToFileURL } from 'node:url';
import { mkdtempSync, existsSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname;
const esbuildEntry = join(ROOT, 'app/node_modules/esbuild/lib/main.js');
if (!existsSync(esbuildEntry)) {
  console.error('esbuild not found — run `npm install` inside app/ first.');
  process.exit(1);
}
const { build } = await import(pathToFileURL(esbuildEntry).href);

const dir = mkdtempSync(join(tmpdir(), 'nex-face-'));
const outfile = join(dir, 'engine.mjs');
await build({
  entryPoints: [join(ROOT, 'app/src/eyes/engine.ts')],
  bundle: true,
  format: 'esm',
  platform: 'neutral',
  outfile,
  logLevel: 'error',
});
const { EyeEngine } = await import(pathToFileURL(outfile).href);

globalThis.requestAnimationFrame = (cb) => setTimeout(() => cb(performance.now()), 16);
globalThis.cancelAnimationFrame = (handle) => clearTimeout(handle);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Renders a single eye using the exact markup of the React component.
 *
 * `flat` drops the SVG gradients. Browsers render them perfectly, but some
 * rasterisers (ImageMagick's built-in MSVG) paint unresolved gradients as
 * opaque black — the flat variant is used for the PNG previews so they show
 * the real colours.
 */
function eyeSvg(draw, id, x, y, size = 240, flat = false) {
  const transform = `translate(${draw.translateX.toFixed(2)} ${draw.translateY.toFixed(2)}) ` +
    `rotate(${draw.rotate.toFixed(2)} 120 120) ` +
    `translate(120 120) scale(${draw.scale.toFixed(3)}) translate(-120 -120)`;

  const halo = flat
    ? `<path d="${draw.haloPath}" fill="none" stroke="${draw.glow}"
         stroke-opacity="${(draw.haloOpacity * 0.5).toFixed(3)}" stroke-width="9"
         transform="translate(120 120) scale(1.14) translate(-120 -120)"/>`
    : `<path d="${draw.haloPath}" fill="url(#halo-${id})" opacity="${draw.haloOpacity.toFixed(3)}"
         transform="translate(120 120) scale(1.22) translate(-120 -120)" filter="url(#blur-${id})"/>`;

  const shade = flat
    ? ''
    : `<path d="${draw.bodyPath}" fill="url(#shade-${id})"/>`;

  return `
  <g transform="translate(${x} ${y})">
    <defs>
      <radialGradient id="halo-${id}" cx="50%" cy="50%" r="50%">
        <stop offset="45%" stop-color="${draw.glow}" stop-opacity="0.5"/>
        <stop offset="100%" stop-color="${draw.glow}" stop-opacity="0"/>
      </radialGradient>
      <linearGradient id="shade-${id}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#ffffff" stop-opacity="0.18"/>
        <stop offset="45%" stop-color="#ffffff" stop-opacity="0"/>
        <stop offset="100%" stop-color="#0b1b2a" stop-opacity="0.22"/>
      </linearGradient>
      <clipPath id="clip-${id}">
        <path d="${draw.bodyPath}"/>
      </clipPath>
    </defs>
    <g transform="${transform}">
      ${halo}
      <path d="${draw.bodyPath}" fill="${draw.tint}" stroke="${draw.glow}"
            stroke-opacity="${draw.strokeOpacity.toFixed(3)}" stroke-width="2.2" stroke-linejoin="round"/>
      ${shade}
      <g clip-path="url(#clip-${id})">
        <path d="${draw.pupilPath}" fill="${draw.pupilColor}" opacity="${draw.pupilOpacity.toFixed(3)}"/>
        <path d="${draw.heartPath}" fill="#FF2E74" opacity="${draw.heartOpacity.toFixed(3)}"/>
        <circle cx="${(draw.pupilCx - draw.pupilRadius * 0.34).toFixed(2)}" cy="${(draw.pupilCy - draw.pupilRadius * 0.38).toFixed(2)}"
                r="${(draw.pupilRadius * 0.22).toFixed(2)}" fill="#ffffff" opacity="${draw.highlightOpacity.toFixed(3)}"/>
        <circle cx="${(draw.pupilCx + draw.pupilRadius * 0.34).toFixed(2)}" cy="${(draw.pupilCy + draw.pupilRadius * 0.38).toFixed(2)}"
                r="${(draw.pupilRadius * 0.12).toFixed(2)}" fill="#ffffff" opacity="${(draw.highlightOpacity * 0.7).toFixed(3)}"/>
        <path d="${draw.tearPath}" fill="#7FD8FF" opacity="${draw.tearOpacity.toFixed(3)}"/>
      </g>
    </g>
  </g>`;
}

async function capture(expression, settleMs = 900) {
  const engine = new EyeEngine();
  let left = null;
  let right = null;
  engine.register(0, (d) => (left = d));
  engine.register(1, (d) => (right = d));
  engine.start();
  engine.setExpression(expression);
  await sleep(settleMs);
  engine.stop();
  return { left, right };
}

const expressions = [
  'neutral', 'happy', 'sad', 'angry', 'sleep', 'blink',
  'dance', 'surprised', 'thinking', 'listening', 'speaking', 'laugh',
  'cry', 'love', 'gaming', 'curious', 'confused', 'excited',
];

mkdirSync(join(ROOT, 'docs'), { recursive: true });

// ---------------------------------------------------------------- main face
{
  const { left, right } = await capture('listening', 1200);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="360" viewBox="0 0 720 360">
  <defs><filter id="blur-main" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="7"/></filter></defs>
  <rect width="720" height="360" fill="#000000"/>
  ${eyeSvg(left, 'l', 30, 60)}
  ${eyeSvg(right, 'r', 450, 60)}
</svg>`;
  writeFileSync(join(ROOT, 'docs/nex-face.svg'), svg);
  console.log('wrote docs/nex-face.svg');

  const flatSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="360" viewBox="0 0 720 360">
  <rect width="720" height="360" fill="#000000"/>
  ${eyeSvg(left, 'l', 30, 60, 240, true)}
  ${eyeSvg(right, 'r', 450, 60, 240, true)}
</svg>`;
  writeFileSync(join(ROOT, 'docs/nex-face-flat.svg'), flatSvg);
  console.log('wrote docs/nex-face-flat.svg (rasteriser friendly)');
}

// -------------------------------------------------------- expression grid
{
  const cols = 6;
  // 320 px per cell: the eye body is 240 units and the glow halo expands it
  // by ~22 %, so 320 keeps every cell free of overlap.
  const cell = 320;
  const rows = Math.ceil(expressions.length / cols);
  const parts = [];
  const flatParts = [];
  let index = 0;
  for (const expression of expressions) {
    const { left } = await capture(expression, 700);
    const col = index % cols;
    const row = Math.floor(index / cols);
    const x = col * cell + 6;
    const y = row * cell + 6;
    parts.push(eyeSvg(left, `g${index}`, x, y));
    flatParts.push(eyeSvg(left, `g${index}`, x, y, 240, true));
    index += 1;
  }
  const header = `<defs><filter id="blur-g0" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="5"/></filter></defs>`;
  writeFileSync(
    join(ROOT, 'docs/nex-expressions.svg'),
    `<svg xmlns="http://www.w3.org/2000/svg" width="${cols * cell}" height="${rows * cell}"
  viewBox="0 0 ${cols * cell} ${rows * cell}">
  ${header}
  <rect width="100%" height="100%" fill="#000000"/>
  ${parts.join('\n')}
</svg>`,
  );
  writeFileSync(
    join(ROOT, 'docs/nex-expressions-flat.svg'),
    `<svg xmlns="http://www.w3.org/2000/svg" width="${cols * cell}" height="${rows * cell}"
  viewBox="0 0 ${cols * cell} ${rows * cell}">
  <rect width="100%" height="100%" fill="#000000"/>
  ${flatParts.join('\n')}
</svg>`,
  );
  console.log(`wrote docs/nex-expressions.svg (${expressions.length} expressions)`);
}
