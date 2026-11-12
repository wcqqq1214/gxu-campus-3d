import * as THREE from 'three';
import type { ModelManifest } from './boot';
import { disposeObject } from './resources';
import {
  nearbyChunks,
  planDetails,
  ResourceQueue,
  type StreamAsset,
} from './streaming';
import type { LayerKey } from './types';

/** Decoded geometry bytes of a model; shared buffers count once. */
export function detailCost(root: THREE.Object3D) {
  const buffers = new Set<ArrayBufferLike>();
  root.traverse((o) => {
    if (!(o instanceof THREE.Mesh)) return;
    for (const attribute of Object.values(o.geometry.attributes) as (
      | THREE.BufferAttribute
      | THREE.InterleavedBufferAttribute
    )[]) {
      const a =
        attribute instanceof THREE.InterleavedBufferAttribute
          ? attribute.data.array
          : attribute.array;
      buffers.add(a.buffer);
    }
    if (o.geometry.index) buffers.add(o.geometry.index.array.buffer);
  });
  return [...buffers].reduce((n, buffer) => n + buffer.byteLength, 0);
}

export interface DetailView {
  manifest: ModelManifest | null;
  /** The base model is published and the scene is not disposed. */
  ready: boolean;
  selected: string | null;
  smooth: boolean;
  budgetMiB: number;
  /** Where the camera is going; a flight selects details at its destination. */
  target: THREE.Vector3;
  camera: THREE.Vector3;
}

/**
 * Near-view streaming: the selected landmark, building chunks, roads and
 * sports details around the camera destination, within a decoded-geometry
 * budget. One recently used landmark may stay resident.
 */
export function createDetailStreaming({
  scene,
  root,
  layers,
  detailLayer,
  view,
  load,
  nearTrees,
  onNearTreesFailed,
  onAttached,
  onReleased,
  onSettled,
  onFailed,
  onReconciled,
}: {
  scene: THREE.Scene;
  /** Parent of attached detail models. */
  root: THREE.Group;
  layers: Record<LayerKey, boolean>;
  detailLayer: (key: string) => LayerKey;
  view: () => DetailView;
  load: (
    asset: StreamAsset,
    key: string,
    signal: AbortSignal,
  ) => Promise<{ scene: THREE.Group }>;
  /** Near trees share the queue; returns their loader only while they are wanted. */
  nearTrees: (
    distance: number,
  ) => ((signal: AbortSignal) => Promise<void>) | undefined;
  onNearTreesFailed: () => void;
  onAttached: (key: string) => void;
  onReleased: (key: string) => void;
  /** A queued request finished; the scene schedules a later reconcile. */
  onSettled: () => void;
  onFailed: () => void;
  onReconciled: () => void;
}) {
  const loaded = new Map<string, THREE.Group>();
  const failed = new Map<string, StreamAsset>();
  const wanted = new Set<string>();
  const recentlyUsed = new Map<string, number>();
  const geometryCosts = new Map<string, number>();
  const queue = new ResourceQueue<void>(2);
  let disposed = false;
  function release(key: string) {
    const detail = loaded.get(key);
    if (!detail) return;
    root.remove(detail);
    disposeObject(detail, [scene]);
    loaded.delete(key);
    onReleased(key);
    recentlyUsed.delete(key);
  }
  function loadDetail(a: StreamAsset, key: string, priority = 2) {
    if (loaded.has(key) || queue.tasks.has(key) || failed.has(key) || disposed)
      return;
    void queue
      .enqueue(key, priority, async (signal) => {
        const g = await load(a, key, signal);
        if (disposed || !wanted.has(key)) {
          disposeObject(g.scene);
          return;
        }
        root.add(g.scene);
        loaded.set(key, g.scene);
        recentlyUsed.set(key, performance.now());
        geometryCosts.set(key, detailCost(g.scene));
        failed.delete(key);
        onAttached(key);
        reconcile();
      })
      .catch((error) => {
        if (!disposed && error?.name !== 'AbortError') {
          failed.set(key, a);
          onFailed();
        }
      })
      .finally(() => {
        if (!disposed) onSettled();
      });
  }
  function reconcile(focusing = false) {
    const state = view();
    const { manifest, selected } = state;
    if (!manifest || disposed || !state.ready) return;
    const cap = state.budgetMiB * 1048576;
    const currentKey = 'landmark-' + selected;
    const foreground = manifest.landmarks.find((a) => a.id === selected);
    const destination = state.target;
    const destinationCamera = state.camera;
    const x = destination.x;
    const y = -destination.z;
    const distance = destinationCamera.distanceTo(destination);
    const near = !state.smooth && (focusing || distance < 1050);
    const candidates =
      near && layers.buildings ? nearbyChunks(manifest.zones, x, y) : [];
    // Keep in-flight building chunks ahead of new background work.
    candidates.sort(
      (a, b) =>
        Number(Boolean(queue.tasks.get(b.asset.id!)?.started)) -
        Number(Boolean(queue.tasks.get(a.asset.id!)?.started)),
    );
    const plan = planDetails({
      foreground:
        foreground && layers[detailLayer(currentKey)]
          ? [currentKey, foreground]
          : undefined,
      foregroundReady: loaded.has(currentKey),
      roads:
        near && layers.roads
          ? nearbyChunks(manifest.infrastructure ?? [], x, y, 230).map(
              ({ asset }) => asset,
            )
          : [],
      buildings: candidates.map(({ asset }) => asset),
      sports:
        near && layers.sports && distance < 300
          ? nearbyChunks(manifest.sports ?? [], x, y, 120).map(
              ({ asset }) => asset,
            )
          : [],
      costs: geometryCosts,
      cap,
    });
    const wantedAssets = plan.assets;
    let allocation = plan.allocation;
    wanted.clear();
    wantedAssets.forEach(([key]) => wanted.add(key));
    for (const key of queue.tasks.keys())
      if (key !== 'trees-near' && !wanted.has(key)) queue.cancel(key);
    for (const key of failed.keys()) if (!wanted.has(key)) failed.delete(key);
    // One recent landmark can stay warm if it fits the decoded-geometry budget.
    const older = [...loaded.keys()]
      .filter((key) => !wanted.has(key))
      .sort((a, b) => (recentlyUsed.get(b) ?? 0) - (recentlyUsed.get(a) ?? 0));
    let warm = false;
    for (const key of older) {
      const cost = geometryCosts.get(key) ?? 0;
      if (
        !warm &&
        key.startsWith('landmark-') &&
        layers[detailLayer(key)] &&
        allocation + cost <= cap
      ) {
        allocation += cost;
        warm = true;
      } else release(key);
    }
    for (const [index, [key, a]] of wantedAssets.entries()) {
      if (loaded.has(key)) recentlyUsed.set(key, performance.now());
      else loadDetail(a, key, index);
    }
    const loadNearTrees = queue.tasks.has('trees-near')
      ? undefined
      : nearTrees(distance);
    if (loadNearTrees)
      void queue.enqueue('trees-near', 5, loadNearTrees).catch((error) => {
        if (!disposed && error?.name !== 'AbortError') onNearTreesFailed();
      });
    onReconciled();
  }
  return {
    loaded: loaded as ReadonlyMap<string, THREE.Group>,
    geometryCosts: geometryCosts as ReadonlyMap<string, number>,
    get queued() {
      return queue.tasks.size;
    },
    reconcile,
    /** A wanted detail failed and has not been retried. */
    hasFailures() {
      return [...failed.keys()].some((key) => wanted.has(key));
    },
    retry() {
      failed.clear();
    },
    cancel(key: string) {
      queue.cancel(key);
    },
    /** Night windows add attributes lazily; include them in the budget. */
    remeasure() {
      for (const [key, detail] of loaded)
        geometryCosts.set(key, detailCost(detail));
    },
    dispose() {
      disposed = true;
      queue.dispose();
    },
  };
}
