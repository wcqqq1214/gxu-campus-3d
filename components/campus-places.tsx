import { useMemo, useRef } from 'react';
import { Building2, ChevronRight, Search, X } from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import { Input } from '@/components/ui/input';
import {
  buildingLocationLabel,
  destinationName,
  getPlaceSearchIndex,
} from '@/lib/campus/navigation';
import type { Building, Category, Landmark } from '@/lib/campus/types';
import { CATEGORY_NAMES } from '@/lib/campus/types';

const BUILDING_RESULT_LIMIT = 40;
const CATEGORY_ORDER: Category[] = [
  'academic',
  'culture',
  'landmark',
  'infrastructure',
  'living',
  'service',
];

/** Search field and place list of the explore tab. */
export function CampusPlaces({
  landmarks,
  buildings,
  query,
  selected,
  hovered,
  ready,
  failed,
  onQueryChange,
  onSearchFocus,
  onHover,
  onChoose,
  onRetry,
}: {
  landmarks: Landmark[];
  buildings: Building[];
  query: string;
  selected: string | null;
  hovered: string | null;
  ready: boolean;
  failed: boolean;
  onQueryChange: (query: string) => void;
  onSearchFocus: () => void;
  onHover: (id: string | null) => void;
  onChoose: (id: string) => void;
  onRetry: () => void;
}) {
  const { t, locale } = useCampusLocale();
  const searchWrap = useRef<HTMLDivElement>(null);
  const index = useMemo(
    () => getPlaceSearchIndex(buildings, landmarks),
    [buildings, landmarks],
  );
  const {
    places,
    buildings: buildingMatches,
    buildingsFirst,
  } = useMemo(() => index.query(query, locale), [index, query, locale]);
  const searching = Boolean(query.trim());
  const resultCount = places.length + buildingMatches.length;
  const groups = searching
    ? places.length
      ? [{ key: 'search', name: t('精选地点'), places }]
      : []
    : CATEGORY_ORDER.map((key) => ({
        key,
        name: t(CATEGORY_NAMES[key]),
        places: places.filter((p) => p.category === key),
      })).filter((group) => group.places.length);
  function resetSearch() {
    onQueryChange('');
    searchWrap.current?.querySelector('input')?.focus();
  }
  const landmarkRows = (
    <PlaceGroups
      key="places"
      query={query}
      groups={groups}
      selected={selected}
      hovered={hovered}
      ready={ready}
      searching={searching && !buildingMatches.length}
      onHover={onHover}
      onChoose={onChoose}
    />
  );
  const buildingRows = (
    <BuildingResults
      key="buildings"
      buildings={buildingMatches}
      landmarks={landmarks}
      selected={selected}
      ready={ready}
      titled={places.length > 0}
      onChoose={onChoose}
    />
  );
  return (
    <>
      <div className="search-wrap" ref={searchWrap}>
        <Search size={16} />
        <Input
          type="search"
          onFocus={onSearchFocus}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={t('搜索地点或建筑')}
          aria-label={t('搜索校园地点')}
        />
        {query && (
          <button title={t('清除搜索')} onClick={resetSearch}>
            <X size={14} />
          </button>
        )}
      </div>
      <output
        className="result-heading"
        data-searching={searching}
        aria-atomic="true"
      >
        {searching
          ? t('{count} 个结果', { count: resultCount })
          : t('{count} 个地点', { count: resultCount })}
      </output>
      <div className="places">
        {!landmarks.length ? (
          failed ? (
            <div className="empty-state">
              <p>{t('地点数据加载失败')}</p>
              <button className="search-reset" onClick={onRetry}>
                {t('重新加载')}
              </button>
            </div>
          ) : (
            <output className="empty-state">{t('正在加载地点…')}</output>
          )
        ) : resultCount ? (
          <>
            {buildingsFirst
              ? [buildingRows, landmarkRows]
              : [landmarkRows, buildingRows]}
          </>
        ) : (
          <div className="empty-state">
            <p>{t('没有找到相关地点或建筑')}</p>
            <button className="search-reset" onClick={resetSearch}>
              {t('清空搜索')}
            </button>
          </div>
        )}
      </div>
    </>
  );
}

function PlaceGroups({
  query,
  groups,
  selected,
  hovered,
  ready,
  searching,
  onHover,
  onChoose,
}: {
  query: string;
  groups: { key: string; name: string; places: Landmark[] }[];
  selected: string | null;
  hovered: string | null;
  ready: boolean;
  searching: boolean;
  onHover: (id: string | null) => void;
  onChoose: (id: string) => void;
}) {
  const { locale } = useCampusLocale();
  return (
    <>
      {groups.map((group) => (
        <section
          className="place-group"
          key={group.key}
          aria-label={group.name}
        >
          {!searching && <h3>{group.name}</h3>}
          {group.places.map((p) => (
            <button
              key={p.id}
              data-place-id={p.id}
              className={`place-row ${selected === p.id ? 'selected' : ''} ${hovered === p.id ? 'linked-hover' : ''}`}
              onPointerEnter={() => onHover(p.id)}
              onPointerLeave={() => onHover(null)}
              onFocus={() => onHover(p.id)}
              onBlur={() => onHover(null)}
              onClick={() => onChoose(p.id)}
              disabled={!ready}
            >
              <span className="place-copy">
                <strong>{destinationName(p, locale, query)}</strong>
              </span>
              <ChevronRight size={16} aria-hidden="true" />
            </button>
          ))}
        </section>
      ))}
    </>
  );
}

function BuildingResults({
  buildings,
  landmarks,
  selected,
  ready,
  titled,
  onChoose,
}: {
  buildings: Building[];
  landmarks: Landmark[];
  selected: string | null;
  ready: boolean;
  titled: boolean;
  onChoose: (id: string) => void;
}) {
  const { t, locale } = useCampusLocale();
  if (!buildings.length) return null;
  const shown = buildings.slice(0, BUILDING_RESULT_LIMIT);
  return (
    <section
      className="place-group building-results"
      aria-label={t('其他建筑')}
    >
      {titled && <h3>{t('其他建筑')}</h3>}
      {shown.map((b) => (
        <button
          key={b.id}
          data-place-id={b.id}
          className={`place-row building-row ${selected === b.id ? 'selected' : ''}`}
          onClick={() => onChoose(b.id)}
          disabled={!ready}
        >
          <Building2 size={15} className="place-kind" aria-hidden="true" />
          <span className="place-copy">
            <strong>{destinationName(b, locale)}</strong>
            <small>
              <span>{t(CATEGORY_NAMES[b.category])}</span>
              <span>{buildingLocationLabel(b, landmarks, locale)}</span>
            </small>
          </span>
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      ))}
      {buildings.length > shown.length && (
        <p className="result-more">
          {t('还有 {count} 处，请输入更完整的名称', {
            count: buildings.length - shown.length,
          })}
        </p>
      )}
    </section>
  );
}
