import { Check, Moon, Sun, Sunrise, Sunset } from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import { asset } from '@/lib/campus/boot';
import type { Preset, Quality } from '@/lib/campus/types';

const PRESETS: [Preset, string, typeof Sun][] = [
  ['morning', '清晨', Sunrise],
  ['day', '白天', Sun],
  ['evening', '黄昏', Sunset],
  ['night', '夜晚', Moon],
];
const QUALITY_OPTIONS: [Quality, string][] = [
  ['auto', '自动'],
  ['fine', '精细'],
  ['smooth', '流畅'],
];

/** Time-of-day presets and rendering quality. */
export function CampusLightingSettings({
  preset,
  quality,
  onPresetChange,
  onQualityChange,
}: {
  preset: Preset;
  quality: Quality;
  onPresetChange: (preset: Preset) => void;
  onQualityChange: (quality: Quality) => void;
}) {
  const { t } = useCampusLocale();
  return (
    <>
      <div className="preset-grid">
        {PRESETS.map(([p, label, Icon]) => (
          <button
            key={p}
            className={preset === p ? 'active' : ''}
            onClick={() => onPresetChange(p)}
            aria-pressed={preset === p}
            aria-label={t(label)}
          >
            <img
              src={asset(`images/presets/${p}.jpg`)}
              alt=""
              width={640}
              height={360}
              loading="lazy"
              decoding="async"
            />
            <span className="preset-caption">
              <Icon size={16} />
              {t(label)}
              {preset === p && <Check size={14} />}
            </span>
          </button>
        ))}
      </div>
      <div className="setting-row">
        <span id="quality-title">{t('画质')}</span>
        <fieldset className="segmented" aria-labelledby="quality-title">
          {QUALITY_OPTIONS.map(([q, label]) => (
            <button
              key={q}
              aria-pressed={quality === q}
              onClick={() => onQualityChange(q)}
            >
              {t(label)}
            </button>
          ))}
        </fieldset>
      </div>
    </>
  );
}
