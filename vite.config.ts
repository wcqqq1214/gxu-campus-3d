import { campusDracoAssets } from './scripts/vite-draco-assets.mjs';
import tailwindcss from '@tailwindcss/postcss';
import vinext from 'vinext';
import { defineConfig } from 'vite';
export default defineConfig({
  plugins: [
    campusDracoAssets(process.env.NEXT_PUBLIC_BASE_PATH ?? ''),
    vinext(),
  ],
  css: { postcss: { plugins: [tailwindcss()] } },
  server: { host: '127.0.0.1' },
});
