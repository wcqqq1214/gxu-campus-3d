import test from 'node:test';
import assert from 'node:assert/strict';
import { createLoadStatusStore } from '../lib/campus/load-status-store.ts';

test('progress changes only the status snapshot; error selectors stay stable', () => {
  const store = createLoadStatusStore();
  const initial = store.getInitial();
  let calls = 0;
  const stop = store.subscribe(() => calls++);
  const message = {
    text: '正在加载{name} {percent}%',
    values: { name: '图书馆', percent: 42 },
  };
  store.set(message, false, 0.42);
  const snapshot = store.get();
  store.set({ ...message, values: { ...message.values } }, false, 0.42);
  assert.equal(store.get(), snapshot);
  store.set(message, false, 0.421);
  assert.equal(store.get(), snapshot);
  assert.equal(calls, 1);
  assert.equal(store.getError(), false);
  store.set('失败', true);
  assert.equal(store.getError(), true);
  assert.equal(store.get().progress, undefined);
  store.set('正在重新加载…');
  assert.equal(store.getError(), false);
  assert.equal(store.getInitial(), initial);
  stop();
  store.set('');
  assert.equal(calls, 3);
});
