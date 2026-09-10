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
  const materials = [
    new LineMaterial({
      color: '#fff5d9',
      linewidth: 3,
      transparent: true,
      opacity: 0.35,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    }),
    new LineMaterial({
      color: '#ca852c',
      linewidth: 1.8,
      transparent: true,
      opacity: 1,
      dashed: true,
      dashSize: 45,
      gapSize: 24,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    }),
  ];
  for (const ring of data.rings) {
    const geometry = new LineGeometry();
    geometry.setPositions(ring.flatMap(([x, y, z]) => [x, z, -y]));
    materials.forEach((material, i) => {
      const line = new Line2(geometry, material);
      line.computeLineDistances();
      line.renderOrder = 20 + i;
      line.frustumCulled = false;
      root.add(line);
    });
  }
  return root;
}
