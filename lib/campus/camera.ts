import { Box3, Vector3 } from 'three';
import type { Building, Landmark, LandmarkView, ViewportFrame } from './types';

/** WGS84 bearings: north is -Z, east is +X in the web scene. */
export function landmarkDirection(
  place: Landmark,
  view: LandmarkView,
  architecture?: Building['architecture'],
) {
  const bearing = architecture
    ? Math.PI - architecture.angle
    : ((place.frontBearing ?? 180) * Math.PI) / 180;
  if (view === 'top') return new Vector3(0, 1, 0.025).normalize();
  if (view === 'oblique')
    return new Vector3(...(place.cameraOffset ?? [-0.5, 0.66, 1])).normalize();
  const reverse = view === 'back' || view === 'rear-entrance' ? -1 : 1;
  return new Vector3(
    Math.sin(bearing) * reverse,
    view === 'entrance' || view === 'rear-entrance'
      ? place.placeKind === 'bridge'
        ? 0.09
        : 0.48
      : 0.32,
    -Math.cos(bearing) * reverse,
  ).normalize();
}

/** Fit all eight corners into the unobscured portion of a perspective viewport. */
export function fitBox(
  box: Box3,
  direction: Vector3,
  frame: ViewportFrame,
  viewport: { width: number; height: number },
  fov = 41,
) {
  const target = box.getCenter(new Vector3());
  const back = direction.clone().normalize();
  const right = new Vector3()
    .crossVectors(new Vector3(0, 1, 0), back)
    .normalize();
  const up = new Vector3().crossVectors(back, right).normalize();
  const tanY = Math.tan((fov * Math.PI) / 360);
  const usableX =
    ((tanY * (viewport.width / viewport.height) * frame.width) /
      viewport.width) *
    0.86;
  const usableY = ((tanY * frame.height) / viewport.height) * 0.86;
  let distance = 18;
  for (const x of [box.min.x, box.max.x])
    for (const y of [box.min.y, box.max.y])
      for (const z of [box.min.z, box.max.z]) {
        const relative = new Vector3(x, y, z).sub(target);
        distance = Math.max(
          distance,
          relative.dot(back) + Math.abs(relative.dot(right)) / usableX,
          relative.dot(back) + Math.abs(relative.dot(up)) / usableY,
        );
      }
  return { target, position: target.clone().addScaledVector(back, distance) };
}

export function landmarkBox(place: Landmark) {
  const [x0, y0, x1, y1] = place.bounds;
  return new Box3(
    new Vector3(x0 - 3, place.elevation - 0.5, -y1 - 3),
    new Vector3(x1 + 3, place.elevation + place.height + 3, -y0 + 3),
  );
}

/** Follow the curved ramp so a narrow viewport cannot put the eye behind its wall. */
export function bridgeEntrancePose(
  place: Landmark,
  pose: { target: Vector3; position: Vector3 },
) {
  if (place.placeKind !== 'bridge' || !place.approachPath) return pose;
  const intended = pose.position.clone();
  if (intended.distanceTo(pose.target) < 30)
    intended
      .copy(pose.target)
      .addScaledVector(pose.position.clone().sub(pose.target).normalize(), 30);
  let nearest = Infinity;
  const position = intended.clone();
  const path = place.approachPath;
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1],
      b = path[i];
    const dx = b[0] - a[0],
      dy = b[1] - a[1];
    const lengthSq = dx * dx + dy * dy;
    if (!lengthSq) continue;
    const t = Math.max(
      0,
      Math.min(
        1,
        ((intended.x - a[0]) * dx + (-intended.z - a[1]) * dy) / lengthSq,
      ),
    );
    const x = a[0] + dx * t,
      y = a[1] + dy * t;
    const distance = Math.hypot(intended.x - x, intended.z + y);
    if (distance >= nearest) continue;
    nearest = distance;
    position.set(x, Math.max(intended.y, a[2] + (b[2] - a[2]) * t + 2.2), -y);
  }
  // Keep the pose within OrbitControls' 85.5 degree polar limit.
  position.y = Math.max(
    position.y,
    pose.target.y +
      0.08 * Math.hypot(position.x - pose.target.x, position.z - pose.target.z),
  );
  return { target: pose.target, position };
}

/** Entrance crops use the modeled front axis; the full-building views retain the entire box. */
export function entranceBox(
  place: Landmark,
  box: Box3,
  rear: boolean,
  architecture?: Building['architecture'],
) {
  if (place.placeKind === 'sculpture') {
    return new Box3(
      new Vector3(
        place.center[0] - 8,
        place.elevation - 0.5,
        -place.center[1] - 7,
      ),
      new Vector3(
        place.center[0] + 8,
        place.elevation + place.height + 3,
        -place.center[1] + 7,
      ),
    );
  }
  if (place.placeKind === 'bridge' && place.portalCenter) {
    const forward = landmarkDirection(place, 'front').setY(0).normalize();
    // Crop the opening rather than an 18 m cube. A deep cube pushes a portrait
    // camera beyond the curved ramp, where the retaining wall obscures the view.
    return new Box3().setFromCenterAndSize(
      new Vector3(place.center[0], place.elevation + 2.7, -place.center[1]),
      new Vector3(
        Math.abs(forward.z) * 8 + Math.abs(forward.x) * 2,
        5,
        Math.abs(forward.x) * 8 + Math.abs(forward.z) * 2,
      ),
    );
  }
  const forward = landmarkDirection(
    place,
    rear ? 'back' : 'front',
    architecture,
  )
    .setY(0)
    .normalize();
  const center = box.getCenter(new Vector3());
  const size = box.getSize(new Vector3());
  const reach = Math.min(
    Math.abs(forward.x) > 0.001 ? size.x / 2 / Math.abs(forward.x) : Infinity,
    Math.abs(forward.z) > 0.001 ? size.z / 2 / Math.abs(forward.z) : Infinity,
  );
  center.addScaledVector(forward, reach * 0.9);
  center.y = place.elevation + Math.min(6, place.height * 0.3);
  // Library doors are offset from the catalogue centroid; use its modeled local origin.
  if (place.id === 'library' && architecture) {
    const { angle, origin } = architecture;
    const localY = rear ? 34 : -42;
    center.set(
      origin[0] - Math.sin(angle) * localY,
      place.elevation + 4.3,
      -(origin[1] + Math.cos(angle) * localY),
    );
  }
  const width =
    place.id === 'library'
      ? rear
        ? 23
        : 34
      : Math.max(16, Math.min(38, Math.max(size.x, size.z) * 0.45));
  return new Box3().setFromCenterAndSize(
    center,
    new Vector3(width, Math.min(16, place.height + 3), width * 0.35),
  );
}
