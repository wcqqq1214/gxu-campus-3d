import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { pruneGroundTriangles } from '../lib/campus/ground-triangles.ts';
function fixture() {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(
      [0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 0, 0, 0, 1e-12, 0],
      3,
    ),
  );
  geometry.setAttribute(
    'uv',
    new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1, 2, 0, 0, 1e-12], 2),
  );
  geometry.setIndex([0, 1, 2, 0, 0, 1, 0, 1, 3, 0, 1, 4]);
  const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial());
  const root = new THREE.Group();
  root.userData.layer = 'terrain';
  root.add(mesh);
  return { root, mesh, geometry };
}
test('删除重复顶点和共线零面积面，保留微小非零面、顺序与全部属性', () => {
  const { root, geometry } = fixture();
  const position = geometry.attributes.position,
    uv = geometry.attributes.uv;
  geometry.computeBoundingBox();
  const bounds = geometry.boundingBox;
  assert.equal(pruneGroundTriangles(root), 2);
  assert.deepEqual([...geometry.index.array], [0, 1, 2, 0, 1, 4]);
  assert.equal(geometry.attributes.position, position);
  assert.equal(geometry.attributes.uv, uv);
  assert.equal(geometry.boundingBox, bounds);
  assert.equal(pruneGroundTriangles(root), 0);
});
test('不修改建筑、线框、位移或具有分组和局部绘制范围的几何', () => {
  for (const configure of [
    ({ root }) => (root.userData.layer = 'buildings'),
    ({ mesh }) => (mesh.material.wireframe = true),
    ({ mesh }) => (mesh.material.displacementMap = new THREE.Texture()),
    ({ geometry }) => geometry.addGroup(0, 3, 0),
    ({ geometry }) => geometry.setDrawRange(3, 6),
    ({ geometry }) =>
      (geometry.morphAttributes.position = [
        geometry.attributes.position.clone(),
      ]),
  ]) {
    const f = fixture();
    configure(f);
    const index = f.geometry.index;
    assert.equal(pruneGroundTriangles(f.root), 0);
    assert.equal(f.geometry.index, index);
  }
});
test('共享几何只处理一次，空索引不会意外恢复全部顶点绘制', () => {
  const { root, mesh, geometry } = fixture();
  root.add(mesh.clone());
  geometry.setIndex([0, 0, 1]);
  assert.equal(pruneGroundTriangles(root), 1);
  assert.equal(geometry.index.count, 0);
});
test('没有退化面的网格保留原索引对象', () => {
  const { root, geometry } = fixture();
  geometry.setIndex([0, 1, 2]);
  const index = geometry.index;
  assert.equal(pruneGroundTriangles(root), 0);
  assert.equal(geometry.index, index);
});
