import { useRef } from 'react';
import { ChevronLeft, ChevronRight, Pause, Play, X } from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import type { CampusTour as Tour } from '@/hooks/use-campus-tour';
import type { Landmark } from '@/lib/campus/types';

/** Tour controls at the foot of the panel, plus the compact form while it is collapsed. */
export function CampusTour({
  tour,
  landmarks,
  ready,
  collapsed,
}: {
  tour: Tour;
  landmarks: Landmark[];
  ready: boolean;
  collapsed: boolean;
}) {
  const { t, name } = useCampusLocale();
  const entry = useRef<HTMLButtonElement>(null);
  const { playing, started, index, progress } = tour;
  return (
    <>
      {collapsed && started && (
        <button
          className="tour-compact"
          onClick={() => tour.setPlaying((value) => !value)}
        >
          {playing ? <Pause size={15} /> : <Play size={15} />}
          {playing ? t('暂停游览') : t('继续游览')}
          <span>
            {index + 1}/{landmarks.length}
          </span>
        </button>
      )}
      <div className={`tour-bar ${started ? 'tour-active' : 'tour-idle'}`}>
        {playing && (
          <div className="tour-timer" key={index} aria-hidden="true">
            <span ref={progress} />
          </div>
        )}
        {started && (
          <div className="tour-heading">
            <div className="tour-copy">
              <small>
                <span className="tour-position">
                  {index + 1}/{landmarks.length}
                </span>
                <span>
                  {landmarks[index] ? name(landmarks[index].name) : ''}
                </span>
              </small>
            </div>
            <button
              className="tour-end"
              title={t('结束游览')}
              aria-label={t('结束游览')}
              onClick={(event) => {
                const panel = event.currentTarget.closest('aside');
                tour.setPlaying(false);
                tour.setStarted(false);
                requestAnimationFrame(() => {
                  const target =
                    entry.current ??
                    panel?.querySelector<HTMLButtonElement>(
                      '[role="tab"][aria-selected="true"]',
                    );
                  target?.focus({ preventScroll: true });
                });
              }}
            >
              <X size={16} />
            </button>
          </div>
        )}
        <button
          ref={entry}
          className="tour-start"
          disabled={!ready}
          onClick={() => {
            tour.setStarted(true);
            tour.setPlaying((value) => !value);
          }}
        >
          {playing ? <Pause size={15} /> : <Play size={15} />}
          <span>
            {playing ? t('暂停游览') : started ? t('继续游览') : t('开始游览')}
          </span>
          {!started && (
            <small className="tour-count">
              {t('{count} 个地点', { count: landmarks.length })}
            </small>
          )}
        </button>
        {started && (
          <>
            <button
              className="tour-skip"
              title={t('上一站')}
              disabled={!ready}
              onClick={() => tour.jump(-1)}
            >
              <ChevronLeft size={17} />
            </button>
            <button
              className="tour-skip"
              title={t('下一站')}
              disabled={!ready}
              onClick={() => tour.jump(1)}
            >
              <ChevronRight size={17} />
            </button>
          </>
        )}
      </div>
    </>
  );
}
