import { Box3, Sphere, Vector3, type Object3D } from 'three';
import type { Building, Landmark, LandmarkView, ViewportFrame } from './types';

/** Opt-in measurement mode: retain a shared pose when starting an orbit. */
export function benchmarkOrbitEnabled(search: string) {
  const params = new URLSearchParams(search);
  return params.has('debug') && params.get('benchmark') === 'fixed-orbit';
}

/** WGS84 bearings: north is -Z, east is +X in the web scene. */
export function landmarkDirection(
  place: Landmark,
  view: LandmarkView,
  architecture?: Building['architecture'],
) {
  const bearing = architecture
    ? (place.id === 'huicui' ? 0 : Math.PI) - architecture.angle
    : ((place.frontBearing ?? 180) * Math.PI) / 180;
  if (view === 'top') return new Vector3(0, 1, 0.025).normalize();
  if (view === 'oblique')
    return new Vector3(...(place.cameraOffset ?? [-0.5, 0.66, 1])).normalize();
  if (place.id === 'new-east-gate' && view === 'entrance')
    return new Vector3(Math.sin(bearing), 0.12, -Math.cos(bearing)).normalize();
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
  return fitPoints(boxCorners(box), direction, frame, viewport, fov);
}

function boxCorners(box: Box3) {
  return [box.min.x, box.max.x].flatMap((x) =>
    [box.min.y, box.max.y].flatMap((y) =>
      [box.min.z, box.max.z].map((z) => new Vector3(x, y, z)),
    ),
  );
}

/** Preserve the irregular campus outline and every roof, without fitting empty corners. */
export function campusOverviewPoints(
  rings: number[][][],
  buildings: Building[],
  landmarks: Landmark[],
) {
  return [
    ...rings.flat().map(([x, y, elevation]) => new Vector3(x, elevation, -y)),
    ...buildings.flatMap((b) =>
      boxCorners(
        new Box3(
          new Vector3(b.bounds[0], b.elevation, -b.bounds[3]),
          new Vector3(b.bounds[2], b.elevation + b.height + 10, -b.bounds[1]),
        ),
      ),
    ),
    ...landmarks.flatMap((l) => boxCorners(landmarkBox(l))),
  ];
}

export function fitPoints(
  points: Vector3[],
  direction: Vector3,
  frame: ViewportFrame,
  viewport: { width: number; height: number },
  fov = 41,
) {
  const target = new Box3().setFromPoints(points).getCenter(new Vector3());
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
  for (const point of points) {
    const relative = point.clone().sub(target);
    distance = Math.max(
      distance,
      relative.dot(back) + Math.abs(relative.dot(right)) / usableX,
      relative.dot(back) + Math.abs(relative.dot(up)) / usableY,
    );
  }
  return { target, position: target.clone().addScaledVector(back, distance) };
}

export function landmarkBox(place: Landmark) {
  const site = place.siteBoundsOffset?.map((v, i) => v + place.center[i % 2]);
  const [x0, y0, x1, y1] = site
    ? [
        Math.min(site[0], place.bounds[0]),
        Math.min(site[1], place.bounds[1]),
        Math.max(site[2], place.bounds[2]),
        Math.max(site[3], place.bounds[3]),
      ]
    : place.bounds;
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
  if (place.id === 'new-east-gate' && !rear) {
    // Keep both short enclosure edges, the tower and pedestrian canopy together.
    // The generic entrance crop moves out into the road and fits too much sky.
    return new Box3().setFromCenterAndSize(
      new Vector3(
        place.center[0] + 0.55,
        place.elevation + 5.3,
        -place.center[1] - 2.25,
      ),
      new Vector3(21.3, 11.4, 13),
    );
  }
  if (place.id === 'huicui' && architecture && !rear) {
    const { origin, angle } = architecture;
    const localY = 34;
    return new Box3().setFromCenterAndSize(
      new Vector3(
        origin[0] - Math.sin(angle) * localY,
        place.elevation + 3,
        -(origin[1] + Math.cos(angle) * localY),
      ),
      new Vector3(22, 8, 10),
    );
  }
  if (place.id === 'teaching-six' && architecture) {
    const { origin, angle } = architecture;
    const y = rear ? 30 : -30;
    return new Box3().setFromCenterAndSize(
      new Vector3(
        origin[0] - Math.sin(angle) * y,
        place.elevation + 3,
        -(origin[1] + Math.cos(angle) * y),
      ),
      new Vector3(34, 9, 13),
    );
  }
  if (place.id === 'teaching-ten' && architecture) {
    const { origin, angle } = architecture;
    const localY = -19.4;
    return new Box3().setFromCenterAndSize(
      new Vector3(
        origin[0] - Math.sin(angle) * localY,
        place.elevation + 3.5,
        -(origin[1] + Math.cos(angle) * localY),
      ),
      new Vector3(18, 8, 13),
    );
  }
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

type Pose = { target: Vector3; position: Vector3 };
type Viewport = { width: number; height: number };
export type MapView = 'top' | 'tilt' | 'north' | 'zoomIn' | 'zoomOut';

/** Padded box of an ordinary building, from its footprint and height. */
export function buildingBox(b: Building) {
  const [x0, y0, x1, y1] = b.bounds;
  return new Box3(
    new Vector3(x0 - 4, b.elevation - 0.5, -y1 - 4),
    new Vector3(x1 + 4, b.elevation + b.height + 4, -y0 + 4),
  );
}

/** Ordinary buildings have a top and an oblique view only. */
export function buildingPose(
  b: Building,
  view: LandmarkView,
  frame: ViewportFrame,
  viewport: Viewport,
  fov?: number,
) {
  return fitBox(
    buildingBox(b),
    view === 'top'
      ? new Vector3(0, 1, 0.025).normalize()
      : new Vector3(-0.5, 0.66, 1).normalize(),
    frame,
    viewport,
    fov,
  );
}

/**
 * Frames a landmark from a named view. The loaded model, when present, gives
 * the bounds; full oblique views also keep the label above small gates.
 */
export function landmarkPose(
  place: Landmark,
  view: LandmarkView,
  {
    model,
    anchor,
    architecture,
  }: {
    model?: Object3D;
    anchor: Vector3;
    architecture?: Building['architecture'];
  },
  frame: ViewportFrame,
  viewport: Viewport,
  fov?: number,
): Pose {
  let box = model ? new Box3().setFromObject(model) : landmarkBox(place);
  if (view === 'oblique')
    box.expandByPoint(anchor.clone().add(new Vector3(0, 5, 0)));
  if (view === 'entrance' || view === 'rear-entrance')
    box = entranceBox(place, box, view === 'rear-entrance', architecture);
  const framing = fitBox(
    box,
    landmarkDirection(place, view, architecture),
    frame,
    viewport,
    fov,
  );
  return view === 'entrance' ? bridgeEntrancePose(place, framing) : framing;
}

/** A sphere fits through a complete rotation, including the wider sides. */
export function orbitPose(
  place: Landmark,
  model: Object3D | undefined,
  frame: ViewportFrame,
  viewport: Viewport,
) {
  const box = model ? new Box3().setFromObject(model) : landmarkBox(place);
  const sphere = box.getBoundingSphere(new Sphere());
  return fitBox(
    new Box3().setFromCenterAndSize(
      sphere.center,
      new Vector3().setScalar(sphere.radius * 2),
    ),
    landmarkDirection(place, 'oblique'),
    frame,
    viewport,
  );
}

/** The whole campus; the measured boundary replaces the fixed box once loaded. */
export function overviewPose(
  points: Vector3[] | null,
  frame: ViewportFrame,
  viewport: Viewport,
) {
  const direction = new Vector3(0.55, 1.1, 1);
  return points
    ? fitPoints(points, direction, frame, viewport)
    : fitBox(
        new Box3(new Vector3(-920, -10, -1260), new Vector3(1000, 65, 1300)),
        direction,
        frame,
        viewport,
      );
}

/** Changes the viewing angle or zoom around the current target. */
export function viewPose(
  view: MapView,
  target: Vector3,
  position: Vector3,
  distance: { min: number; max: number },
): Pose {
  const t = target.clone();
  const offset = position.clone().sub(t);
  if (view === 'top')
    return {
      target: t,
      position: t.clone().add(new Vector3(0, offset.length(), 0.01)),
    };
  if (view === 'tilt')
    return {
      target: t,
      position: t
        .clone()
        .add(
          new Vector3(-0.45, 0.66, 0.8)
            .normalize()
            .multiplyScalar(offset.length()),
        ),
    };
  if (view === 'north')
    return {
      target: t,
      position: t
        .clone()
        .add(new Vector3(0, offset.y, Math.hypot(offset.x, offset.z))),
    };
  const factor = view === 'zoomIn' ? 0.75 : 1.33;
  const d = Math.max(
    distance.min,
    Math.min(distance.max, offset.length() * factor),
  );
  return {
    target: t,
    position: t.clone().add(offset.normalize().multiplyScalar(d)),
  };
}
