import {
  BufferAttribute,
  Color,
  Mesh,
  MeshStandardMaterial,
  Vector3,
  type Object3D,
} from 'three';
import type { Building } from './types';

const FACADES = [
  [1.04, 0.99, 0.94], // living: warm limestone
  [0.98, 1.015, 1.04], // teaching: soft cool mineral
  [1.015, 1.01, 0.985], // administration/laboratory: pale neutral
  [1.03, 1.0, 0.97], // other: light sand
];
const ROOFS = [
  [1.02, 1.025, 1.03],
  [1.055, 1.025, 0.97],
  [0.97, 0.995, 1.01],
];
const WALL_MATERIALS = new Set([
  'stone',
  'stoneWarm',
  'stoneCool',
  'livingWarm',
  'livingCool',
  'pink',
]);
function hash(value: string) {
  let h = 2166136261;
  for (const c of value) h = Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0;
  return h;
}

/** Classification is presentation-only; does not claim verified facade colours. */
export function facadePalette(building: Pick<Building, 'category' | 'name'>) {
  if (building.category === 'living' || /宿舍|公寓/.test(building.name))
    return 0;
  if (/行政|办公|实验|科研/.test(building.name)) return 2;
  return building.category === 'academic' ? 1 : 3;
}

export function createPalette(buildings: Building[]) {
  const cells = new Map<string, Building[]>();
  for (const b of buildings) {
    if (!b.insideCampus || b.landmark) continue;
    const [x0, y0, x1, y1] = b.bounds;
    for (let x = Math.floor((x0 - 3) / 64); x <= Math.floor((x1 + 3) / 64); x++)
      for (
        let y = Math.floor((y0 - 3) / 64);
        y <= Math.floor((y1 + 3) / 64);
        y++
      ) {
        const key = `${x},${y}`;
        if (!cells.has(key)) cells.set(key, []);
        cells.get(key)!.push(b);
      }
  }
  const styled = new WeakSet<MeshStandardMaterial>();
  const smoothed = new WeakSet();
  return {
    terrain(mesh: Mesh) {
      if (
        !(mesh.material instanceof MeshStandardMaterial) ||
        mesh.material.name !== 'grass' ||
        smoothed.has(mesh.geometry)
      )
        return;
      smoothed.add(mesh.geometry);
      const positions = mesh.geometry.getAttribute('position');
      const normals = mesh.geometry.getAttribute('normal');
      if (!normals) return;
      const groups = new Map<string, Vector3>();
      const keys: string[] = [];
      const normal = new Vector3();
      for (let i = 0; i < positions.count; i++) {
        const key = `${positions.getX(i).toFixed(2)},${positions.getY(i).toFixed(2)},${positions.getZ(i).toFixed(2)}`;
        keys.push(key);
        if (!groups.has(key)) groups.set(key, new Vector3());
        groups.get(key)!.add(normal.fromBufferAttribute(normals, i));
      }
      for (const value of groups.values()) value.normalize();
      for (let i = 0; i < positions.count; i++) {
        const n = groups.get(keys[i])!;
        normals.setXYZ(i, n.x, n.y, n.z);
      }
      normals.needsUpdate = true;
    },
    surface(material: MeshStandardMaterial) {
      if (styled.has(material)) return;
      styled.add(material);
      if (material.name === 'grass') material.color.setRGB(1.02, 0.97, 0.83);
      if (material.name === 'path') material.color.setRGB(1.13, 1.13, 1.1);
      if (material.name === 'water') material.color.set('#397b83');
    },
    buildings(root: Object3D, key: string) {
      root.updateMatrixWorld(true);
      const materials = new Map<MeshStandardMaterial, MeshStandardMaterial>();
      const point = new Vector3();
      const tint = new Color();
      root.traverse((object) => {
        if (
          !(object instanceof Mesh) ||
          !(object.material instanceof MeshStandardMaterial)
        )
          return;
        let ordinary = key.startsWith('chunk-');
        for (let node: Object3D | null = object; node; node = node.parent) {
          if (node.userData.landmark || node.name.startsWith('landmark-'))
            return;
          if (node.name.startsWith('chunk-')) ordinary = true;
        }
        const material = object.material;
        const roof = material.name === 'paleRoof';
        if (!ordinary || (!roof && !WALL_MATERIALS.has(material.name))) return;
        const positions = object.geometry.getAttribute('position');
        const colors = new Float32Array(positions.count * 3);
        for (let i = 0; i < positions.count; i++) {
          point
            .fromBufferAttribute(positions, i)
            .applyMatrix4(object.matrixWorld);
          const x = point.x,
            y = -point.z;
          const candidates =
            cells.get(`${Math.floor(x / 64)},${Math.floor(y / 64)}`) ?? [];
          const building = candidates.find(
            (b) =>
              x >= b.bounds[0] - 2 &&
              x <= b.bounds[2] + 2 &&
              y >= b.bounds[1] - 2 &&
              y <= b.bounds[3] + 2,
          );
          if (building) {
            const seed = hash(building.id);
            const rgb = roof
              ? ROOFS[seed % ROOFS.length]
              : FACADES[facadePalette(building)];
            tint
              .setRGB(rgb[0], rgb[1], rgb[2])
              .multiplyScalar(0.985 + (seed % 31) / 1000);
          } else tint.setRGB(1, 1, 1);
          tint.toArray(colors, i * 3);
        }
        object.geometry.setAttribute('color', new BufferAttribute(colors, 3));
        let clone = materials.get(material);
        if (!clone) {
          clone = material.clone();
          clone.vertexColors = true;
          materials.set(material, clone);
        }
        object.material = clone;
      });
      // Originals may also be used by unchanged meshes; their lifecycle stays with the GLTF root.
      const used = new Set<MeshStandardMaterial>();
      root.traverse((o) => {
        if (o instanceof Mesh)
          for (const m of Array.isArray(o.material) ? o.material : [o.material])
            used.add(m);
      });
      for (const original of materials.keys())
        if (!used.has(original)) original.dispose();
    },
  };
}
