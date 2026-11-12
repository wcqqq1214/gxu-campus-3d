import { Share2 } from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import { CampusViewControls } from '@/components/campus-view-controls';
import { landmarkDescription } from '@/lib/campus/i18n/descriptions';
import { buildingLocationLabel } from '@/lib/campus/navigation';
import type { Building, Landmark, LandmarkView } from '@/lib/campus/types';
import { CATEGORY_NAMES } from '@/lib/campus/types';

/** Detail of the selected landmark or, failing that, ordinary building. */
export function CampusPlaceDetail({
  landmark,
  building,
  landmarks,
  view,
  orbit,
  reducedMotion,
  onViewChange,
  onOrbitChange,
  onShare,
}: {
  landmark?: Landmark;
  building?: Building;
  landmarks: Landmark[];
  view: LandmarkView | null;
  orbit: boolean;
  reducedMotion: boolean;
  onViewChange: (view: LandmarkView) => void;
  onOrbitChange: () => void;
  onShare: () => void;
}) {
  const { t, name, locale } = useCampusLocale();
  const current = (landmark ?? building)!;
  return (
    <section className="place-detail" aria-label={t('地点详情')}>
      <div className="detail-heading">
        <h2>{name(current.name)}</h2>
        <p className="detail-meta">
          <span className="detail-category">
            {t(CATEGORY_NAMES[current.category])}
          </span>
          {!landmark && (
            <span className="building-location">
              {buildingLocationLabel(building!, landmarks, locale)}
            </span>
          )}
        </p>
      </div>
      {landmark ? (
        <p>{landmarkDescription(landmark, locale)}</p>
      ) : (
        <p className="building-facts">
          {building!.levels >= 1
            ? t('约 {levels} 层，高约 {height} 米', {
                levels: Math.round(building!.levels),
                height: Math.round(building!.height),
              })
            : t('高约 {height} 米', {
                height: Math.round(building!.height),
              })}
        </p>
      )}
      <CampusViewControls
        landmark={landmark}
        view={view}
        orbit={orbit}
        reducedMotion={reducedMotion}
        onViewChange={onViewChange}
        onOrbitChange={onOrbitChange}
      />
      <div className="detail-actions">
        <button onClick={onShare}>
          <Share2 size={14} />
          {t('分享视角')}
        </button>
      </div>
    </section>
  );
}
