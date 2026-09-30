// Decode the shipped Draco primitives and compare oriented, coloured triangles.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import * as THREE from 'three';
import { pruneGroundTriangles } from '../lib/campus/ground-triangles.ts';

const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
const raw = fs.readFileSync('public/models/base.glb');
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

const rows = [];
for (const node of doc.nodes) {
  if (
    node.mesh === undefined ||
    !['terrain', 'roads'].includes(node.extras?.layer)
  )
    continue;
  for (const primitive of doc.meshes[node.mesh].primitives) {
    const geometry = decode(primitive),
      root = new THREE.Group();
    root.userData.layer = node.extras.layer;
    root.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial()));
    const before = [...geometry.index.array],
      attributes = Object.fromEntries(
        Object.entries(geometry.attributes).map(([k, a]) => [
          k,
          sha(
            Buffer.from(a.array.buffer, a.array.byteOffset, a.array.byteLength),
          ),
        ]),
      );
    const removed = pruneGroundTriangles(root),
      after = [...geometry.index.array];
    const positions = geometry.attributes.position,
      expected = [];
    for (let i = 0; i < before.length; i += 3) {
      const a = new THREE.Vector3().fromBufferAttribute(positions, before[i]),
        b = new THREE.Vector3().fromBufferAttribute(positions, before[i + 1]),
        c = new THREE.Vector3().fromBufferAttribute(positions, before[i + 2]);
      if (b.sub(a).cross(c.sub(a)).lengthSq() !== 0)
        expected.push(...before.slice(i, i + 3));
    }
    assert.deepEqual(after, expected);
    assert.deepEqual(
      Object.fromEntries(
        Object.entries(geometry.attributes).map(([k, a]) => [
          k,
          sha(
            Buffer.from(a.array.buffer, a.array.byteOffset, a.array.byteLength),
          ),
        ]),
      ),
      attributes,
    );
    rows.push({
      node: node.name,
      material: doc.materials[primitive.material].name,
      before: before.length / 3,
      after: after.length / 3,
      removed,
    });
    geometry.dispose();
  }
}
const result = {
  passed: true,
  baseModelSha256: sha(raw),
  removedTriangles: rows.reduce((n, r) => n + r.removed, 0),
  scope:
    'Only exactly zero-area indexed ground triangles; all retained oriented index triples and every vertex attribute byte remain identical.',
  rows,
};
assert(result.removedTriangles > 0);
fs.writeFileSync(
  'docs/model-checks/refinement/s2-platform-west-road-degenerate-triangles.json',
  JSON.stringify(result, null, 2) + '\n',
);
console.log(
  JSON.stringify({
    passed: result.passed,
    removedTriangles: result.removedTriangles,
  }),
);
