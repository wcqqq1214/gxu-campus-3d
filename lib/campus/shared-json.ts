import { fetchJson } from './streaming.ts';

/** Share a page-lifetime immutable JSON response without sharing cancellation. */
export function createSharedJson<T>(
  url: string,
  fetcher: (url: string, signal: AbortSignal) => Promise<T> = fetchJson,
) {
  type Entry = {
    controller: AbortController;
    promise: Promise<T>;
    users: number;
    settled: boolean;
  };
  let cached: Entry | undefined;
  return (signal: AbortSignal): Promise<T> => {
    signal.throwIfAborted();
    if (!cached) {
      const controller = new AbortController();
      const entry: Entry = {
        controller,
        users: 0,
        settled: false,
        promise: fetcher(url, controller.signal).then(
          (value) => {
            entry.settled = true;
            return value;
          },
          (error: unknown) => {
            entry.settled = true;
            if (cached === entry) cached = undefined;
            throw error;
          },
        ),
      };
      cached = entry;
    }
    const entry = cached;
    entry.users++;
    return new Promise<T>((resolve, reject) => {
      let finished = false;
      const release = () => {
        finished = true;
        signal.removeEventListener('abort', abort);
        entry.users--;
        if (!entry.users && !entry.settled) {
          if (cached === entry) cached = undefined;
          entry.controller.abort();
        }
      };
      const abort = () => {
        release();
        reject(signal.reason);
      };
      signal.addEventListener('abort', abort, { once: true });
      entry.promise.then(
        (value) => {
          if (finished) return;
          release();
          resolve(value);
        },
        (error: unknown) => {
          if (finished) return;
          release();
          reject(error);
        },
      );
    });
  };
}
