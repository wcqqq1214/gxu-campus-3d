import test from 'node:test';
import assert from 'node:assert/strict';
import { FramePacer } from '../lib/campus/frame-pacing.ts';

function count(refresh, jitter = 0) {
  const pacer = new FramePacer();
  let frames = 0;
  // Ten seconds, excluding the end point; all refresh callbacks remain monotonic.
  for (let i = 0; i < refresh * 10; i++) {
    const time = i * 1000 / refresh + jitter * Math.sin(i * 2.3);
    if (pacer.shouldUpdate(time, true)) frames++;
  }
  return frames;
}

test('流畅档在不同刷新率保持约30次更新，不逐帧累积取整损失', () => {
  for (const refresh of [30, 60, 75, 90, 120, 144]) {
    assert.ok(Math.abs(count(refresh) - 300) <= 1, `${refresh} Hz`);
  }
  assert.ok(Math.abs(count(60, 1.5) - 300) <= 1);
  assert.ok(Math.abs(count(30, .9) - 300) <= 1);
});

test('回调慢于目标帧率时不额外丢帧，长暂停后不补画积压帧', () => {
  assert.equal(count(20), 200);
  const pacer = new FramePacer();
  assert.equal(pacer.shouldUpdate(0, true), true);
  assert.equal(pacer.shouldUpdate(16, true), false);
  assert.equal(pacer.shouldUpdate(10000, true), true);
  assert.equal(pacer.shouldUpdate(10000, true), false);
  assert.equal(pacer.shouldUpdate(10016, true), false);
  assert.equal(pacer.shouldUpdate(10033.333, true), true);
});

test('非流畅档不受限帧影响，切回流畅档采用新的时间起点', () => {
  const pacer = new FramePacer();
  for (let i = 0; i < 240; i++) assert.equal(pacer.shouldUpdate(i * 1000 / 120, false), true);
  assert.equal(pacer.shouldUpdate(2000, true), true);
  assert.equal(pacer.shouldUpdate(2016, true), false);
  assert.equal(pacer.shouldUpdate(2017, false), true);
  assert.equal(pacer.shouldUpdate(2018, true), true);
  assert.equal(pacer.shouldUpdate(2034, true), false);
});
