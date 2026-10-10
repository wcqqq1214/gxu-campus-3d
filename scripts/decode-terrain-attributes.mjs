// Decode the actual terrain attributes for independent coverage checks.
// Usage: node scripts/decode-terrain-attributes.mjs MODEL.glb OUTPUT.json
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import * as THREE from 'three';

const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
const raw = fs.readFileSync(process.argv[2] || 'public/models/base.glb');
const length = raw.readUInt32LE(12),
  doc = JSON.parse(raw.subarray(20, 20 + length));
const bin = raw.subarray(28 + length);
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'gxu-track-decoder-'));
let draco;
try {
  const wrapper = path.join(temporary, 'decoder.cjs');
  fs.copyFileSync('public/draco/draco_wasm_wrapper.js', wrapper);
  const factory = createRequire(import.meta.url)(wrapper);
  draco = await factory({
    wasmBinary: fs.readFileSync('public/draco/draco_decoder.wasm'),
  });
} finally {
  fs.rmSync(temporary, { recursive: true, force: true });
}

function decode(primitive) {
  const ext = primitive.extensions.KHR_draco_mesh_compression;
  const view = doc.bufferViews[ext.bufferView];
  const bytes = bin.subarray(
    view.byteOffset ?? 0,
    (view.byteOffset ?? 0) + view.byteLength,
  );
  const decoder = new draco.Decoder(),
    input = new draco.DecoderBuffer(),
    mesh = new draco.Mesh();
  input.Init(new Int8Array(bytes), bytes.length);
  const status = decoder.DecodeBufferToMesh(input, mesh);
  assert(status.ok(), status.error_msg());
  const geometry = new THREE.BufferGeometry();
  for (const [semantic, id] of Object.entries(ext.attributes)) {
    const attribute = decoder.GetAttributeByUniqueId(mesh, id);
    const values = new draco.DracoFloat32Array(),
      size = attribute.num_components();
    assert(decoder.GetAttributeFloatForAllPoints(mesh, attribute, values));
    const array = new Float32Array(mesh.num_points() * size);
    for (let i = 0; i < array.length; i++) array[i] = values.GetValue(i);
    const name = {
      POSITION: 'position',
      NORMAL: 'normal',
      TEXCOORD_0: 'uv',
      COLOR_0: 'color',
    }[semantic];
    assert(name, `Unrecognized attribute ${semantic}`);
    geometry.setAttribute(name, new THREE.BufferAttribute(array, size));
    draco.destroy(values);
  }
  const indices = [],
    face = new draco.DracoInt32Array();
  for (let i = 0; i < mesh.num_faces(); i++) {
    assert(decoder.GetFaceFromMesh(mesh, i, face));
    for (let j = 0; j < 3; j++) indices.push(face.GetValue(j));
  }
  geometry.setIndex(indices);
  for (const object of [status, face, mesh, input, decoder])
    draco.destroy(object);
  return geometry;
}

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
