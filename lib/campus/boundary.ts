import { Group } from 'three';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';

export interface CampusBoundary {
  rings: number[][][];
  note: string;
  sourceUrl: string;
  snapshotAt: string;
}

/** An illustrative overlay, not a fence or a navigable physical surface. */
export function createBoundary(data: CampusBoundary) {
  if (!Array.isArray(data.rings) || !data.rings.length)
    throw new Error('boundary');
  if (
    data.rings.some(
      (ring) =>
        !Array.isArray(ring) ||
        ring.length < 4 ||
        ring.some(
          (p) =>
            !Array.isArray(p) ||
            p.length !== 3 ||
            p.some((n) => !Number.isFinite(n)),
        ),
    )
  )
    throw new Error('boundary ring');
  const root = new Group();
  root.name = '校园大致边界';
  const material = new LineMaterial({
    color: '#ffffff',
    linewidth: 2,
    transparent: true,
    opacity: 0.95,
    depthTest: true,
    depthWrite: false,
    toneMapped: false,
  });
  for (const ring of data.rings) {
    const geometry = new LineGeometry();
    geometry.setPositions(ring.flatMap(([x, y, z]) => [x, z, -y]));
    const line = new Line2(geometry, material);
    line.renderOrder = 20;
    line.frustumCulled = false;
    root.add(line);
  }
  return root;
}
