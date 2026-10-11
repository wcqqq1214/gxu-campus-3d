import { Box3, Mesh, Vector3, type Object3D } from 'three';
import type { Landmark } from './types';

/** Optional override is in source east/north/up metres, not Three's x/y/z. */
export function landmarkLabelAnchor(landmark: Landmark, model?: Object3D) {
  if (landmark.labelAnchor) {
    const [east, north, up] = landmark.labelAnchor;
    return new Vector3(east, up, -north);
  }
  const fallback = new Vector3(
    (landmark.bounds[0] + landmark.bounds[2]) / 2,
    landmark.elevation + landmark.height + 0.6,
    -(landmark.bounds[1] + landmark.bounds[3]) / 2,
  );
  if (!model) return fallback;
  model.updateWorldMatrix(true, true);
  const all = new Box3().setFromObject(model);
  if (all.isEmpty()) return fallback;
  const roof = new Box3();
  const point = new Vector3();
  // Ignore entry aprons, landscaping and low wings when finding the body centre.
  const threshold = all.max.y - Math.max(3, landmark.height * 0.3);
  model.traverse((o) => {
    if (!(o instanceof Mesh)) return;
    const positions = o.geometry.getAttribute('position');
    for (let i = 0; i < positions.count; i++) {
      point.fromBufferAttribute(positions, i).applyMatrix4(o.matrixWorld);
      if (point.y >= threshold) roof.expandByPoint(point);
    }
  });
  const box = roof.isEmpty() ? all : roof;
  return new Vector3(
    (box.min.x + box.max.x) / 2,
    box.max.y + 0.6,
    (box.min.z + box.max.z) / 2,
  );
}
