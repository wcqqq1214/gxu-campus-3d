import type { Message } from './i18n/index.ts';

export function createLoadStatusStore() {
  const initial = {
    message: '正在加载校园…' as Message,
    error: false,
    progress: undefined as number | undefined,
  };
  let snapshot = initial;
  let messageKey = JSON.stringify(initial.message);
  const listeners = new Set<() => void>();
  return {
    get: () => snapshot,
    getInitial: () => initial,
    getError: () => snapshot.error,
    set(message: Message, error = false, progress?: number) {
      // The status text already rounds to whole percentages. Match the bar's
      // publication rate so individual network chunks cannot flood React.
      if (progress !== undefined) progress = Math.round(progress * 100) / 100;
      const key = JSON.stringify(message);
      if (
        key === messageKey &&
        error === snapshot.error &&
        progress === snapshot.progress
      )
        return;
      messageKey = key;
      snapshot = { message, error, progress };
      for (const listener of listeners) listener();
    },
    subscribe(this: void, listener: () => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}
export type LoadStatusStore = ReturnType<typeof createLoadStatusStore>;
