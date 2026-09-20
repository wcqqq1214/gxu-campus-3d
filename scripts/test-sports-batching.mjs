import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { batchSportsSurfaces } from '../lib/campus/sports-batching.ts';

function fixture() {
  const root = new THREE.Group(),
    group = new THREE.Group();
  group.name = 'sports-east-track';
  root.add(group);
  for (const [name, color] of [
    ['track', '#aa3333'],
    ['trackAlt', '#bb4444'],
  ]) {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshStandardMaterial({ name, color, roughness: 0.92 }),
    );
    mesh.geometry.clearGroups();
    mesh.position.set(1, 2, 3);
    mesh.castShadow = true;
    group.add(mesh);
  }
  return { root, group };
}

test('同一跑道内按顶点保留线性颜色、法线、变换和阴影，重复调用不再次合并', () => {
  const { root, group } = fixture();
  const originals = group.children.map((m) => ({
    colour: [m.material.color.r, m.material.color.g, m.material.color.b].map(
      Math.fround,
    ),
    positions: [...m.geometry.attributes.position.array],
    normals: [...m.geometry.attributes.normal.array],
  }));
  const counts = batchSportsSurfaces(root);
  assert.equal(counts.removedDraws, 1);
  assert.equal(group.children.length, 1);
  const merged = group.children[0];
  assert.deepEqual(merged.position.toArray(), [1, 2, 3]);
  assert.equal(merged.castShadow, true);
  assert.equal(merged.material.roughness, 0.92);
  assert.equal(merged.material.color.getHex(), 0xffffff);
  assert.deepEqual(
    [...merged.geometry.attributes.position.array],
    originals.flatMap((m) => m.positions),
  );
  assert.deepEqual(
    [...merged.geometry.attributes.normal.array],
    originals.flatMap((m) => m.normals),
  );
  assert.deepEqual(
    [...merged.geometry.attributes.color.array],
    originals.flatMap((m) =>
      Array.from({ length: m.positions.length / 3 }, () => m.colour).flat(),
    ),
  );
  assert.deepEqual(batchSportsSurfaces(root), {
    batches: 0,
    removedDraws: 0,
    colourBytes: 0,
  });
});

test('粗糙度、深度偏移、变换、贴图、透明度或图层不同时保留原分组', () => {
  for (const change of [
    (m) => {
      m.material.roughness = 0.5;
    },
    (m) => {
      m.material.polygonOffset = true;
    },
    (m) => {
      m.position.x = 5;
    },
    (m) => {
      m.material.map = new THREE.Texture();
    },
    (m) => {
      m.material.transparent = true;
    },
    (m) => {
      m.layers.set(2);
    },
    (m) => {
      m.geometry.setDrawRange(0, 3);
    },
  ]) {
    const { root, group } = fixture();
    change(group.children[1]);
    assert.equal(batchSportsSurfaces(root).batches, 0);
    assert.equal(group.children.length, 2);
  }
});

test('不跨跑道父节点合并、不处理标线，释放旧网格时保护其他对象共享资源', () => {
  const { root, group } = fixture();
  const original = group.children[0];
  let released = 0;
  original.geometry.addEventListener('dispose', () => released++);
  const retained = new THREE.Mesh(original.geometry, original.material);
  root.add(retained);
  const marking = new THREE.Mesh(
    new THREE.PlaneGeometry(),
    new THREE.MeshStandardMaterial({ name: 'sportWhite' }),
  );
  group.add(marking);
  assert.equal(batchSportsSurfaces(root).batches, 1);
  assert.equal(released, 0);
  assert.equal(group.children.includes(marking), true);
  assert.equal(root.children.includes(retained), true);
  const other = fixture();
  other.group.name = 'unrelated-building';
  assert.equal(batchSportsSurfaces(other.root).batches, 0);
});
