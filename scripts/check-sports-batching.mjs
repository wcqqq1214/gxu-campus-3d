// Decode the shipped Draco primitives and compare oriented, coloured triangles.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import * as THREE from 'three';
import { batchSportsSurfaces } from '../lib/campus/sports-batching.ts';

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

const records = [];
for (const node of doc.nodes.filter((n) =>
  ['sports-east-track', 'sports-west-track'].includes(n.name),
)) {
  const root = new THREE.Group(),
    parent = new THREE.Group();
  parent.name = node.name;
  root.add(parent);
  for (const primitive of doc.meshes[node.mesh].primitives) {
    const source = doc.materials[primitive.material],
      pbr = source.pbrMetallicRoughness;
    // The tested track surfaces and markings have no textures or extensions.
    assert(!pbr.baseColorTexture && !source.extensions);
    const mat = new THREE.MeshStandardMaterial({
      name: source.name,
      roughness: pbr.roughnessFactor ?? 1,
      metalness: pbr.metallicFactor ?? 1,
      side: source.doubleSided ? THREE.DoubleSide : THREE.FrontSide,
    });
    mat.color.fromArray(pbr.baseColorFactor ?? [1, 1, 1, 1]);
    const mesh = new THREE.Mesh(decode(primitive), mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    if (mat.name === 'sportWhite') {
      mat.polygonOffset = true;
      mat.polygonOffsetFactor = -2;
      mat.polygonOffsetUnits = -2;
      mesh.castShadow = false;
    }
    parent.add(mesh);
  }
  const before = triangles(parent),
    beforeMeshes = parent.children.length;
  const stats = batchSportsSurfaces(root),
    after = triangles(parent);
  assert.deepEqual(
    after,
    before,
    `${node.name}: oriented coloured triangles changed`,
  );
  assert.equal(stats.removedDraws, 4);
  records.push({
    node: node.name,
    beforeMeshes,
    afterMeshes: parent.children.length,
    triangles: before.length,
    triangleHash: sha(before.join('\n')),
    ...stats,
  });
}
assert.equal(records.length, 2);
const report = {
  passed: true,
  modelSha256: sha(raw),
  records,
  method:
    'Actual Draco primitives; identical sorted oriented triangles with position, normal, linear RGB, optional UV and all other material properties. Float32 comparison, not a real-world geometry measurement.',
};
const output =
  process.argv[2] ??
  'docs/model-checks/refinement/s5-track-batching-decoded.json';
fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
