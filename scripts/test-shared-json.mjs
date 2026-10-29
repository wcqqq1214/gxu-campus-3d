import test from 'node:test';
import assert from 'node:assert/strict';
import { createSharedJson } from '../lib/campus/shared-json.ts';
const tick = () => new Promise((resolve) => setImmediate(resolve));
test('shared JSON isolates consumer cancellation and retains completed data', async () => {
  let calls = 0,
    resolve,
    requestSignal;
  const load = createSharedJson('/boundary', (_url, signal) => {
    calls++;
    requestSignal = signal;
    return new Promise((r) => (resolve = r));
  });
  const a = new AbortController(),
    b = new AbortController();
  const pa = load(a.signal),
    pb = load(b.signal);
  a.abort();
  await assert.rejects(pa, { name: 'AbortError' });
  assert.equal(requestSignal.aborted, false);
  const value = { rings: [] };
  resolve(value);
  assert.equal(await pb, value);
  assert.equal(await load(new AbortController().signal), value);
  assert.equal(calls, 1);
});
test('last consumer abort cancels the transfer; failures never poison retries', async () => {
  let calls = 0;
  const load = createSharedJson('/boundary', (_url, signal) => {
    calls++;
    return calls === 1
      ? new Promise((_r, reject) =>
          signal.addEventListener('abort', () => reject(signal.reason), {
            once: true,
          }),
        )
      : Promise.resolve({ ok: true });
  });
  const c = new AbortController();
  const pending = load(c.signal);
  c.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  await tick();
  assert.deepEqual(await load(new AbortController().signal), { ok: true });
  assert.equal(calls, 2);
  let failures = 0;
  const retry = createSharedJson('/boundary', async () => {
    if (!failures++) throw Error('503');
    return 1;
  });
  await assert.rejects(retry(new AbortController().signal), /503/);
  assert.equal(await retry(new AbortController().signal), 1);
});
