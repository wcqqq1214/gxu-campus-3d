import * as THREE from 'three';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { asset } from './boot';
import type { createContextStyle } from './context-style';
import type { createNightStyle } from './night';
import type { createPalette } from './palette';

/**
 * GLTF loader with the bundled Draco decoder. A decoder whose preload failed
 * stays broken, so `recover` replaces it before a retry.
 */
export function createModelLoader() {
  const loader = new GLTFLoader();
  let failed = false;
  function createDecoder() {
    const decoder = new DRACOLoader();
    decoder.setDecoderPath(asset('draco/'));
    // The base model carries hundreds of Draco primitives. Phone-sized layouts
    // keep two decoder heaps; larger screens use spare cores, at most four.
    decoder.setWorkerLimit(
      window.innerWidth < 760
        ? 2
        : Math.min(4, Math.max(2, (navigator.hardwareConcurrency || 2) - 1)),
    );
    // Fetch the decoder while the base model is still downloading. Model loads
    // still await this request; observing it here only avoids an unhandled
    // rejection when it fails before the first decode.
    (
      decoder.preload() as DRACOLoader & { decoderPending?: Promise<unknown> }
    ).decoderPending?.catch(() => {
      if (draco === decoder) failed = true;
    });
    return decoder;
  }
  let draco = createDecoder();
  loader.setDRACOLoader(draco);
  return {
    parseAsync: (buffer: ArrayBuffer, path: string) =>
      loader.parseAsync(buffer, path),
    recover() {
      if (!failed) return;
      draco.dispose();
      failed = false;
      draco = createDecoder();
      loader.setDRACOLoader(draco);
    },
    dispose() {
      draco.dispose();
    },
  };
}

/** Extends the base model's grass material across the surrounding ground plane. */
export function matchGround(
  ground: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshStandardMaterial>,
  base: THREE.Object3D,
  {
    nightStyle,
    contextStyle,
    night,
  }: {
    nightStyle: ReturnType<typeof createNightStyle>;
    contextStyle: ReturnType<typeof createContextStyle>;
    night: boolean;
  },
) {
  let grass: THREE.MeshStandardMaterial | undefined;
  base.traverse((o) => {
    if (
      !grass &&
      o instanceof THREE.Mesh &&
      o.material instanceof THREE.MeshStandardMaterial &&
      o.material.name === 'grass'
    )
      grass = o.material;
  });
  if (!grass) return;
  ground.material.dispose();
  ground.material = grass.clone();
  nightStyle.copyDayColor(grass, ground.material);
  nightStyle.apply(ground, night);
  contextStyle.apply(ground.material);
  const uv = ground.geometry.getAttribute('uv');
  for (let i = 0; i < uv.count; i++)
    uv.setXY(i, uv.getX(i) * 7500, uv.getY(i) * 7500);
  uv.needsUpdate = true;
}

/**
 * Building colours and terrain normals, computed after the base is already
 * shown. Keeps the original summation order and publishes each normal buffer
 * only once complete, yielding between bounded vertex batches. Resolves true
 * when finished, false when cancelled.
 */
export async function refineBase(
  base: THREE.Object3D,
  palette: ReturnType<typeof createPalette>,
  cancelled: () => boolean,
) {
  palette.buildings(base, 'base');
  const meshes: THREE.Mesh[] = [];
  base.traverse((o) => {
    if (o instanceof THREE.Mesh) meshes.push(o);
  });
  for (const mesh of meshes) {
    const steps = palette.terrainSteps(mesh);
    while (!cancelled()) {
      const step = steps.next();
      if (step.done) break;
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
    }
    if (cancelled()) return false;
  }
  return true;
}
