import test from 'node:test';
import assert from 'node:assert/strict';
import { Vector3 } from 'three';
import { ShadowFrustum } from '../lib/campus/shadow-frustum.ts';

test('orbiting a static scene retains the same light volume despite roundoff', () => {
  const volume = new ShadowFrustum();
  const offset = new Vector3(89, 186, 444);
  const size = offset.length() * 0.8;
  assert.equal(volume.changed(205, 24, 490, size, 'day'), true);
  for (let frame = 0; frame < 3600; frame++) {
    offset.applyAxisAngle(new Vector3(0, 1, 0), 0.13 / 60);
    assert.equal(
      volume.changed(205, 24, 490, offset.length() * 0.8, 'day'),
      false,
    );
  }
});

test('pan, zoom, lighting and cumulative small movement invalidate the light volume', () => {
  const volume = new ShadowFrustum();
  for (const state of [
    [0, 0, 0, 100, 'day'],
    [1, 0, 0, 100, 'day'],
    [1, 2, 0, 100, 'day'],
    [1, 2, 3, 100, 'day'],
    [1, 2, 3, 150, 'day'],
    [1, 2, 3, 150, 'evening'],
  ]) {
    assert.equal(volume.changed(...state), true);
    assert.equal(volume.changed(...state), false);
  }
  assert.equal(volume.changed(1 + 0.4e-6, 2, 3, 150, 'evening'), false);
  assert.equal(volume.changed(1 + 1.2e-6, 2, 3, 150, 'evening'), true);
});
