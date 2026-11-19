import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { asset, type ModelManifest } from './boot';
import type { createNightStyle } from './night';
import { disposeObject } from './resources';
import type { StreamAsset } from './streaming';
import {
  orderTreeGroup,
  treeAppearance,
  treeCrownWidthFactor,
  treeInstanceCounts,
  treeElevation,
  treeRotation,
} from './vegetation';

interface Terrain {
  bounds: number[];
  cols: number;
  rows: number;
  heights: number[];
}

/**
 * Instanced campus trees. The far set loads after the base model; the near
 * set replaces it within 500 m when quality allows. Templates are merged per
 * type and instanced per 450 m sector so each sector can be culled.
 */
export function createSceneTrees({
  scene,
  lifetime,
  nightStyle,
  night,
  load,
  onLoaded,
  onSettled,
}: {
  scene: THREE.Scene;
  /** Aborted when the scene is disposed. */
  lifetime: AbortSignal;
  nightStyle: ReturnType<typeof createNightStyle>;
  night: () => boolean;
  load: (
    asset: StreamAsset,
    key: string,
    signal: AbortSignal,
  ) => Promise<{ scene: THREE.Group }>;
  /** Instances were added; the scene reapplies density and layers. */
  onLoaded: () => void;
  onSettled: () => void;
}) {
  let root: THREE.Group | null = null;
  let nearReady = false;
  let nearFailed = false;
  let farFailed = false;
  let loading = false;
  let data: { rows: number[][]; terrain: Terrain } | null = null;
  async function json<T>(path: string, name: string) {
    const response = await fetch(asset(path), { signal: lifetime });
    if (!response.ok) throw new Error(name);
    return response.json() as Promise<T>;
  }
  async function loadTrees(
    manifest: ModelManifest,
    near = false,
    signal = lifetime,
  ) {
    if ((near ? nearReady || !manifest.treesNear : root) || loading) return;
    loading = true;
    try {
      const [all, terrain] = data
        ? [data.rows, data.terrain]
        : await Promise.all([
            json<number[][]>('data/vegetation.json', 'vegetation'),
            json<Terrain>('data/terrain.json', 'terrain'),
          ]);
      if (lifetime.aborted) return;
      data = { rows: all, terrain };
      const g = await load(
        near ? manifest.treesNear! : manifest.trees,
        near ? 'trees-near' : 'trees',
        signal,
      );
      if (!root) {
        root = new THREE.Group();
        root.name = 'vegetation';
        root.userData.layer = 'vegetation';
        scene.add(root);
      }
      const parts: THREE.Mesh[] = [];
      g.scene.traverse((o) => {
        if (o instanceof THREE.Mesh) parts.push(o);
      });
      const priority = new Set(
        (manifest.treePriorityPositions ?? []).map(([x, y]) => `${x},${y}`),
      );
      for (const typ of new Set(all.map((row) => row[3]))) {
        const partsForType = parts.filter((o) => {
          let p: THREE.Object3D | null = o;
          while (p) {
            if (
              p.userData.template === typ ||
              p.name === `Tree-template-${typ}`
            )
              return true;
            p = p.parent;
          }
          return false;
        });
        if (!partsForType.length) continue;
        const geometries = partsForType.map((part) => {
          const geometry = part.geometry.index
            ? part.geometry.toNonIndexed()
            : part.geometry.clone();
          const material = (
            Array.isArray(part.material) ? part.material[0] : part.material
          ) as THREE.MeshStandardMaterial;
          const color = material.color;
          const colors = new Float32Array(
            geometry.getAttribute('position').count * 3,
          );
          for (let i = 0; i < colors.length; i += 3) {
            colors[i] = color.r;
            colors[i + 1] = color.g;
            colors[i + 2] = color.b;
          }
          geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
          geometry.deleteAttribute('uv');
          return geometry;
        });
        const geometry = mergeGeometries(geometries)!;
        geometries.forEach((g) => g.dispose());
        const material = new THREE.MeshStandardMaterial({
          name: 'treeCanopy',
          vertexColors: true,
          roughness: 0.94,
          side: THREE.DoubleSide,
        });
        const sectors = new Map<string, number[][]>();
        for (const row of all) {
          if (row[3] !== typ) continue;
          const key = `${Math.floor(row[0] / 450)},${Math.floor(row[1] / 450)}`;
          if (!sectors.has(key)) sectors.set(key, []);
          sectors.get(key)!.push(row);
        }
        for (const [sector, sectorRows] of sectors) {
          const { rows, priorityCount } = orderTreeGroup(sectorRows, priority);
          const inst = new THREE.InstancedMesh(geometry, material, rows.length);
          const transform = new THREE.Object3D();
          rows.forEach((row, i) => {
            const [x, y, h] = row;
            transform.position.set(x, treeElevation(row, terrain), -y);
            transform.rotation.set(0, treeRotation(x, y), 0);
            const appearance = treeAppearance(x, y);
            const width = (treeCrownWidthFactor(x, y) * appearance.width * h) / 9;
            transform.scale.set(
              width,
              (appearance.height * h) / 9,
              width,
            );
            transform.updateMatrix();
            inst.setMatrixAt(i, transform.matrix);
            inst.setColorAt(i, new THREE.Color(...appearance.tint));
          });
          nightStyle.apply(inst, night());
          inst.instanceMatrix.needsUpdate = true;
          inst.computeBoundingSphere();
          inst.castShadow = true;
          inst.receiveShadow = true;
          inst.userData.sector = sector;
          inst.userData.fullCount = rows.length;
          inst.userData.priorityCount = priorityCount;
          inst.userData.lod = near ? 1 : 0;
          inst.userData.center = new THREE.Vector3(
            rows.reduce((sum, r) => sum + r[0], 0) / rows.length,
            0,
            -rows.reduce((sum, r) => sum + r[1], 0) / rows.length,
          );
          root.add(inst);
        }
      }
      disposeObject(g.scene);
      if (near) nearReady = true;
      // Materials and geometry are shared with the instanced meshes and disposed once during teardown.
      onLoaded();
    } catch (error) {
      if (!lifetime.aborted && !signal.aborted) {
        if (near) nearFailed = true;
        else farFailed = true;
      }
      throw error;
    } finally {
      loading = false;
      onSettled();
    }
  }
  return {
    get loaded() {
      return Boolean(root);
    },
    /** Far trees failed, or near trees failed while they were wanted. */
    failed(nearWanted: boolean) {
      return farFailed || (nearFailed && nearWanted);
    },
    load: (manifest: ModelManifest) => loadTrees(manifest),
    /** The near-tree loader while it still has work to do, for the detail queue. */
    nearLoader(manifest: ModelManifest | null) {
      return root &&
        manifest?.treesNear &&
        !nearReady &&
        !nearFailed &&
        !loading
        ? (signal: AbortSignal) => loadTrees(manifest, true, signal)
        : undefined;
    },
    resetFailures() {
      nearFailed = false;
      farFailed = false;
    },
    setVisible(visible: boolean) {
      if (root) root.visible = visible;
    },
    /** Quality changes: instance density and whether near trees stay resident. */
    configure(density: number, near: boolean) {
      if (!near && root && nearReady) {
        const retired = new THREE.Group();
        for (const child of root.children.slice())
          if (child.userData.lod === 1) retired.add(child);
        disposeObject(retired, [scene]);
        nearReady = false;
      }
      const sectors = new Map<string, THREE.InstancedMesh[]>();
      for (const mesh of root?.children ?? []) {
        if (!(mesh instanceof THREE.InstancedMesh)) continue;
        const key = `${mesh.userData.lod}/${mesh.userData.sector}`;
        if (!sectors.has(key)) sectors.set(key, []);
        sectors.get(key)!.push(mesh);
      }
      for (const meshes of sectors.values()) {
        const counts = treeInstanceCounts(
          meshes.map(({ userData }) => ({
            total: userData.fullCount,
            priority: userData.priorityCount,
          })),
          density,
        );
        meshes.forEach((mesh, i) => {
          mesh.count = counts[i];
        });
      }
    },
    /** Swaps sectors between near and far sets; returns whether any visibility changed. */
    updateLOD(camera: THREE.Vector3, near: boolean) {
      let changed = false;
      for (const o of root?.children ?? []) {
        const close =
          nearReady && near && camera.distanceTo(o.userData.center) < 500;
        const visible = o.userData.lod === 1 ? close : !close;
        if (o.visible !== visible) changed = true;
        o.visible = visible;
      }
      return changed;
    },
  };
}
