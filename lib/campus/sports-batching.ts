import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { disposeObject } from './resources.ts';

const surfaces = new Set([
  'track',
  'trackAlt',
  'trackApron',
  'fieldGreen',
  'fieldStripe',
]);
const nodes = new Set(['sports-east-track', 'sports-west-track']);

function signature(mesh: THREE.Mesh): string | null {
  const material = mesh.material;
  const geometry = mesh.geometry;
  if (
    mesh instanceof THREE.SkinnedMesh ||
    mesh instanceof THREE.InstancedMesh ||
    !(material instanceof THREE.MeshStandardMaterial) ||
    !surfaces.has(material.name) ||
    material.vertexColors ||
    material.transparent ||
    material.opacity !== 1 ||
    !mesh.visible ||
    mesh.children.length ||
    geometry.hasAttribute('color') ||
    Object.keys(geometry.morphAttributes).length ||
    geometry.groups.length ||
    geometry.drawRange.start !== 0 ||
    geometry.drawRange.count !== Infinity ||
    Object.values(material).some((value) => value instanceof THREE.Texture)
  )
    return null;
  // Material colour is baked as linear RGB; every other serialized property must match.
  const properties: Record<string, unknown> = { ...material.toJSON() };
  delete properties.uuid;
  delete properties.name;
  delete properties.color;
  delete properties.metadata;
  if (mesh.matrixAutoUpdate) mesh.updateMatrix();
  return JSON.stringify({
    material: properties,
    matrix: mesh.matrix.elements,
    layers: mesh.layers.mask,
    order: mesh.renderOrder,
    castShadow: mesh.castShadow,
    receiveShadow: mesh.receiveShadow,
    frustumCulled: mesh.frustumCulled,
  });
}

/** Merge only colour variants within each track node; keep layer/LOD parents intact. */
export function batchSportsSurfaces(root: THREE.Object3D) {
  const stats = { batches: 0, removedDraws: 0, colourBytes: 0 };
  const parents: THREE.Object3D[] = [];
  root.traverse((object) => {
    if (nodes.has(object.name)) parents.push(object);
  });
  for (const parent of parents) {
    const buckets = new Map<string, THREE.Mesh[]>();
    for (const child of parent.children) {
      if (!(child instanceof THREE.Mesh)) continue;
      const key = signature(child);
      if (key === null) continue;
      const bucket = buckets.get(key) ?? [];
      bucket.push(child);
      buckets.set(key, bucket);
    }
    for (const meshes of buckets.values()) {
      if (meshes.length < 2) continue;
      const inputs = meshes.map((mesh) => {
        const geometry = mesh.geometry.clone();
        const colour = (mesh.material as THREE.MeshStandardMaterial).color;
        const count = geometry.getAttribute('position').count;
        const rgb = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
          rgb[i * 3] = colour.r;
          rgb[i * 3 + 1] = colour.g;
          rgb[i * 3 + 2] = colour.b;
        }
        geometry.setAttribute('color', new THREE.BufferAttribute(rgb, 3));
        return geometry;
      });
      const geometry = mergeGeometries(inputs, false);
      for (const input of inputs) input.dispose();
      if (!geometry) continue;
      geometry.computeBoundingBox();
      geometry.computeBoundingSphere();
      const first = meshes[0];
      const material = (first.material as THREE.MeshStandardMaterial).clone();
      material.name = 'trackSurfaceColours';
      material.color.setRGB(1, 1, 1);
      material.vertexColors = true;
      const merged = new THREE.Mesh(geometry, material);
      merged.name = `${parent.name}-colours`;
      merged.position.copy(first.position);
      merged.quaternion.copy(first.quaternion);
      merged.scale.copy(first.scale);
      merged.matrix.copy(first.matrix);
      merged.matrixAutoUpdate = first.matrixAutoUpdate;
      merged.layers.mask = first.layers.mask;
      merged.renderOrder = first.renderOrder;
      merged.castShadow = first.castShadow;
      merged.receiveShadow = first.receiveShadow;
      merged.frustumCulled = first.frustumCulled;
      parent.add(merged);
      const retired = new THREE.Group();
      for (const mesh of meshes) retired.add(mesh);
      disposeObject(retired, [root]);
      stats.batches++;
      stats.removedDraws += meshes.length - 1;
      stats.colourBytes += geometry.getAttribute('color').array.byteLength;
    }
  }
  return stats;
}
