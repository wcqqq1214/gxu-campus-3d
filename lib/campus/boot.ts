import { fetchJson, fetchModel, type StreamAsset } from './streaming.ts';

const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';
const DATA_VERSION = process.env.NEXT_PUBLIC_DATA_VERSION;
export const asset = (path: string) =>
  `${BASE}/${path}` +
  (DATA_VERSION && path.startsWith('data/') && path.endsWith('.json')
    ? `?v=${DATA_VERSION}`
    : '');
/** Content-hashed model URL; prefetch and scene must request the same URL. */
export const modelUrl = (a: StreamAsset) =>
  asset(a.url) + (a.sha256 ? `?v=${a.sha256}` : '');

export interface ModelManifest {
  treePriorityPositions?: number[][];
  base: StreamAsset;
  trees: StreamAsset;
  treesNear?: StreamAsset;
  zones: StreamAsset[];
  landmarks: StreamAsset[];
  infrastructure?: StreamAsset[];
  sports?: StreamAsset[];
}

export interface BasePrefetch {
  manifest: Promise<ModelManifest>;
  base: Promise<ArrayBuffer>;
  /** Replays the latest fraction, then reports later download progress. */
  onProgress: (listener: (fraction: number) => void) => () => void;
}

/**
 * Start the manifest and base model before the scene code and building data
 * arrive. Both use the scene's normal retry policy and URLs. The caller owns
 * cancellation; an unconsumed failure stays silent until the scene awaits it.
 */
export function prefetchBase(signal: AbortSignal): BasePrefetch {
  const listeners = new Set<(fraction: number) => void>();
  let latest: number | null = null;
  const manifest = fetchJson<ModelManifest>(asset('data/models.json'), signal);
  const base = manifest.then((m) =>
    fetchModel(modelUrl(m.base), m.base.bytes, signal, (fraction) => {
      latest = fraction;
      for (const listener of listeners) listener(fraction);
    }),
  );
  manifest.catch(() => {});
  base.catch(() => {});
  return {
    manifest,
    base,
    onProgress(listener) {
      listeners.add(listener);
      if (latest !== null) listener(latest);
      return () => listeners.delete(listener);
    },
  };
}
