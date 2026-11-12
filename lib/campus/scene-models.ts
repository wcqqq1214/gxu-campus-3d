import * as THREE from 'three';
import { asset, modelUrl, type BasePrefetch } from './boot.ts';
import type { createContextStyle } from './context-style.ts';
import { pruneGroundTriangles } from './ground-triangles.ts';
import type { createNightStyle } from './night.ts';
import type { createPalette } from './palette.ts';
import { disposeObject } from './resources.ts';
import { batchStaticRoadSurfaces } from './road-batching.ts';
import { batchSportsSurfaces } from './sports-batching.ts';
import { fetchModel, type StreamAsset } from './streaming.ts';
import type { Landmark, Preset } from './types.ts';

export interface LoadProgress {
  label: string;
  name?: string;
  fraction: number;
}

/**
 * Downloads, decodes and styles campus models. Styling is sliced across
 * tasks so a large model does not block input; a preset change during those
 * slices is applied before the model is returned for publishing.
 */
export function createModelPipeline({
  loader,
  palette,
  contextStyle,
  nightStyle,
  landmarks,
  preset,
  lifetime,
  onProgress,
  schedule = (resume) => setTimeout(resume, 0),
}: {
  loader: {
    parseAsync: (
      buffer: ArrayBuffer,
      path: string,
    ) => Promise<{ scene: THREE.Group }>;
  };
  palette: ReturnType<typeof createPalette>;
  contextStyle: Pick<ReturnType<typeof createContextStyle>, 'apply'>;
  nightStyle: ReturnType<typeof createNightStyle>;
  landmarks: Landmark[];
  preset: () => Preset;
  /** Aborted when the scene is disposed. */
  lifetime: AbortSignal;
  /** Reports a model's download progress; null once it has finished or failed. */
  onProgress: (key: string, progress: LoadProgress | null) => void;
  /** Runs `resume` in a later task between styling slices. */
  schedule?: (resume: () => void) => void;
}) {
  let loadedBytes = 0;
  /** Night windows, lamp glass and the Time Gate follow the current preset. */
  function applyLighting(root: THREE.Object3D) {
    const night = preset() === 'night';
    root.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return;
      nightStyle.apply(o, night);
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (!(m instanceof THREE.MeshStandardMaterial)) continue;
        if (m.name === 'timeSilver' || m.name === 'timeLight') {
          m.emissive.set('#83b6e2');
          m.emissiveIntensity = night
            ? m.name === 'timeSilver'
              ? 0.16
              : 1.8
            : 0;
        }
      }
    });
  }
  function style(root: THREE.Object3D, refineTerrain = true) {
    root.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return;
      if (refineTerrain) palette.terrain(o);
      o.castShadow = true;
      o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (m instanceof THREE.MeshStandardMaterial) {
          palette.surface(m);
          contextStyle.apply(m);
          if (
            ['sportWhite', 'roadWhite', 'roadYellow', 'tactile'].includes(
              m.name,
            )
          ) {
            // Paint is a decal surface: bias its depth at oblique/distant views
            // as well as retaining geometric separation through Draco export.
            m.polygonOffset = true;
            m.polygonOffsetFactor = -2;
            m.polygonOffsetUnits = -2;
            o.castShadow = false;
          }
          if (m.name === 'water') {
            o.castShadow = false;
            m.roughness = 0.3;
            m.metalness = 0.28;
          }
          if (m.name === 'timeSilver') m.envMapIntensity = 1.5;
        }
      }
    });
    applyLighting(root);
  }
  async function load(
    a: StreamAsset,
    key = 'base',
    signal = lifetime,
    prefetched?: Pick<BasePrefetch, 'base' | 'onProgress'>,
  ) {
    const label =
      key === 'base'
        ? '正在加载校园'
        : key.startsWith('trees')
          ? '正在加载树木'
          : key.startsWith('landmark-')
            ? '正在加载{name}'
            : '正在加载周边细节';
    const name = key.startsWith('landmark-')
      ? (landmarks.find((l) => 'landmark-' + l.id === key)?.name ?? '地标')
      : undefined;
    const progress = (fraction: number) =>
      onProgress(key, { label, fraction, name });
    let unsubscribe: (() => void) | undefined;
    try {
      let buffer: ArrayBuffer;
      if (prefetched) {
        unsubscribe = prefetched.onProgress(progress);
        buffer = await prefetched.base;
      } else buffer = await fetchModel(modelUrl(a), a.bytes, signal, progress);
      signal.throwIfAborted();
      const gltf = await loader.parseAsync(buffer, asset('models/'));
      if (lifetime.aborted || signal.aborted) {
        disposeObject(gltf.scene);
        throw new DOMException('Request cancelled', 'AbortError');
      }
      loadedBytes += a.bytes;
      const yieldLoading = async () => {
        await new Promise<void>((resolve) => schedule(resolve));
        signal.throwIfAborted();
        if (lifetime.aborted)
          throw new DOMException('Scene disposed', 'AbortError');
      };
      try {
        if (key !== 'base') palette.buildings(gltf.scene, key);
        const styledPreset = preset();
        style(gltf.scene, key !== 'base');
        await yieldLoading();
        batchSportsSurfaces(gltf.scene);
        await yieldLoading();
        batchStaticRoadSurfaces(gltf.scene);
        await yieldLoading();
        if (key === 'base') pruneGroundTriangles(gltf.scene);
        // Preset changes during a yield cannot reach this unattached root.
        // Synchronize after the last yield, before the caller publishes it.
        if (preset() !== styledPreset) applyLighting(gltf.scene);
        return gltf;
      } catch (error) {
        // A cancelled detail must not leak a decoded root while yielding.
        disposeObject(gltf.scene);
        throw error;
      }
    } finally {
      unsubscribe?.();
      onProgress(key, null);
    }
  }
  return {
    load,
    applyLighting,
    get loadedBytes() {
      return loadedBytes;
    },
  };
}
