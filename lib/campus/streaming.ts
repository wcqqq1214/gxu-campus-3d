export interface StreamAsset {
  id?: string;
  url: string;
  bytes: number;
  sha256?: string;
  featureIds?: string[];
  /** Local east/north bounds; height is handled by the scene's frustum. */
  bounds?: [number, number, number, number];
}

export function nearbyChunks(
  assets: StreamAsset[],
  x: number,
  y: number,
  radius = 320,
) {
  return assets
    .map((asset) => {
      const b = asset.bounds;
      const distance = b
        ? Math.hypot(
            Math.max(b[0] - x, 0, x - b[2]),
            Math.max(b[1] - y, 0, y - b[3]),
          )
        : Infinity;
      const centerDistance = b
        ? Math.hypot((b[0] + b[2]) / 2 - x, (b[1] + b[3]) / 2 - y)
        : Infinity;
      return { asset, distance, centerDistance };
    })
    .filter((a) => a.distance < radius)
    .sort(
      (a, b) => a.distance - b.distance || a.centerDistance - b.centerDistance,
    );
}

/** Foreground, roads and buildings share a byte budget, not a slot count. */
export function planDetails(options: {
  foreground?: [string, StreamAsset];
  foregroundReady: boolean;
  roads: StreamAsset[];
  buildings: StreamAsset[];
  costs: ReadonlyMap<string, number>;
  cap: number;
}) {
  const { foreground, foregroundReady, roads, buildings, costs, cap } = options;
  const assets: [string, StreamAsset][] = [];
  let allocation = 0;
  if (foreground) {
    assets.push(foreground);
    allocation = costs.get(foreground[0]) ?? foreground[1].bytes * 24;
  }
  const append = (candidates: StreamAsset[], limit: number, factor: number) => {
    let count = 0;
    for (const item of candidates) {
      if (!item.id || count >= limit) continue;
      const cost = costs.get(item.id) ?? item.bytes * factor;
      if (allocation + cost > cap) continue;
      allocation += cost;
      assets.push([item.id, item]);
      count++;
    }
  };
  append(roads.slice(0, 3), 3, 28);
  append(buildings, foreground && !foregroundReady ? 1 : 3, 32);
  return { assets, allocation };
}

const abortError = () => new DOMException('Request cancelled', 'AbortError');
export class HttpError extends Error {
  status: number;
  constructor(status: number) {
    super(`HTTP ${status}`);
    this.status = status;
  }
}
/** Retry only transient failures, at most three attempts. Disposal interrupts backoff too. */
export async function withRetry<T>(
  operation: () => Promise<T>,
  signal: AbortSignal,
  delays = [600, 1800],
): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    signal.throwIfAborted();
    try {
      return await operation();
    } catch (error) {
      if (signal.aborted) throw abortError();
      const permanent =
        error instanceof HttpError &&
        error.status < 500 &&
        ![408, 429].includes(error.status);
      if (permanent || attempt >= delays.length) throw error;
      await new Promise<void>((resolve, reject) => {
        const cancel = () => {
          clearTimeout(timer);
          reject(abortError());
        };
        const timer = setTimeout(() => {
          signal.removeEventListener('abort', cancel);
          resolve();
        }, delays[attempt]);
        signal.addEventListener('abort', cancel, { once: true });
      });
    }
  }
}

export async function fetchModel(
  url: string,
  bytes: number,
  signal: AbortSignal,
  progress: (fraction: number) => void,
) {
  return withRetry(async () => {
    const timeout = new AbortController();
    const abort = () => timeout.abort();
    signal.addEventListener('abort', abort, { once: true });
    const timer = setTimeout(abort, 45000);
    try {
      progress(0);
      const response = await fetch(url, { signal: timeout.signal });
      if (!response.ok) throw new HttpError(response.status);
      if (!response.body) return await response.arrayBuffer();
      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      let received = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        received += value.byteLength;
        progress(Math.min(0.98, received / Math.max(1, bytes)));
      }
      const buffer = new Uint8Array(received);
      let offset = 0;
      for (const chunk of chunks) {
        buffer.set(chunk, offset);
        offset += chunk.byteLength;
      }
      return buffer.buffer;
    } finally {
      clearTimeout(timer);
      signal.removeEventListener('abort', abort);
    }
  }, signal);
}

interface Task<T> {
  key: string;
  priority: number;
  controller: AbortController;
  work: (signal: AbortSignal) => Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
  started: boolean;
}
/** Pending foreground models jump ahead of background chunks; cancelled work releases its slot. */
export class ResourceQueue<T> {
  tasks = new Map<string, Task<T>>();
  private active = 0;
  private concurrency: number;
  constructor(concurrency = 2) {
    this.concurrency = concurrency;
  }
  enqueue(
    key: string,
    priority: number,
    work: (signal: AbortSignal) => Promise<T>,
  ) {
    if (this.tasks.has(key)) throw new Error('Duplicate queue key');
    return new Promise<T>((resolve, reject) => {
      this.tasks.set(key, {
        key,
        priority,
        work,
        resolve,
        reject,
        started: false,
        controller: new AbortController(),
      });
      this.pump();
    });
  }
  cancel(key: string) {
    const task = this.tasks.get(key);
    if (!task) return;
    task.controller.abort();
    if (!task.started) {
      this.tasks.delete(key);
      task.reject(abortError());
    }
  }
  dispose() {
    for (const key of this.tasks.keys()) this.cancel(key);
  }
  private pump() {
    while (this.active < this.concurrency) {
      const next = [...this.tasks.values()]
        .filter((t) => !t.started)
        .sort((a, b) => a.priority - b.priority)[0];
      if (!next) return;
      this.active++;
      next.started = true;
      void next
        .work(next.controller.signal)
        .then(next.resolve, next.reject)
        .finally(() => {
          this.active--;
          this.tasks.delete(next.key);
          this.pump();
        });
    }
  }
}
