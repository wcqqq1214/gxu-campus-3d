import { createServer } from 'vite';
// Independent HTML fixtures import production modules without starting vinext.
const server = await createServer({
  configFile: false,
  server: {
    host: '127.0.0.1',
    port: Number(process.env.PORT ?? 4313),
    strictPort: true,
  },
});
await server.listen();
server.printUrls();
console.log('Open /scripts/fixtures/postprocessing.html');
