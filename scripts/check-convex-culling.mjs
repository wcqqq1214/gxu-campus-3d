// Verify convex-face culling on real Draco geometry; write snapshots for Blender ray checks.
// Usage: node --experimental-strip-types scripts/check-convex-culling.mjs MODEL.glb OUTPUT_DIR
import { createPrimitiveDecoder } from './draco-geometry.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { pruneGroundTriangles } from '../lib/campus/ground-triangles.ts';

const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
const raw = fs.readFileSync(process.argv[2] || 'public/models/base.glb');
const length = raw.readUInt32LE(12),
  doc = JSON.parse(raw.subarray(20, 20 + length));
const bin = raw.subarray(28 + length);
const decode = await createPrimitiveDecoder(doc, bin);

import { batchSportsSurfaces } from '../lib/campus/sports-batching.ts';
import { batchStaticRoadSurfaces } from '../lib/campus/road-batching.ts';
const textures = new Map();
const materials = doc.materials.map((source) => {
  const pbr = source.pbrMetallicRoughness;
  const m = new THREE.MeshStandardMaterial({
    name: source.name,
    roughness: pbr.roughnessFactor ?? 1,
    metalness: pbr.metallicFactor ?? 1,
    side: source.doubleSided ? THREE.DoubleSide : THREE.FrontSide,
  });
  m.color.fromArray(pbr.baseColorFactor ?? [1, 1, 1, 1]);
  if (pbr.baseColorTexture) {
    const i = pbr.baseColorTexture.index;
    if (!textures.has(i)) textures.set(i, new THREE.Texture());
    m.map = textures.get(i);
  }
  assert(!source.alphaMode || source.alphaMode === 'OPAQUE');
  if (['sportWhite', 'roadWhite', 'roadYellow', 'tactile'].includes(m.name)) {
    m.polygonOffset = true;
    m.polygonOffsetFactor = -2;
    m.polygonOffsetUnits = -2;
  }
  return m;
});
const root = new THREE.Group();
for (const node of doc.nodes) {
  if (node.mesh === undefined) continue;
  assert(!node.matrix && !node.rotation && !node.translation && !node.scale);
  const parent = new THREE.Group();
  parent.name = node.name;
  parent.userData = { ...node.extras };
  root.add(parent);
  for (const primitive of doc.meshes[node.mesh].primitives) {
    const geometry = decode(primitive),
      a = doc.accessors[primitive.attributes.POSITION];
    geometry.boundingBox = new THREE.Box3(
      new THREE.Vector3(...a.min),
      new THREE.Vector3(...a.max),
    );
    geometry.boundingSphere = geometry.boundingBox.getBoundingSphere(
      new THREE.Sphere(),
    );
    const mesh = new THREE.Mesh(geometry, materials[primitive.material]);
    mesh.castShadow = ![
      'sportWhite',
      'roadWhite',
      'roadYellow',
      'tactile',
      'water',
    ].includes(mesh.material.name);
    mesh.receiveShadow = true;
    parent.add(mesh);
  }
  parent.visible = parent.name !== 'landmark-library';
}
batchSportsSurfaces(root);
batchStaticRoadSurfaces(root);
pruneGroundTriangles(root);

import { createConvexCulling } from '../lib/campus/convex-culling.ts';
const meshes = [];
root.traverseVisible((o) => {
  if (o instanceof THREE.Mesh) meshes.push(o);
});
const originals = meshes.map((o) => new Uint32Array(o.geometry.index.array));
const attributes = meshes.map((o) =>
  Object.fromEntries(
    Object.entries(o.geometry.attributes).map(([k, a]) => [
      k,
      sha(Buffer.from(a.array.buffer, a.array.byteOffset, a.array.byteLength)),
    ]),
  ),
);
const originalIndexHashes = meshes.map((o) =>
  sha(Buffer.from(o.geometry.index.array.buffer)),
);
const control = createConvexCulling(root);
root.updateMatrixWorld(true);
const positions = [],
  offsets = [];
for (const mesh of meshes) {
  assert(mesh.matrixWorld.equals(new THREE.Matrix4()));
  offsets.push(positions.length / 3);
  const a = mesh.geometry.attributes.position;
  for (let i = 0; i < a.count; i++)
    positions.push(a.getX(i), a.getY(i), a.getZ(i));
}
const before = [];
for (let m = 0; m < meshes.length; m++)
  for (const id of originals[m]) before.push(id + offsets[m]);
assert(process.argv[3], 'OUTPUT_DIR is required');
const work = path.resolve(process.argv[3]) + path.sep;
fs.mkdirSync(work, { recursive: true });
fs.writeFileSync(
  work + 'ray-positions.bin',
  Buffer.from(new Float32Array(positions).buffer),
);
fs.writeFileSync(
  work + 'ray-before.bin',
  Buffer.from(new Uint32Array(before).buffer),
);
const rows = JSON.parse(
  fs.readFileSync(
    'docs/model-checks/refinement/s3-agriculture-road-activity.json',
  ),
).find(
  (r) => r.label === 'candidate' && r.tier === '流畅' && r.repeat === 2,
).samples;
const frames = [],
  timings = [];
for (const [order, k] of [0, 3, 7, 11, 15, 20].entries()) {
  const m = rows[k],
    c = m.benchmark.camera,
    f = m.benchmark.frame;
  const camera = new THREE.PerspectiveCamera(
    41,
    1280 / 720,
    Math.max(1, Math.min(100, (c.position[1] - 50) * 0.01)),
    30000,
  );
  camera.position.fromArray(c.position);
  camera.lookAt(new THREE.Vector3(...c.target));
  camera.setViewOffset(
    1280,
    720,
    1280 / 2 - (f.left + f.width / 2),
    720 / 2 - (f.top + f.height / 2),
    1280,
    720,
  );
  camera.updateMatrixWorld();
  const start = performance.now();
  control.update(camera, true);
  timings.push(performance.now() - start);
  const after = [],
    faceIds = [];
  let globalFace = 0;
  for (let j = 0; j < meshes.length; j++) {
    const g = meshes[j].geometry,
      n = Math.min(g.index.count, g.drawRange.count);
    let at = 0;
    for (let q = 0; q < originals[j].length; q += 3) {
      if (
        at < n &&
        [0, 1, 2].every((i) => originals[j][q + i] === g.index.getX(at + i))
      ) {
        for (let i = 0; i < 3; i++)
          after.push(g.index.getX(at + i) + offsets[j]);
        faceIds.push(globalFace + q / 3);
        at += 3;
      }
    }
    assert.equal(at, n);
    globalFace += originals[j].length / 3;
  }
  const rays = [],
    ray = new THREE.Raycaster();
  for (let y = 0; y < 54; y++)
    for (let x = 0; x < 96; x++) {
      ray.setFromCamera(
        new THREE.Vector2(((x + 0.5) / 96) * 2 - 1, 1 - ((y + 0.5) / 54) * 2),
        camera,
      );
      rays.push([...ray.ray.origin.toArray(), ...ray.ray.direction.toArray()]);
    }
  fs.writeFileSync(
    work + `ray-after-${order}.bin`,
    Buffer.from(new Uint32Array(after).buffer),
  );
  fs.writeFileSync(
    work + `ray-faces-${order}.bin`,
    Buffer.from(new Uint32Array(faceIds).buffer),
  );
  frames.push({
    order,
    rays,
    near: camera.near,
    sourceFaces: before.length / 3,
    retainedFaces: after.length / 3,
  });
}
control.update(new THREE.PerspectiveCamera(), false);
for (let j = 0; j < meshes.length; j++) {
  assert.deepEqual(
    new Uint32Array(meshes[j].geometry.index.array),
    originals[j],
  );
  assert.equal(
    sha(Buffer.from(meshes[j].geometry.index.array.buffer)),
    originalIndexHashes[j],
  );
  assert.deepEqual(
    Object.fromEntries(
      Object.entries(meshes[j].geometry.attributes).map(([k, a]) => [
        k,
        sha(
          Buffer.from(a.array.buffer, a.array.byteOffset, a.array.byteLength),
        ),
      ]),
    ),
    attributes[j],
  );
}
fs.writeFileSync(work + 'ray-frames.json', JSON.stringify(frames));
fs.writeFileSync(
  work + 'actual-runtime.json',
  JSON.stringify(
    {
      passed: true,
      modelSHA256: sha(raw),
      runtimeSHA256: sha(fs.readFileSync('lib/campus/convex-culling.ts')),
      poseSource:
        'docs/model-checks/refinement/s3-agriculture-road-activity.json (candidate smooth repeat 2; samples 0,3,7,11,15,20)',
      meshes: control.meshes,
      closedParts: control.parts,
      allAttributesAndRestoredIndexBytesIdentical: true,
      updateMilliseconds: timings,
      frames: frames.map(({ rays: _rays, ...r }) => r),
    },
    null,
    2,
  ),
);
console.log(
  'Actual runtime retained attributes/order; restored every index; timings',
  timings,
);
