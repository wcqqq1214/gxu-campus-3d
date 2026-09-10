import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  ResourceQueue,
  withRetry,
  HttpError,
  nearbyChunks,
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
