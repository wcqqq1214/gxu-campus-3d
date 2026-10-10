import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { batchStaticRoadSurfaces } from '../lib/campus/road-batching.ts';

function fixture() {
  const root = new THREE.Group();
  root.position.set(4, 2, 6);
  const material = new THREE.MeshStandardMaterial({ name: 'path' });
  material.map = new THREE.Texture();
  const add = (name, direct = false) => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute([0, 0, 0, 2, 0, 0, 0, 0, 3], 3),
    );
    geometry.setAttribute(
      'normal',
      new THREE.Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0], 3),
    );
    geometry.setAttribute(
      'uv',
      new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1], 2),
    );
    geometry.setIndex([0, 2, 1]);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = mesh.receiveShadow = true;
    const parent = direct ? mesh : new THREE.Group();
    parent.name = name;
    parent.userData.layer = 'roads';
    if (!direct) parent.add(mesh);
    root.add(parent);
    return { parent, mesh, geometry };
  };
  const a = add('roads.001'),
    b = add('site-test', true),
    c = add('paving-test');
  return { root, material, add, a, b, c };
}

function faces(root) {
  const rows = [];
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (!(o instanceof THREE.Mesh)) return;
    for (let i = 0; i < o.geometry.index.count; i += 3) {
      const corners = [];
      for (let k = 0; k < 3; k++) {
        const j = o.geometry.index.getX(i + k);
        const xyz = new THREE.Vector3()
          .fromBufferAttribute(o.geometry.attributes.position, j)
          .applyMatrix4(o.matrixWorld)
          .toArray();
        const values = Object.entries(o.geometry.attributes)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([name, attr]) => [
            name,
            Array.from(
              attr.array.slice(j * attr.itemSize, (j + 1) * attr.itemSize),
            ),
          ]);
        corners.push([xyz, values]);
      }
      rows.push(
        JSON.stringify([
          o.material.uuid,
          o.castShadow,
          o.receiveShadow,
          o.renderOrder,
          o.layers.mask,
          corners,
        ]),
      );
    }
  });
  return rows.sort((a, b) => a.localeCompare(b));
}

test('单材质Mesh和多材质Group共同合批，保留有向面、属性、世界变换及材质身份', () => {
  const f = fixture(),
    before = faces(f.root);
  assert.equal(batchStaticRoadSurfaces(f.root), 2);
  assert.deepEqual(faces(f.root), before);
  const group = f.root.getObjectByName('static-road-surfaces');
  assert.equal(group.userData.layer, 'roads');
  assert.equal(group.children[0].material, f.material);
  assert.equal(group.children[0].geometry.index.count, 9);
  assert.equal(batchStaticRoadSurfaces(f.root), 0);
});

test('可被近景替换的走廊、桥梁和楼栋，以及其他图层均不合批', () => {
  const f = fixture();
  const retained = [
    'infra-road-03',
    'infra-lake-bridge-123',
    'landmark-bocui-bridge',
    'chunk-p0-n1',
    'north-campus-roads',
  ].map((n) => f.add(n));
  const other = f.add('site-nonroad');
  other.parent.userData.layer = 'buildings';
  retained.push(other);
  assert.equal(batchStaticRoadSurfaces(f.root), 2);
  for (const r of retained) assert.equal(r.mesh.parent, r.parent);
});

test('不合并变换、可见性、材质身份或渲染状态不一致的网格', () => {
  for (const configure of [
    (f) => f.b.parent.position.setX(1),
    (f) => (f.b.mesh.visible = false),
    (f) => (f.b.mesh.material = f.material.clone()),
    (f) => (f.b.mesh.castShadow = false),
    (f) => (f.b.mesh.receiveShadow = false),
    (f) => f.b.mesh.layers.set(2),
    (f) => (f.b.mesh.renderOrder = 1),
    (f) => (f.b.mesh.frustumCulled = false),
    (f) => f.b.geometry.setDrawRange(0, 3),
    (f) => f.b.geometry.addGroup(0, 3, 0),
    (f) =>
      (f.b.geometry.morphAttributes.position = [
        f.b.geometry.attributes.position.clone(),
      ]),
    (f) => f.b.geometry.deleteAttribute('uv'),
  ]) {
    const f = fixture();
    configure(f);
    const before = faces(f.root);
    assert.equal(batchStaticRoadSurfaces(f.root), 1);
    assert.equal(f.b.mesh.parent, f.root);
    assert.deepEqual(faces(f.root), before);
  }
  for (const configure of [
    (m) => (m.transparent = true),
    (m) => (m.opacity = 0.5),
  ]) {
    const f = fixture();
    configure(f.material);
    assert.equal(batchStaticRoadSurfaces(f.root), 0);
  }
});

test('共享的几何与贴图保留，独占旧几何释放，空合批不遗留节点', () => {
  const f = fixture();
  let sharedDisposed = 0,
    oldDisposed = 0,
    materialDisposed = 0,
    textureDisposed = 0;
  f.a.geometry.addEventListener('dispose', () => sharedDisposed++);
  f.b.geometry.addEventListener('dispose', () => oldDisposed++);
  f.material.addEventListener('dispose', () => materialDisposed++);
  f.material.map.addEventListener('dispose', () => textureDisposed++);
  const other = f.add('landmark-test');
  other.mesh.geometry = f.a.geometry;
  batchStaticRoadSurfaces(f.root);
  assert.deepEqual(
    [sharedDisposed, oldDisposed, materialDisposed, textureDisposed],
    [0, 1, 0, 0],
  );
  assert.equal(batchStaticRoadSurfaces(f.root), 0);
  assert.equal(
    f.root.children.filter((o) => o.name === 'static-road-surfaces').length,
    1,
  );
});
