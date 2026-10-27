import type { CameraSnapshot } from './share';

/**
 * Camera samples arrive several times a second while the view moves. Only the
 * compass and minimap read them, so they subscribe here instead of the page
 * holding the sample in state and re-rendering every panel.
 */
export interface CameraStore {
  get: () => CameraSnapshot | null;
  set: (snapshot: CameraSnapshot) => void;
  subscribe: (listener: () => void) => () => void;
}

export function createCameraStore(): CameraStore {
  let snapshot: CameraSnapshot | null = null;
  const listeners = new Set<() => void>();
  return {
    get: () => snapshot,
    set(next) {
      snapshot = next;
      for (const listener of listeners) listener();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}
