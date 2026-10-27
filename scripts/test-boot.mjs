import test from 'node:test';
import assert from 'node:assert/strict';
import { prefetchBase, modelUrl } from '../lib/campus/boot.ts';
import { createCameraStore } from '../lib/campus/camera-store.ts';

const manifest = {
  base: { url: 'models/base.glb', bytes: 8, sha256: 'abc' },
  trees: { url: 'models/trees.glb', bytes: 1 },
  zones: [],
  landmarks: [],
};

function mockFetch(routes) {
  const requests = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    const href = typeof url === 'string' ? url : url.url;
    requests.push(href);
    init?.signal?.throwIfAborted();
    const route = routes[href];
    if (!route) return new Response('missing', { status: 404 });
    return route();
  };
  return { requests, restore: () => (globalThis.fetch = original) };
}

test('预取先读模型清单，再按场景相同的带指纹地址下载基础模型', async (t) => {
  let release;
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array([1, 2, 3, 4]));
      release = () => {
        controller.enqueue(new Uint8Array([5, 6, 7, 8]));
        controller.close();
      };
    },
  });
  const mock = mockFetch({
    '/data/models.json': () => Response.json(manifest),
    [modelUrl(manifest.base)]: () => new Response(body),
  });
  t.after(mock.restore);
  const boot = prefetchBase(new AbortController().signal);
  assert.deepEqual(await boot.manifest, manifest);
  await new Promise((resolve) => setTimeout(resolve, 10));
  // A scene that subscribes late first receives the latest progress.
  const seen = [];
  const unsubscribe = boot.onProgress((f) => seen.push(f));
  assert.equal(seen.at(-1), 0.5);
  release();
  const bytes = new Uint8Array(await boot.base);
  unsubscribe();
  assert.deepEqual([...bytes], [1, 2, 3, 4, 5, 6, 7, 8]);
  assert.equal(seen.at(-1), 0.98);
  assert.deepEqual(mock.requests, [
    '/data/models.json',
    '/models/base.glb?v=abc',
  ]);
});

test('预取失败在被场景读取前保持静默，读取时得到原错误', async (t) => {
  const mock = mockFetch({});
  t.after(mock.restore);
  const unhandled = [];
  const onUnhandled = (reason) => unhandled.push(reason);
  process.on('unhandledRejection', onUnhandled);
  t.after(() => process.off('unhandledRejection', onUnhandled));
  const boot = prefetchBase(new AbortController().signal);
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.deepEqual(unhandled, []);
  await assert.rejects(boot.manifest, /HTTP 404/);
  await assert.rejects(boot.base, /HTTP 404/);
});

test('取消页面生命周期会中止预取', async (t) => {
  const mock = mockFetch({
    '/data/models.json': () => Response.json(manifest),
  });
  t.after(mock.restore);
  const lifetime = new AbortController();
  lifetime.abort();
  const boot = prefetchBase(lifetime.signal);
  await assert.rejects(boot.base, { name: 'AbortError' });
  assert.deepEqual(mock.requests, []);
});

test('相机快照只通知订阅者，取消订阅后不再通知', () => {
  const store = createCameraStore();
  assert.equal(store.get(), null);
  let calls = 0;
  const unsubscribe = store.subscribe(() => calls++);
  const snapshot = { position: [1, 2, 3], target: [0, 0, 0] };
  store.set(snapshot);
  assert.equal(store.get(), snapshot);
  assert.equal(calls, 1);
  unsubscribe();
  store.set({ ...snapshot });
  assert.equal(calls, 1);
});
