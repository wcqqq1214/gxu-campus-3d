// Historical contact-only stage, replaced in the browser by commit c30990c.
// Retained for decoded-asset checks and replaying recorded before/after comparisons.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { disposeObject } from '../../lib/campus/resources.ts';

function signature(mesh: THREE.Mesh) {
  const material = mesh.material;
  const g = mesh.geometry;
  if (
    mesh instanceof THREE.InstancedMesh ||
    mesh instanceof THREE.SkinnedMesh ||
    !(material instanceof THREE.MeshStandardMaterial) ||
    !['asphalt', 'curb'].includes(material.name) ||
    material.transparent ||
    !mesh.visible ||
    mesh.children.length ||
    g.groups.length ||
    Object.keys(g.morphAttributes).length ||
    g.drawRange.start !== 0 ||
    g.drawRange.count !== Infinity
  )
    return null;
  const properties: Record<string, unknown> = { ...material.toJSON() };
  delete properties.uuid;
  delete properties.metadata;
  return JSON.stringify({
    properties,
    matrix: mesh.matrixWorld.elements,
    layers: mesh.layers.mask,
    order: mesh.renderOrder,
    cast: mesh.castShadow,
    receive: mesh.receiveShadow,
    culled: mesh.frustumCulled,
  });
}

/** Rejoin the two small contact materials split out for local road quantization. */
export function batchPlatformRoadContacts(root: THREE.Object3D) {
  const road = root.children.find((o) => /^roads(?:[._]?\d+)?$/.test(o.name));
  const local = root.children.find(
    (o) => o.name === 'paving-civil-platform-service-export',
  );
  if (
    !road ||
    !local ||
    road.userData.layer !== 'roads' ||
    local.userData.layer !== 'roads' ||
    !road.visible ||
    !local.visible
  )
    return 0;
  root.updateMatrixWorld(true);
  let removed = 0;
  // Retiring a merged mesh mutates local.children during this loop.
  for (const child of local.children.slice()) {
    if (!(child instanceof THREE.Mesh)) continue;
    const key = signature(child);
    if (!key) continue;
    const target = road.children.find(
      (o) => o instanceof THREE.Mesh && signature(o) === key,
    ) as THREE.Mesh | undefined;
    if (!target) continue;
    const geometry = mergeGeometries([target.geometry, child.geometry], false);
    if (!geometry) continue;
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    const previous = new THREE.Mesh(target.geometry, target.material);
    target.geometry = geometry;
    const retired = new THREE.Group();
    retired.add(previous, child);
    disposeObject(retired, [root]);
    removed++;
  }
  return removed;
}
