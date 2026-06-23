// Genera los iconos PNG de la PWA (pesa + figura corriendo) a partir de un SVG.
// Uso: node scripts/gen-icons.mjs   (requiere la devDependency 'sharp')
import sharp from "sharp";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, "..", "public", "icons");
mkdirSync(outDir, { recursive: true });

const runnerAndBell = `
  <g fill="none" stroke="#d8472b" stroke-width="26" stroke-linecap="round" stroke-linejoin="round">
    <path d="M292 196 L244 300"/>
    <path d="M286 224 L348 206"/>
    <path d="M286 224 L228 250"/>
    <path d="M244 300 L300 330 L304 384"/>
    <path d="M244 300 L200 340 L160 330"/>
  </g>
  <circle cx="300" cy="156" r="32" fill="#d8472b"/>
  <g fill="#eef2f4">
    <rect x="176" y="410" width="160" height="20" rx="10"/>
    <rect x="156" y="394" width="22" height="52" rx="7"/>
    <rect x="334" y="394" width="22" height="52" rx="7"/>
    <rect x="134" y="404" width="18" height="32" rx="6"/>
    <rect x="360" y="404" width="18" height="32" rx="6"/>
  </g>`;

// rx grande = esquinas redondeadas (iconos "any"); rx=0 + escala = maskable con safe-zone.
function svg({ rx = 112, scale = 1 } = {}) {
  const content =
    scale === 1
      ? runnerAndBell
      : `<g transform="translate(256,256) scale(${scale}) translate(-256,-256)">${runnerAndBell}</g>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <rect width="512" height="512" rx="${rx}" fill="#14181c"/>${content}</svg>`;
}

const targets = [
  { name: "icon-192.png", size: 192, opts: { rx: 96 } },
  { name: "icon-512.png", size: 512, opts: { rx: 112 } },
  { name: "maskable-512.png", size: 512, opts: { rx: 0, scale: 0.72 } },
  { name: "apple-touch-icon.png", size: 180, opts: { rx: 0 } }, // iOS aplica su propia máscara
  { name: "favicon-32.png", size: 32, opts: { rx: 6 } },
];

for (const t of targets) {
  await sharp(Buffer.from(svg(t.opts)))
    .resize(t.size, t.size)
    .png()
    .toFile(resolve(outDir, t.name));
  console.log("icono:", t.name, `${t.size}x${t.size}`);
}
console.log("Iconos generados en", outDir);
