'use client';

import { useEffect, useRef } from 'react';
import { Orbit, Pause } from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import type { Landmark, LandmarkView } from '@/lib/campus/types';

function landmarkViewOptions(landmark: Landmark, t: (key: string) => string) {
  const northSouth = ['library', 'teaching-six'].includes(landmark.id);
  const options: [LandmarkView, string][] = [
    ['front', t(northSouth ? '南侧' : '正面')],
    ['back', t(northSouth ? '北侧' : '背面')],
    [
      'entrance',
      t(
        northSouth
          ? '南门近景'
          : landmark.placeKind === 'bridge'
            ? '桥下近景'
            : landmark.placeKind === 'sculpture'
              ? '雕塑近景'
              : '入口近景',
      ),
    ],
  ];
  if (northSouth) options.push(['rear-entrance', t('北门近景')]);
  return options;
}

export function CampusViewControls({
  landmark,
  view,
  orbit,
  reducedMotion,
  onViewChange,
  onOrbitChange,
}: {
  landmark?: Landmark;
  view: LandmarkView | null;
  orbit: boolean;
  reducedMotion: boolean;
  onViewChange: (view: LandmarkView) => void;
  onOrbitChange: () => void;
}) {
  const { t, locale } = useCampusLocale();
  const directions = useRef<HTMLFieldSetElement>(null);
  const landmarkId = landmark?.id;

  useEffect(() => {
    const row = directions.current;
    if (!row) return;
    let frame = 0;
    const measure = () => {
      const remaining = row.scrollWidth - row.clientWidth - row.scrollLeft;
      row.dataset.fade =
        row.scrollWidth <= row.clientWidth + 1
          ? 'none'
          : remaining > 6
            ? 'right'
            : 'left';
    };
    const reveal = (behavior: ScrollBehavior) => {
      if (
        window.innerWidth < 760 &&
        row.clientWidth > 0 &&
        row.scrollWidth > row.clientWidth
      ) {
        row
          .querySelector<HTMLButtonElement>('[aria-pressed="true"]')
          ?.scrollIntoView({ inline: 'nearest', block: 'nearest', behavior });
      }
      measure();
    };
    // Observe the row and options: translations, font loading and reopening the dock
    // can change the overflow even when the selected view remains the same.
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => reveal('auto'));
    });
    observer.observe(row);
    Array.from(row.children).forEach((child) => observer.observe(child));
    row.addEventListener('scroll', measure, { passive: true });
    reveal(reducedMotion ? 'auto' : 'smooth');
    return () => {
      observer.disconnect();
      row.removeEventListener('scroll', measure);
      cancelAnimationFrame(frame);
    };
  }, [view, orbit, locale, landmarkId, reducedMotion]);

  return (
    <fieldset className="landmark-views" aria-label={t('地点观察视角')}>
      <div className="view-primary-row">
        <fieldset className="segmented" aria-label={t('视角')}>
          {(['oblique', 'top'] as const).map((value) => (
            <button
              key={value}
              aria-pressed={!orbit && view === value}
              onClick={() => onViewChange(value)}
            >
              {t(value === 'oblique' ? '全貌' : '俯视')}
            </button>
          ))}
        </fieldset>
        {landmark && (
          <button
            className="orbit-toggle"
            aria-pressed={orbit}
            disabled={reducedMotion}
            title={
              reducedMotion
                ? t('系统已启用减少动态效果')
                : t('环绕当前地点，拖动画面可暂停')
            }
            onClick={onOrbitChange}
          >
            {orbit ? <Pause size={14} /> : <Orbit size={14} />}
            {orbit ? t('暂停环绕') : t('环绕')}
          </button>
        )}
      </div>
      {landmark && (
        <fieldset
          className="segmented view-directions"
          ref={directions}
          aria-label={t('方位与近景')}
        >
          {landmarkViewOptions(landmark, t).map(([value, label]) => (
            <button
              key={value}
              aria-pressed={!orbit && view === value}
              onClick={() => onViewChange(value)}
            >
              {label}
            </button>
          ))}
        </fieldset>
      )}
    </fieldset>
  );
}
