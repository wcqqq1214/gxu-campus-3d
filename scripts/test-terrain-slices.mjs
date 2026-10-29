import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createPalette } from '../lib/campus/palette.ts';

test('sliced terrain smoothing preserves the original rounded groups and sums', () => {
  const n = 17000;
  const positions = new Float32Array(n * 3),
    normals = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    positions.set([(i % 27) / 1000, (i % 3) / 1000, -(i % 71) / 1000], i * 3);
    normals.set([i % 5, 1, i % 7], i * 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(normals.slice(), 3));
  const mesh = new THREE.Mesh(
    g,
    new THREE.MeshStandardMaterial({ name: 'grass' }),
  );
  // Independent copy of the prior grouping/summation contract.
  const groups = new Map(),
    keys = [];
  for (let i = 0; i < n; i++) {
    const key = [0, 1, 2].map((k) => positions[i * 3 + k].toFixed(2)).join(',');
    keys.push(key);
    const v = groups.get(key) ?? new THREE.Vector3();
    v.add(new THREE.Vector3(...normals.slice(i * 3, i * 3 + 3)));
    groups.set(key, v);
  }
  for (const v of groups.values()) v.normalize();
  const expected = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) groups.get(keys[i]).toArray(expected, i * 3);
  const palette = createPalette([]);
  const steps = palette.terrainSteps(mesh);
  let slices = 0;
  while (!steps.next().done) {
    slices++;
    assert.equal(g.attributes.normal.version, 0, 'no partial GPU upload');
  }
  assert.ok(slices >= 8);
  assert.deepEqual(g.attributes.normal.array, expected);
  assert.equal(g.attributes.normal.version, 1);
  assert.equal(
    palette.terrainSteps(mesh).next().done,
    true,
    'smooth only once',
  );
});
