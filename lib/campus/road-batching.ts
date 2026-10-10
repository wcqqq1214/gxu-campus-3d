import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { disposeObject } from './resources.ts';

const identity = new THREE.Matrix4();
const staticRoadName =
  /^(roads(?:[._]?\d+)?|infra-approach-.+|paving-.+|site-.+)$/;

function staticSignature(mesh: THREE.Mesh) {
  const g = mesh.geometry;
  const m = mesh.material;
  if (mesh.matrixAutoUpdate) mesh.updateMatrix();
  if (
    mesh instanceof THREE.InstancedMesh ||
    mesh instanceof THREE.SkinnedMesh ||
    !(m instanceof THREE.MeshStandardMaterial) ||
    m.transparent ||
    m.opacity !== 1 ||
    !mesh.visible ||
    mesh.children.length ||
    !mesh.matrix.equals(identity) ||
    g.groups.length ||
    Object.keys(g.morphAttributes).length ||
    g.drawRange.start !== 0 ||
    g.drawRange.count !== Infinity ||
    Object.values(g.attributes).some(
      (a) => !(a instanceof THREE.BufferAttribute),
    )
  )
    return null;
  return JSON.stringify({
    // Identity retains textures, uniforms, shader hooks and day/night updates.
    material: m.uuid,
    indexed: g.index !== null,
    attributes: Object.entries(g.attributes)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([name, a]) => {
        const attribute = a as THREE.BufferAttribute;
        return [
          name,
          attribute.itemSize,
          attribute.normalized,
          attribute.array.constructor.name,
          attribute.gpuType,
        ];
      }),
    layers: mesh.layers.mask,
    order: mesh.renderOrder,
    cast: mesh.castShadow,
    receive: mesh.receiveShadow,
    culled: mesh.frustumCulled,
  });
}

/** Batch static road/site surfaces; replaceable corridor and bridge LODs stay separate. */
export function batchStaticRoadSurfaces(root: THREE.Object3D) {
  const buckets = new Map<string, THREE.Mesh[]>();
  for (const parent of root.children) {
    if (parent.matrixAutoUpdate) parent.updateMatrix();
    if (
      !staticRoadName.test(parent.name) ||
      parent.userData.layer !== 'roads' ||
      !parent.visible ||
      !parent.matrix.equals(identity) ||
      parent.renderOrder !== 0
    )
      continue;
    // glTF represents a one-material node as a Mesh, multiple materials as a Group.
    for (const child of parent instanceof THREE.Mesh
      ? [parent]
      : parent.children) {
      if (!(child instanceof THREE.Mesh)) continue;
      const key = staticSignature(child);
      if (key === null) continue;
      const meshes = buckets.get(key) ?? [];
      meshes.push(child);
      buckets.set(key, meshes);
    }
  }
  const combined = new THREE.Group();
  combined.name = 'static-road-surfaces';
  combined.userData.layer = 'roads';
  root.add(combined);
  let removedDraws = 0;
  for (const meshes of buckets.values()) {
    if (meshes.length < 2) continue;
    const geometry = mergeGeometries(
      meshes.map((m) => m.geometry),
      false,
    );
    if (!geometry) continue;
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    const first = meshes[0];
    const merged = new THREE.Mesh(geometry, first.material);
    merged.name = `${combined.name}-${combined.children.length}`;
    merged.layers.mask = first.layers.mask;
    merged.renderOrder = first.renderOrder;
    merged.castShadow = first.castShadow;
    merged.receiveShadow = first.receiveShadow;
    merged.frustumCulled = first.frustumCulled;
    combined.add(merged);
    const retired = new THREE.Group();
    for (const mesh of meshes) retired.add(mesh);
    disposeObject(retired, [root]);
    removedDraws += meshes.length - 1;
  }
  if (!combined.children.length) root.remove(combined);
  return removedDraws;
}
