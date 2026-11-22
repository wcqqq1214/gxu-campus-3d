import { fileURLToPath } from 'node:url';
import { campusDracoAssets } from './scripts/vite-draco-assets.mjs';
import tailwindcss from '@tailwindcss/postcss';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
// build-pages.mjs resolves the Pages prefix; the dev server serves from the root.
const basePath = process.env.CAMPUS_BASE_PATH ?? '';
export default defineConfig({
  base: `${basePath}/`,
  plugins: [campusDracoAssets(basePath), react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./', import.meta.url)) } },
  css: { postcss: { plugins: [tailwindcss()] } },
  server: { host: '127.0.0.1', port: 3000 },
  build: { outDir: 'out', emptyOutDir: true },
});
