import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  ResourceQueue,
  withRetry,
  HttpError,
  nearbyChunks,
  planDetails,
  fetchJson,
} from '../lib/campus/streaming.ts';
const tick = () => new Promise((resolve) => setImmediate(resolve));
test('加载并发最多两项，等待的精选地标优先于背景区块', async () => {
  const queue = new ResourceQueue(2);
  const started = [];
  const resolvers = {};
  const work = (key) => async () => {
    started.push(key);
    await new Promise((resolve) => (resolvers[key] = resolve));
  };
  const promises = [
    queue.enqueue('a', 2, work('a')),
    queue.enqueue('b', 2, work('b')),
    queue.enqueue('c', 2, work('c')),
    queue.enqueue('library', 0, work('library')),
  ];
  await tick();
  assert.deepEqual(started, ['a', 'b']);
  resolvers.a();
  await tick();
  assert.deepEqual(started, ['a', 'b', 'library']);
  resolvers.b();
  resolvers.library();
  await tick();
  resolvers.c();
  await Promise.all(promises);
  await tick();
  assert.equal(queue.tasks.size, 0);
});
test('离开区块会取消排队和传输中的资源，后续任务仍可运行', async () => {
  const queue = new ResourceQueue(1);
  const started = [];
  const first = queue.enqueue('a', 1, async (signal) => {
    started.push('a');
    await new Promise((_, reject) =>
      signal.addEventListener(
        'abort',
        () => reject(new DOMException('cancel', 'AbortError')),
        { once: true },
      ),
    );
  });
  const second = queue.enqueue('b', 2, async () => {
    started.push('b');
  });
  const checked = Promise.all([
    assert.rejects(first, { name: 'AbortError' }),
    assert.rejects(second, { name: 'AbortError' }),
  ]);
  await tick();
  queue.cancel('b');
  queue.cancel('a');
  await checked;
  await tick();
  await queue.enqueue('c', 0, async () => {
    started.push('c');
  });
  assert.deepEqual(started, ['a', 'c']);
});
test('503 自动重试能恢复；持续失败最多三次；404 不自动重试', async () => {
  const signal = new AbortController().signal;
  let count = 0;
  assert.equal(
    await withRetry(
      async () => {
        if (++count === 1) throw new HttpError(503);
        return 'ok';
      },
      signal,
      [0, 0],
    ),
    'ok',
  );
  assert.equal(count, 2);
  count = 0;
  await assert.rejects(
    withRetry(
      async () => {
        count++;
        throw new HttpError(503);
      },
      signal,
      [0, 0],
    ),
  );
  assert.equal(count, 3);
  count = 0;
  await assert.rejects(
    withRetry(
      async () => {
        count++;
        throw new HttpError(404);
      },
      signal,
      [0, 0],
    ),
  );
  assert.equal(count, 1);
});
test('区块覆盖全部普通校内建筑一次，每块低于 2 MB 且使用相同基础替换节点', async () => {
  const manifest = JSON.parse(
    await readFile(new URL('../public/data/models.json', import.meta.url)),
  );
  const b = await readFile(
    new URL('../public/models/base.glb', import.meta.url),
  );
  const gltf = JSON.parse(b.toString('utf8', 20, 20 + b.readUInt32LE(12)));
  assert.equal(manifest.version, 2);
  assert.ok(manifest.zones.length >= 20);
  for (const a of manifest.zones) {
    assert.ok(a.bytes < 2_000_000, `${a.id}: ${a.bytes}`);
    assert.equal(
      gltf.nodes.filter(
        (n) => n.name === a.id && n.extras?.layer === 'buildings',
      ).length,
      1,
    );
    assert.ok(a.bounds.every(Number.isFinite));
  }
  assert.ok(nearbyChunks(manifest.zones, 179, -485).length > 0);
  assert.equal(nearbyChunks(manifest.zones, 9000, 9000).length, 0);
});

test('地标和三条道路不会挤占附近建筑的三个名额，所有背景资源仍受同一预算限制', async () => {
  const manifest = JSON.parse(
    await readFile(new URL('../public/data/models.json', import.meta.url)),
  );
  const landmarks = JSON.parse(
    await readFile(new URL('../public/data/landmarks.json', import.meta.url)),
  );
  const place = landmarks.find((p) => p.id === 'library');
  const foreground = manifest.landmarks.find((p) => p.id === 'library');
  const roads = nearbyChunks(manifest.infrastructure, ...place.center, 230).map(
    ({ asset }) => asset,
  );
  const buildings = nearbyChunks(manifest.zones, ...place.center).map(
    ({ asset }) => asset,
  );
  assert.ok(roads.length >= 3);
  assert.ok(buildings.length >= 3);
  const mib = 1048576;
  const costs = new Map([...roads, ...buildings].map((a) => [a.id, 2 * mib]));
  costs.set('landmark-library', 18 * mib);
  const options = {
    foreground: ['landmark-library', foreground],
    foregroundReady: true,
    roads,
    buildings,
    costs,
    cap: 64 * mib,
  };
  const plan = planDetails(options);
  assert.equal(
    plan.assets.filter(([key]) => buildings.some((b) => b.id === key)).length,
    3,
  );
  assert.equal(
    plan.assets.filter(([key]) => roads.some((b) => b.id === key)).length,
    3,
  );
  assert.equal(plan.allocation, 30 * mib);
  const constrained = planDetails({ ...options, cap: 26 * mib });
  assert.equal(constrained.allocation, 26 * mib);
  assert.equal(
    constrained.assets.filter(([key]) => buildings.some((b) => b.id === key))
      .length,
    1,
  );
  const pending = planDetails({ ...options, foregroundReady: false });
  assert.equal(
    pending.assets.filter(([key]) => buildings.some((b) => b.id === key))
      .length,
    1,
  );
});

test('JSON请求503自动恢复，超时退出并可重试，生命周期取消停止所有后续请求', async (t) => {
  let calls = 0;
  const fake = t.mock.method(globalThis, 'fetch', async () => {
    calls++;
    return calls === 1
      ? new Response('', { status: 503 })
      : Response.json({ ready: true });
  });
  assert.deepEqual(
    await fetchJson(
      'https://example.com/data.json',
      new AbortController().signal,
      { delays: [0, 0] },
    ),
    { ready: true },
  );
  assert.equal(calls, 2);
  calls = 0;
  fake.mock.mockImplementation(async (_url, { signal }) => {
    calls++;
    return new Promise((_, reject) =>
      signal.addEventListener(
        'abort',
        () => reject(new DOMException('Aborted', 'AbortError')),
        { once: true },
      ),
    );
  });
  await assert.rejects(
    fetchJson('https://example.com/hang.json', new AbortController().signal, {
      timeoutMs: 10,
      delays: [0, 0],
    }),
  );
  assert.equal(calls, 3);
  calls = 0;
  const lifetime = new AbortController();
  const pending = fetchJson(
    'https://example.com/cancel.json',
    lifetime.signal,
    { timeoutMs: 1000, delays: [0, 0] },
  );
  lifetime.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  assert.equal(calls, 1);
  fake.mock.mockImplementation(async () => Response.json({ recovered: true }));
  assert.deepEqual(
    await fetchJson(
      'https://example.com/retry.json',
      new AbortController().signal,
    ),
    { recovered: true },
  );
});
