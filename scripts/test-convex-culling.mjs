import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {
  closedConvexParts,
  createConvexCulling,
} from '../lib/campus/convex-culling.ts';
function fixture() {
  const root = new THREE.Group();
  root.userData.layer = 'buildings';
  const g = new THREE.BoxGeometry(4, 4, 4);
  g.clearGroups();
  const mesh = new THREE.Mesh(
    g,
    new THREE.MeshStandardMaterial({ side: THREE.DoubleSide }),
  );
  root.add(mesh);
  root.updateMatrixWorld(true);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
  camera.position.set(0, 0, 20);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld();
  return { root, g, mesh, camera };
}
test('recognizes closed boxes despite split normal/UV vertices; rejects an opening, reversed shell and concavity', () => {
  assert.equal(closedConvexParts(fixture().g).length, 1);
  for (const alter of [
    (g) => g.setIndex([...g.index.array].slice(3)),
    (g) => {
      for (let i = 0; i < g.index.count; i += 3) {
        const a = g.index.getX(i);
        g.index.setX(i, g.index.getX(i + 1));
        g.index.setX(i + 1, a);
      }
    },
    (g) => {
      const p = g.attributes.position;
      for (let i = 0; i < p.count; i++)
        if (p.getX(i) === 2 && p.getY(i) === 2 && p.getZ(i) === 2)
          p.setXYZ(i, 0, 0, 0);
    },
  ]) {
    const { g } = fixture();
    alter(g);
    assert.equal(closedConvexParts(g).length, 0);
  }
});
test('retains closest visible surfaces across a full orbit, restores bytes for shadows, and keeps one index object', () => {
  const { root, g, mesh, camera } = fixture(),
    original = [...g.index.array],
    index = g.index;
  const baseline = mesh.clone();
  baseline.geometry = g.clone();
  baseline.updateMatrixWorld();
  const control = createConvexCulling(root);
  assert.equal(control.parts, 1);
  const ray = new THREE.Raycaster();
  let reduced = false;
  for (let a = 0; a < Math.PI * 2; a += 0.17) {
    camera.position.set(20 * Math.cos(a), 7, 20 * Math.sin(a));
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    control.update(camera, true);
    reduced ||= g.drawRange.count < index.count;
    assert.equal(g.index, index);
    for (const x of [-0.1, 0, 0.1])
      for (const y of [-0.1, 0, 0.1]) {
        ray.setFromCamera(new THREE.Vector2(x, y), camera);
        const before = ray.intersectObject(baseline)[0],
          after = ray.intersectObject(mesh)[0];
        assert.equal(Boolean(before), Boolean(after));
        if (before)
          assert.ok(Math.abs(before.distance - after.distance) < 1e-9);
      }
  }
  assert.ok(reduced);
  control.update(camera, false);
  assert.deepEqual([...index.array], original);
  assert.equal(g.drawRange.count, Infinity);
});
test('camera inside a solid or near-plane intersection preserves all exit faces', () => {
  const { root, g, camera } = fixture(),
    original = [...g.index.array],
    control = createConvexCulling(root);
  control.update(camera, true);
  camera.position.set(0, 0, 0);
  camera.lookAt(0, 0, -10);
  camera.updateMatrixWorld();
  control.update(camera, true);
  assert.equal(g.drawRange.count, g.index.count);
  assert.deepEqual([...g.index.array], original);
  camera.position.set(0, 0, 3);
  camera.near = 2;
  camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
  control.update(camera, true);
  assert.deepEqual([...g.index.array], original);
});
test('transparent, cutout, displaced, back-side, shared or morphed geometry stays unchanged', () => {
  for (const alter of [
    (f) => (f.mesh.material.transparent = true),
    (f) => (f.mesh.material.depthWrite = false),
    (f) => (f.mesh.material.depthFunc = THREE.AlwaysDepth),
    (f) => (f.mesh.material.stencilWrite = true),
    (f) => (f.mesh.material.alphaTest = 0.5),
    (f) => (f.mesh.material.displacementMap = new THREE.Texture()),
    (f) => (f.mesh.material.side = THREE.BackSide),
    (f) => f.root.add(f.mesh.clone()),
    (f) => (f.g.morphAttributes.position = [f.g.attributes.position.clone()]),
  ]) {
    const f = fixture();
    alter(f);
    const original = [...f.g.index.array],
      control = createConvexCulling(f.root);
    assert.equal(control.parts, 0);
    control.update(f.camera, true);
    assert.deepEqual([...f.g.index.array], original);
    assert.equal(f.g.drawRange.count, Infinity);
  }
});
