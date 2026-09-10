import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
const root = path.resolve('out');
const port = Number(process.env.PORT ?? 4300);
const logRequests = process.argv.includes('--log-requests');
const fail = new Set(
  (process.argv.find((a) => a.startsWith('--fail-once='))?.split('=')[1] ?? '')
    .split(',')
    .filter(Boolean),
);
const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.geojson': 'application/geo+json',
  '.wasm': 'application/wasm',
  '.glb': 'model/gltf-binary',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.txt': 'text/plain',
};
http
  .createServer(async (req, res) => {
    try {
      let url = decodeURIComponent(
        new URL(req.url, 'http://localhost').pathname,
      ).replace(/^\/gxu-campus-3d(?=\/|$)/, '');
      if (url.endsWith('/')) url += 'index.html';
      const file = path.resolve(root, '.' + url);
      if (!file.startsWith(root + path.sep)) {
        res.writeHead(403);
        res.end();
        return;
      }
      if (fail.delete(path.basename(file))) {
        if (logRequests)
          console.log(JSON.stringify({ path: url, status: 503 }));
        res.writeHead(503, { 'Cache-Control': 'no-store' });
        res.end('Intentional one-time asset failure for local QA');
        return;
      }
      const data = await readFile(file);
      if (logRequests)
        console.log(
          JSON.stringify({ path: url, status: 200, bytes: data.byteLength }),
        );
      res.writeHead(200, {
        'Content-Type': types[path.extname(file)] ?? 'application/octet-stream',
        'Cache-Control': 'no-cache',
      });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end('Not found');
    }
  })
  .listen(port, '127.0.0.1', () =>
    console.log(`Local: http://127.0.0.1:${port}/gxu-campus-3d/`),
  );
