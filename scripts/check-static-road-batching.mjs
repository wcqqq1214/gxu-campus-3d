// Verify static-road batching against actual Draco-decoded base geometry and recorded camera poses.
// Usage: node --experimental-strip-types scripts/check-static-road-batching.mjs MODEL.glb REPORT.json
import { createPrimitiveDecoder } from './draco-geometry.mjs';
import fs from 'node:fs';
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
import {
  batchPlatformRoadContacts,
  batchStaticRoadSurfaces,
} from '../lib/campus/road-batching.ts';
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
batchPlatformRoadContacts(root);
pruneGroundTriangles(root);
const rows = JSON.parse(
  fs.readFileSync(
    'docs/model-checks/refinement/s0-current-activity-samples.json',
  ),
)
  .filter((r) => r.label === 'current' && r.tier === '流畅')
  .flatMap((r) => r.samples);
const median = (a) => {
  a = a.slice().sort((a, b) => a - b);
  return a[Math.floor(a.length / 2)];
};
function measure() {
  const costs = new Map(),
    samples = [];
  root.updateMatrixWorld(true);
  for (const row of rows) {
    const b = row.benchmark,
      c = b.camera,
      [w, h] = b.viewport,
      f = b.frame;
    const camera = new THREE.PerspectiveCamera(
      41,
      w / h,
      Math.max(1, Math.min(100, (c.position[1] - 50) * 0.01)),
      30000,
    );
    camera.setViewOffset(
      w,
      h,
      w / 2 - f.left - f.width / 2,
      h / 2 - f.top - f.height / 2,
      w,
      h,
    );
    camera.position.fromArray(c.position);
    camera.lookAt(new THREE.Vector3(...c.target));
    camera.updateMatrixWorld();
    const frustum = new THREE.Frustum().setFromProjectionMatrix(
      new THREE.Matrix4().multiplyMatrices(
        camera.projectionMatrix,
        camera.matrixWorldInverse,
      ),
    );
    let triangles = 0,
      calls = 0;
    for (const parent of root.children) {
      if (!parent.visible) continue;
      let pt = 0,
        pc = 0;
      for (const mesh of parent.children) {
        if (!frustum.intersectsObject(mesh)) continue;
        const t = mesh.geometry.index.count / 3;
        pt += t;
        pc++;
      }
      triangles += pt;
      calls += pc;
      if (!costs.has(parent.name)) costs.set(parent.name, []);
      costs.get(parent.name).push({ triangles: pt, calls: pc });
    }
    samples.push({ triangles, calls });
  }
  return {
    triangles: median(samples.map((x) => x.triangles)),
    calls: median(samples.map((x) => x.calls)),
    samples,
    costs: [...costs]
      .map(([node, values]) => ({
        node,
        triangles: median(values.map((x) => x.triangles)),
        calls: median(values.map((x) => x.calls)),
      }))
      .sort((a, b) => b.triangles - a.triangles),
  };
}

function allFaces() {
  const rows = [];
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (!(o instanceof THREE.Mesh)) return;
    const attrs = Object.entries(o.geometry.attributes).sort(([a], [b]) =>
      a.localeCompare(b),
    );
    const props = JSON.stringify([
      o.material.uuid,
      o.castShadow,
      o.receiveShadow,
      o.renderOrder,
      o.layers.mask,
      o.frustumCulled,
    ]);
    const values = attrs.reduce((n, [, a]) => n + a.itemSize, 0),
      buf = Buffer.alloc(values * 3 * 4);
    for (let i = 0; i < o.geometry.index.count; i += 3) {
      let cursor = 0;
      for (let j = 0; j < 3; j++) {
        const k = o.geometry.index.getX(i + j);
        for (const [, a] of attrs)
          for (let q = 0; q < a.itemSize; q++) {
            buf.writeFloatLE(a.array[k * a.itemSize + q], cursor);
            cursor += 4;
          }
      }
      rows.push(sha(props + buf.toString('hex')));
    }
  });
  return rows.sort((a, b) => a.localeCompare(b));
}
const before = measure(),
  faceBefore = allFaces();
const totalRemoved = batchStaticRoadSurfaces(root);
const faceAfter = allFaces();
assert.deepEqual(faceAfter, faceBefore);
const after = measure();
const result = {
  asset: process.argv[2],
  assetSHA256: sha(raw),
  exactFaceAttributesAndMaterialIdentityRetained: true,
  comparedFaces: faceBefore.length,
  totalRemoved,
  before,
  after,
};
fs.writeFileSync(process.argv[3], JSON.stringify(result, null, 2));
console.log(
  JSON.stringify({
    faces: faceBefore.length,
    totalRemoved,
    before: { triangles: before.triangles, calls: before.calls },
    after: { triangles: after.triangles, calls: after.calls },
  }),
);
