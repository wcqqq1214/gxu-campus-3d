import test from 'node:test';
import assert from 'node:assert/strict';
import { Vector3 } from 'three';
import { BenchmarkOrbit } from '../lib/campus/benchmark-orbit.ts';

test('measurement orbit follows the same route despite slow frames and pauses', () => {
  const initial = new Vector3(90, 186, 440);
  for (const steps of [
    [16, 17, 16],
    [33, 34],
    [16, 250, 18, 75],
  ]) {
    const run = new BenchmarkOrbit(700, initial);
    let elapsed = 0,
      index = 0;
    while (elapsed < 31500) {
      elapsed = Math.min(31500, elapsed + steps[index++ % steps.length]);
      run.position(700 + elapsed);
      run.sampleDue();
    }
    const expected = initial
      .clone()
      .applyAxisAngle(new Vector3(0, 1, 0), 31.5 * 0.13);
    assert.ok(run.position(32200).distanceTo(expected) < 1e-10);
    assert.equal(run.sampleIndex, 21);
    assert.equal(run.elapsedMs, 31500);
    assert.equal(initial.y, 186);
  }
  // The former per-frame 50 ms cap loses camera angle on a 250 ms frame.
  assert.ok((0.25 - Math.min(0.05, 0.25)) * 0.13 > 0.025);
});

test('sampling stays anchored to start time and exposes missed windows', () => {
  const run = new BenchmarkOrbit(100, new Vector3(0, 10, 100));
  for (const [elapsed, index, due] of [
    [1499, 0, false],
    [1530, 1, true],
    [2999, 1, false],
    [3001, 2, true],
    [12100, 8, true],
    [12101, 8, false],
  ]) {
    run.position(100 + elapsed);
    assert.equal(run.sampleDue(), due);
    assert.equal(run.sampleIndex, index);
  }
  const restarted = new BenchmarkOrbit(15000, new Vector3(100, 10, 0));
  assert.deepEqual(restarted.position(14999).toArray(), [100, 10, 0]);
  assert.equal(restarted.sampleDue(), false);
});
