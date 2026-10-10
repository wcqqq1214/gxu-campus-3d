// Decode the shipped Draco primitives and compare oriented, coloured triangles.
import { createPrimitiveDecoder } from './draco-geometry.mjs';
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { batchPlatformRoadContacts } from './fixtures/legacy-road-batching.ts';

const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
const raw = fs.readFileSync('public/models/base.glb');
const length = raw.readUInt32LE(12),
  doc = JSON.parse(raw.subarray(20, 20 + length));
const bin = raw.subarray(28 + length);
const decode = await createPrimitiveDecoder(doc, bin);

function triangles(parent) {
  const result = [];
  for (const mesh of parent.children) {
    const g = mesh.geometry,
      m = mesh.material,
      p = g.attributes.position,
      n = g.attributes.normal;
    const c = g.attributes.color,
      indices = g.index;
    mesh.updateMatrix();
    const properties = m.toJSON();
    for (const key of ['uuid', 'name', 'metadata', 'color', 'vertexColors'])
      delete properties[key];
    const key = JSON.stringify(properties);
    for (let i = 0; i < indices.count; i += 3) {
      const corners = [];
      for (let j = 0; j < 3; j++) {
        const v = indices.getX(i + j);
        const xyz = new THREE.Vector3()
          .fromBufferAttribute(p, v)
          .applyMatrix4(mesh.matrix);
        const rgb = c
          ? [
              c.getX(v) * m.color.r,
              c.getY(v) * m.color.g,
              c.getZ(v) * m.color.b,
            ]
          : [m.color.r, m.color.g, m.color.b];
        const values = [
          ...xyz.toArray(),
          n.getX(v),
          n.getY(v),
          n.getZ(v),
          ...rgb,
        ];
        if (g.attributes.uv)
          values.push(g.attributes.uv.getX(v), g.attributes.uv.getY(v));
        const bytes = Buffer.alloc(values.length * 4);
        values.forEach((value, k) =>
          bytes.writeFloatLE(value === 0 ? 0 : value, k * 4),
        );
        corners.push(bytes.toString('hex'));
      }
      const [a, b, c0] = corners;
      result.push(
        key +
          [a + b + c0, b + c0 + a, c0 + a + b].sort((x, y) =>
            x < y ? -1 : x > y ? 1 : 0,
          )[0],
      );
    }
  }
  return result.sort((x, y) => (x < y ? -1 : x > y ? 1 : 0));
}

const root = new THREE.Group();
const textures = new Map();
for (const node of doc.nodes.filter(
  (n) =>
    /^roads(?:[._]?\d+)?$/.test(n.name) ||
    n.name === 'paving-civil-platform-service-export',
)) {
  assert(!node.matrix && !node.translation && !node.rotation && !node.scale);
  const parent = new THREE.Group();
  parent.name = node.name;
  parent.userData = { ...node.extras };
  root.add(parent);
  for (const primitive of doc.meshes[node.mesh].primitives) {
    const source = doc.materials[primitive.material];
    if (!['asphalt', 'curb'].includes(source.name)) continue;
    const pbr = source.pbrMetallicRoughness;
    assert(!source.extensions);
    const mat = new THREE.MeshStandardMaterial({
      name: source.name,
      roughness: pbr.roughnessFactor ?? 1,
      metalness: pbr.metallicFactor ?? 1,
      side: source.doubleSided ? THREE.DoubleSide : THREE.FrontSide,
    });
    mat.color.fromArray(pbr.baseColorFactor ?? [1, 1, 1, 1]);
    if (pbr.baseColorTexture) {
      const index = pbr.baseColorTexture.index;
      assert(
        !pbr.baseColorTexture.extensions && !pbr.baseColorTexture.texCoord,
      );
      if (!textures.has(index)) textures.set(index, new THREE.Texture());
      mat.map = textures.get(index);
    }
    parent.add(new THREE.Mesh(decode(primitive), mat));
  }
}
assert.equal(root.children.length, 2);
const flattened = () => ({
  children: root.children.flatMap((p) => p.children),
});
const before = triangles(flattened()),
  removedDraws = batchPlatformRoadContacts(root),
  after = triangles(flattened());
assert.equal(removedDraws, 2);
assert.deepEqual(before, after);
const report = {
  passed: true,
  modelSha256: sha(raw),
  removedDraws,
  triangles: before.length,
  orientedTriangleHash: sha(before.join('\n')),
  scope:
    'Decoded asphalt and curb triangles: exact Float32 positions, normals, UV, color and material properties retained; same transforms and roads layer. Local road material stays separate.',
};
fs.writeFileSync(
  'docs/model-checks/refinement/s2-platform-path-contact-batching-decoded.json',
  JSON.stringify(report, null, 2) + '\n',
);
console.log(report);
