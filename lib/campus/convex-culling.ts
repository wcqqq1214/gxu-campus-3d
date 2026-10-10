import * as THREE from 'three';

export interface ClosedPart {
  faces: number[];
  planes: THREE.Plane[];
  bounds: THREE.Box3;
}

/** Find small, closed, consistently outward convex solids in one material mesh. */
export function closedConvexParts(
  geometry: THREE.BufferGeometry,
): ClosedPart[] {
  const position = geometry.getAttribute('position'),
    index = geometry.index;
  if (!position || !index || index.count % 3) return [];
  const points: THREE.Vector3[] = [],
    canonical: number[] = [],
    keys = new Map<string, number>();
  for (let i = 0; i < position.count; i++) {
    const p = new THREE.Vector3().fromBufferAttribute(position, i);
    if (![p.x, p.y, p.z].every(Number.isFinite)) return [];
    const key = `${p.x},${p.y},${p.z}`;
    let id = keys.get(key);
    if (id === undefined) {
      id = points.length;
      keys.set(key, id);
      points.push(p);
    }
    canonical.push(id);
  }
  const count = index.count / 3,
    parents = Array.from({ length: count }, (_, i) => i);
  const find = (i: number): number => {
    while (parents[i] !== i) {
      parents[i] = parents[parents[i]];
      i = parents[i];
    }
    return i;
  };
  const faces: number[][] = [],
    edges = new Map<string, { face: number; sign: number }[]>();
  for (let i = 0; i < count; i++) {
    const ids = [0, 1, 2].map((k) => canonical[index.getX(i * 3 + k)]);
    faces.push(ids);
    for (let k = 0; k < 3; k++) {
      const a = ids[k],
        b = ids[(k + 1) % 3],
        key = `${Math.min(a, b)},${Math.max(a, b)}`;
      const owners = edges.get(key) ?? [];
      if (owners.length) parents[find(i)] = find(owners[0].face);
      owners.push({ face: i, sign: a < b ? 1 : -1 });
      edges.set(key, owners);
    }
  }
  const groups = new Map<number, number[]>(),
    invalid = new Set<number>();
  for (let i = 0; i < count; i++) {
    const root = find(i),
      list = groups.get(root) ?? [];
    list.push(i);
    groups.set(root, list);
  }
  for (const owners of edges.values())
    if (owners.length !== 2 || owners[0].sign === owners[1].sign)
      invalid.add(find(owners[0].face));
  const result: ClosedPart[] = [];
  for (const [root, ids] of groups) {
    if (invalid.has(root) || ids.length < 4 || ids.length > 24) continue;
    const vertices = [...new Set(ids.flatMap((i) => faces[i]))].map(
      (i) => points[i],
    );
    const bounds = new THREE.Box3().setFromPoints(vertices),
      center = bounds.getCenter(new THREE.Vector3());
    const epsilon =
      Math.max(1, bounds.getSize(new THREE.Vector3()).length()) * 1e-9;
    const planes: THREE.Plane[] = [];
    let valid = true;
    for (const i of ids) {
      const [a, b, c] = faces[i].map((k) => points[k]);
      const normal = new THREE.Vector3()
        .subVectors(b, a)
        .cross(new THREE.Vector3().subVectors(c, a));
      if (normal.lengthSq() === 0) {
        valid = false;
        break;
      }
      const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(
        normal.normalize(),
        a,
      );
      // Reject inward winding, nonconvex parts and zero-volume sheets. All
      // vertices must be on or behind every outward face plane.
      if (
        plane.distanceToPoint(center) >= -epsilon ||
        vertices.some((p) => plane.distanceToPoint(p) > epsilon)
      ) {
        valid = false;
        break;
      }
      planes.push(plane);
    }
    if (valid) result.push({ faces: ids, planes, bounds });
  }
  return result;
}

/** Skip hidden exit faces of proven closed solids only when shadows are off.
 * Prepare before first GPU upload. One index buffer and one draw per mesh stay.
 */
export function createConvexCulling(root: THREE.Object3D) {
  const uses = new Map<THREE.BufferGeometry, number>();
  root.traverse((o) => {
    if (o instanceof THREE.Mesh)
      uses.set(o.geometry, (uses.get(o.geometry) ?? 0) + 1);
  });
  const records: {
    mesh: THREE.Mesh;
    index: THREE.BufferAttribute;
    original: THREE.TypedArray;
    hidden: Uint8Array;
    parts: ClosedPart[];
    active: boolean;
  }[] = [];
  root.traverse((object) => {
    if (
      !(object instanceof THREE.Mesh) ||
      object instanceof THREE.SkinnedMesh ||
      object instanceof THREE.InstancedMesh
    )
      return;
    let owner: THREE.Object3D | null = object;
    while (owner && !owner.userData.layer) owner = owner.parent;
    const material = object.material,
      geometry = object.geometry;
    if (
      owner?.userData.layer !== 'buildings' ||
      uses.get(geometry) !== 1 ||
      !(material instanceof THREE.MeshStandardMaterial) ||
      material.transparent ||
      material.opacity !== 1 ||
      material.alphaMap ||
      material.alphaTest ||
      material.alphaHash ||
      material.displacementMap ||
      material.wireframe ||
      material.side === THREE.BackSide ||
      !material.depthTest ||
      !material.depthWrite ||
      material.depthFunc !== THREE.LessEqualDepth ||
      material.stencilWrite ||
      material.clippingPlanes?.length ||
      geometry.groups.length ||
      Object.keys(geometry.morphAttributes).length ||
      geometry.drawRange.start !== 0 ||
      geometry.drawRange.count !== Infinity ||
      !geometry.index
    )
      return;
    const parts = closedConvexParts(geometry);
    if (!parts.length) return;
    geometry.index.setUsage(THREE.DynamicDrawUsage);
    records.push({
      mesh: object,
      index: geometry.index,
      original: geometry.index.array.slice(),
      hidden: new Uint8Array(geometry.index.count / 3),
      parts,
      active: false,
    });
  });
  const eye = new THREE.Vector3(),
    direction = new THREE.Vector3(),
    localEye = new THREE.Vector3();
  const inverse = new THREE.Matrix4(),
    projection = new THREE.Matrix4(),
    frustum = new THREE.Frustum(),
    sphere = new THREE.Sphere();
  return {
    meshes: records.length,
    parts: records.reduce((n, r) => n + r.parts.length, 0),
    update(camera: THREE.PerspectiveCamera, enabled: boolean) {
      camera.updateMatrixWorld();
      camera.getWorldPosition(eye);
      camera.getWorldDirection(direction);
      frustum.setFromProjectionMatrix(
        projection.multiplyMatrices(
          camera.projectionMatrix,
          camera.matrixWorldInverse,
        ),
      );
      for (const r of records) {
        if (!enabled) {
          if (!r.active) continue;
          r.index.array.set(r.original);
          r.index.clearUpdateRanges();
          r.index.addUpdateRange(0, r.original.length);
          r.index.needsUpdate = true;
          r.mesh.geometry.setDrawRange(0, Infinity);
          r.hidden.fill(0);
          r.active = false;
          continue;
        }
        let visible = true,
          parent: THREE.Object3D | null = r.mesh;
        while (parent) {
          visible &&= parent.visible;
          parent = parent.parent;
        }
        if (!visible) continue;
        r.mesh.updateWorldMatrix(true, false);
        if (r.mesh.frustumCulled && !frustum.intersectsObject(r.mesh)) continue;
        localEye
          .copy(eye)
          .applyMatrix4(inverse.copy(r.mesh.matrixWorld).invert());
        let changed = false;
        for (const part of r.parts) {
          part.bounds
            .getBoundingSphere(sphere)
            .applyMatrix4(r.mesh.matrixWorld);
          // A near-plane cut can expose exit faces. So can a camera inside a
          // solid: preserve both sides whenever either situation is possible.
          const fullSolid =
            !part.bounds.containsPoint(localEye) &&
            direction.dot(sphere.center.sub(eye)) - sphere.radius > camera.near;
          for (let i = 0; i < part.faces.length; i++) {
            const face = part.faces[i];
            const hidden = Number(
              fullSolid && part.planes[i].distanceToPoint(localEye) < -1e-6,
            );
            if (r.hidden[face] !== hidden) {
              r.hidden[face] = hidden;
              changed = true;
            }
          }
        }
        if (!changed) continue;
        let length = 0;
        for (let i = 0; i < r.hidden.length; i++) {
          if (r.hidden[i]) continue;
          for (let k = 0; k < 3; k++)
            r.index.array[length++] = r.original[i * 3 + k];
        }
        r.mesh.geometry.setDrawRange(0, length);
        if (length) {
          r.index.clearUpdateRanges();
          r.index.addUpdateRange(0, length);
          r.index.needsUpdate = true;
        }
        r.active = true;
      }
    },
  };
}
