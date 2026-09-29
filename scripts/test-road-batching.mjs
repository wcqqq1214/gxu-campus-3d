import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { batchPlatformRoadContacts } from '../lib/campus/road-batching.ts';
function fixture() {
  const root = new THREE.Group(),
    road = new THREE.Group(),
    local = new THREE.Group();
  road.name = 'roads.001';
  local.name = 'paving-civil-platform-service-export';
  road.userData.layer = local.userData.layer = 'roads';
  root.add(road, local);
  for (const name of ['asphalt', 'curb', 'road']) {
    const material = new THREE.MeshStandardMaterial({ name });
    for (const parent of [road, local]) {
      const geometry = new THREE.BoxGeometry();
      geometry.clearGroups();
      parent.add(new THREE.Mesh(geometry, material));
    }
  }
  return { root, road, local };
}
test('road contacts merge only identical small materials; preserve indices and layer parents', () => {
  const { root, road, local } = fixture();
  const source = road.children[0].geometry,
    contact = local.children[0].geometry;
  const positions = [
    ...source.attributes.position.array,
    ...contact.attributes.position.array,
  ];
  assert.equal(batchPlatformRoadContacts(root), 2);
  assert.deepEqual(
    [...road.children[0].geometry.attributes.position.array],
    positions,
  );
  assert.equal(
    road.children[0].geometry.index.count,
    source.index.count + contact.index.count,
  );
  assert.equal(local.children.length, 1);
  assert.equal(local.children[0].material.name, 'road');
  assert.equal(batchPlatformRoadContacts(root), 0);
});
test('different transforms, materials and render state cannot be batched', () => {
  for (const mutate of [
    (o) => (o.position.x = 1),
    (o) => (o.material = o.material.clone()),
    (o) => (o.castShadow = true),
    (o) => (o.visible = false),
  ]) {
    const { root, local } = fixture();
    const o = local.children[0];
    mutate(o);
    if (o.material !== root.children[0].children[0].material)
      o.material.roughness = 0.23;
    assert.equal(batchPlatformRoadContacts(root), 1);
  }
});
test('different layer or unknown local node is left intact', () => {
  for (const mutate of [
    (o) => (o.userData.layer = 'buildings'),
    (o) => (o.name = 'another-road'),
    (o) => (o.visible = false),
  ]) {
    const { root, local } = fixture();
    mutate(local);
    assert.equal(batchPlatformRoadContacts(root), 0);
  }
});
