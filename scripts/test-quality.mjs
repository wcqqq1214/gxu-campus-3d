import test from 'node:test';
import assert from 'node:assert/strict';
import { AdaptiveQuality, qualityProfile } from '../lib/campus/quality.ts';

test('持续低帧率分两级减少阴影、精细植被与资源预算，单次慢帧不降档', () => {
  const adaptive = new AdaptiveQuality();
  assert.equal(adaptive.sample(18, 20), false);
  assert.equal(adaptive.sample(18, 20), true);
  let p = qualityProfile('auto', false, false, adaptive.level);
  assert.deepEqual(
    [p.level, p.shadows, p.nearTrees, p.treeDensity, p.detailBudgetMiB],
    [1, false, false, 0.75, 48],
  );
  adaptive.sample(18, 20);
  adaptive.sample(18, 20);
  p = qualityProfile('auto', false, false, adaptive.level);
  assert.deepEqual([p.level, p.treeDensity, p.detailBudgetMiB], [2, 0.55, 24]);
});

test('流畅档30fps可恢复，但必须连续稳定并经过冷却，空闲和零样本不升级', () => {
  const adaptive = new AdaptiveQuality();
  for (let i = 0; i < 4; i++) adaptive.sample(18, 20);
  for (let i = 0; i < 19; i++) adaptive.sample(30, 30);
  assert.equal(adaptive.level, 2);
  assert.equal(adaptive.sample(30, 30), true);
  assert.equal(adaptive.level, 1);
  for (let i = 0; i < 30; i++) adaptive.sample(60, 0);
  assert.equal(adaptive.level, 1);
  for (let i = 0; i < 10; i++) adaptive.sample(60, 50);
  assert.equal(adaptive.level, 0);
});

test('手动画质、手机及省流量偏好保持优先，重置可重新采样', () => {
  assert.equal(qualityProfile('fine', true, true, 2).level, 0);
  assert.equal(qualityProfile('smooth', false, false, 0).level, 2);
  assert.equal(qualityProfile('auto', true, false, 0).level, 2);
  assert.equal(qualityProfile('auto', false, true, 0).level, 2);
  const adaptive = new AdaptiveQuality();
  adaptive.sample(12, 20);
  adaptive.sample(12, 20);
  adaptive.reset();
  assert.equal(adaptive.level, 0);
  assert.equal(adaptive.sample(12, 20), false);
});
