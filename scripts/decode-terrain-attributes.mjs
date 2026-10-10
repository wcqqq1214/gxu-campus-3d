// Decode the actual terrain attributes for independent coverage checks.
// Usage: node scripts/decode-terrain-attributes.mjs MODEL.glb OUTPUT.json
import { createPrimitiveDecoder } from './draco-geometry.mjs';
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
const raw = fs.readFileSync(process.argv[2] || 'public/models/base.glb');
const length = raw.readUInt32LE(12),
  doc = JSON.parse(raw.subarray(20, 20 + length));
const bin = raw.subarray(28 + length);
const decode = await createPrimitiveDecoder(doc, bin);

assert(
  process.argv[2] && process.argv[3],
  'Expected input GLB and output JSON',
);
const node = doc.nodes.find(
  (n) => n.name.replace(/\.\d{3,}$/, '') === 'terrain',
);
assert(!node.matrix && !node.rotation && !node.translation && !node.scale);
const primitives = doc.meshes[node.mesh].primitives;
assert.equal(primitives.length, 1);
const g = decode(primitives[0]);
const pos = g.attributes.position.array,
  n = g.attributes.normal.array,
  u = g.attributes.uv.array;
const vertices = [],
  normals = [],
  uvs = [],
  triangles = [];
for (let i = 0; i < pos.length; i += 3) {
  vertices.push([pos[i], -pos[i + 2], pos[i + 1]]);
  normals.push([n[i], -n[i + 2], n[i + 1]]);
  uvs.push([u[(i / 3) * 2], u[(i / 3) * 2 + 1]]);
}
for (let i = 0; i < g.index.count; i += 3)
  triangles.push(Array.from(g.index.array.slice(i, i + 3)));
fs.writeFileSync(
  process.argv[3],
  JSON.stringify({
    modelSHA256: sha(raw),
    material: doc.materials[primitives[0].material].name,
    vertices,
    triangles,
    normals,
    uvs,
  }),
);
console.log(process.argv[2], vertices.length, triangles.length);
