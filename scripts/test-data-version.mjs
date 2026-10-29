import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { dataVersion } from './data-version.mjs';
import { fetchJson } from '../lib/campus/streaming.ts';
test('data and runtime transformation changes invalidate the JSON revision', async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'campus-data-version-'));
  try {
    await writeFile(path.join(dir, 'a.json'), '{}');
    const first = await dataVersion(dir, 'v1');
    assert.match(first, /^[a-f0-9]{64}$/);
    assert.equal(await dataVersion(dir, 'v1'), first);
    assert.notEqual(await dataVersion(dir, 'v2'), first);
    await writeFile(path.join(dir, 'a.json'), '{"changed":true}');
    assert.notEqual(await dataVersion(dir, 'v1'), first);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
test('only versioned JSON requests use normal HTTP caching', async () => {
  const original = globalThis.fetch;
  const modes = [];
  globalThis.fetch = async (_url, options) => {
    modes.push(options.cache);
    return new Response('{}');
  };
  try {
    await fetchJson('/data/test.json', new AbortController().signal);
    await fetchJson(
      '/data/test.json?v=' + 'a'.repeat(64),
      new AbortController().signal,
    );
    assert.deepEqual(modes, ['no-cache', 'default']);
  } finally {
    globalThis.fetch = original;
  }
});
