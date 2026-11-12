import type * as THREE from 'three';

type Postprocessing = ReturnType<
  typeof import('./postprocessing').createPostprocessing
>;

/**
 * Post-processing loaded on demand. The module is fetched only once the base
 * model is shown and the fine tier asks for it; a failed load is not retried
 * until the quality choice changes.
 */
export function createSceneEffects({
  renderer,
  scene,
  camera,
  night,
  onReady,
}: {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  night: () => boolean;
  onReady: () => void;
}) {
  let effects: Postprocessing | null = null;
  let enabled = false;
  let loading = false;
  let failed = false;
  let disposed = false;
  return {
    /** Applies the tier's choice; `ready` is false until the base model is shown. */
    sync(on: boolean, ready: boolean) {
      enabled = on;
      if (!on) {
        effects?.dispose();
        effects = null;
        return;
      }
      if (effects) {
        effects.resize();
        return;
      }
      if (loading || failed || !ready) return;
      loading = true;
      void import('./postprocessing')
        .then(({ createPostprocessing }) => {
          if (!disposed && enabled) {
            effects = createPostprocessing(renderer, scene, camera);
            effects.setNight(night());
            onReady();
          }
        })
        .catch(() => {
          failed = true;
        })
        .finally(() => {
          loading = false;
        });
    },
    resetFailure() {
      failed = false;
    },
    setNight(on: boolean) {
      effects?.setNight(on);
    },
    /** Renders through the effects; returns false when they are not active. */
    render() {
      if (!effects || !enabled) return false;
      effects.render();
      return true;
    },
    get status() {
      return effects
        ? 'ready'
        : failed
          ? 'failed'
          : loading
            ? 'loading'
            : 'off';
    },
    dispose() {
      disposed = true;
      effects?.dispose();
    },
  };
}
