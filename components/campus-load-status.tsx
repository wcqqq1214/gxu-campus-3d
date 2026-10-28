'use client';
import { useEffect, useState, useSyncExternalStore } from 'react';
import { LoaderCircle } from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import { statusText } from '@/lib/campus/i18n';
import type { LoadStatusStore } from '@/lib/campus/load-status-store';

export function CampusLoadStatus({
  store,
  ready,
  retry,
}: {
  store: LoadStatusStore;
  ready: boolean;
  retry: () => void;
}) {
  const { locale, t } = useCampusLocale();
  const {
    message: status,
    error,
    progress: loadProgress,
  } = useSyncExternalStore(store.subscribe, store.get, store.getInitial);
  const [backgroundStatusVisible, setBackgroundStatusVisible] = useState(false);
  const backgroundStatus = Boolean(status) && ready && !error;
  useEffect(() => {
    if (!backgroundStatus) {
      queueMicrotask(() => setBackgroundStatusVisible(false));
      return;
    }
    // Most nearby details arrive quickly; only slower loads are worth mentioning.
    const timer = setTimeout(() => setBackgroundStatusVisible(true), 600);
    return () => clearTimeout(timer);
  }, [backgroundStatus]);
  return (
    <>
      {status && ready && !error ? (
        // Streaming after the first paint is background work: a small, delayed pill.
        <output className="load-pill-lane">
          {backgroundStatusVisible && (
            <div className="load-pill">
              <LoaderCircle className="spin" size={14} aria-hidden="true" />
              <span>{statusText(locale, status)}</span>
              {Boolean(loadProgress) && (
                <i
                  aria-hidden="true"
                  style={{ transform: `scaleX(${loadProgress})` }}
                />
              )}
            </div>
          )}
        </output>
      ) : null}
      {status && !(ready && !error) && (
        <div
          className={`scene-status ${error ? 'error' : ''}`}
          role={error ? 'alert' : 'status'}
        >
          {!error && <LoaderCircle className="spin" size={16} />}
          <span>{statusText(locale, status)}</span>
          {loadProgress !== undefined && (
            <progress
              aria-label={t('模型加载进度')}
              max={1}
              value={loadProgress}
            />
          )}
          {error && <button onClick={retry}>{t('重试')}</button>}
        </div>
      )}
    </>
  );
}
