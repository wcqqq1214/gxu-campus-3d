import * as THREE from 'three';

/** Drop only exactly collapsed faces in decoded, static ground meshes. */
export function pruneGroundTriangles(root: THREE.Object3D) {
  const visited = new Set<THREE.BufferGeometry>();
  let removed = 0;
  root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return;
    let owner: THREE.Object3D | null = object;
    while (owner && !owner.userData.layer) owner = owner.parent;
    if (!['terrain', 'roads'].includes(owner?.userData.layer)) return;
    const geometry = object.geometry;
    const material = object.material;
    if (
      object instanceof THREE.SkinnedMesh ||
      object instanceof THREE.InstancedMesh ||
      !(material instanceof THREE.MeshStandardMaterial) ||
      material.wireframe ||
      material.displacementMap ||
      geometry.groups.length ||
      Object.keys(geometry.morphAttributes).length ||
      geometry.drawRange.start !== 0 ||
      geometry.drawRange.count !== Infinity ||
      visited.has(geometry)
    )
      return;
    visited.add(geometry);
    const positions = geometry.getAttribute('position');
    const index = geometry.getIndex();
    if (!positions || !index || index.count % 3) return;
    const retained: number[] = [];
    for (let i = 0; i < index.count; i += 3) {
      const a = index.getX(i),
        b = index.getX(i + 1),
        c = index.getX(i + 2);
      const ux = positions.getX(b) - positions.getX(a);
      const uy = positions.getY(b) - positions.getY(a);
      const uz = positions.getZ(b) - positions.getZ(a);
      const vx = positions.getX(c) - positions.getX(a);
      const vy = positions.getY(c) - positions.getY(a);
      const vz = positions.getZ(c) - positions.getZ(a);
      // No area tolerance: even tiny nonzero triangles remain unchanged.
      if (
        uy * vz - uz * vy === 0 &&
        uz * vx - ux * vz === 0 &&
        ux * vy - uy * vx === 0
      )
        continue;
      retained.push(a, b, c);
    }
    if (retained.length === index.count) return;
    removed += (index.count - retained.length) / 3;
    geometry.setIndex(retained);
    // Keep attributes and bounds: surviving vertices, shading, UVs and culling
    // are identical, and there is no retained GPU index buffer before upload.
  });
  return removed;
}
