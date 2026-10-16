import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { DEMO_LABEL } from '../src/features/public/demo.js';

const original = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8');
const title = 'Synthetic demonstration portfolio | Portfolio research';
const html = original.replace(/<title>.*?<\/title>/s, `<title>${title}</title>`)
  .replace(/<meta name="description" content="[^"]*"\s*\/>/, `<meta name="description" content="${DEMO_LABEL}" />`)
  .replace('</head>', `<meta property="og:title" content="${title}" />\n<meta property="og:description" content="${DEMO_LABEL}" />\n<meta property="og:type" content="website" />\n</head>`);
for (const route of ['demo', 'demo-preview']) {
  const dir = new URL(`../dist/${route}/`, import.meta.url);
  await mkdir(dir, { recursive: true });
  await writeFile(new URL('index.html', dir), html);
}
console.log('Synthetic demonstration static title, description and share metadata generated.');
