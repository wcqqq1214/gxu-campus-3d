'use client';
import { asset } from '@/lib/campus/boot';
import { loadCampusBoundary } from '@/lib/campus/boundary-data';
import { useCampusLocale } from '@/components/campus-locale';
import {
  memo,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from 'react';
import { MapPin, ChevronDown } from 'lucide-react';
import type { Building, Landmark } from '@/lib/campus/types';
import { cameraBearing } from '@/lib/campus/share';
import type { CameraStore } from '@/lib/campus/camera-store';

export const CampusMinimap = memo(function CampusMinimap({
  buildings,
  current,
  camera: cameraStore,
  showBoundary,
}: {
  buildings: Building[];
  current?: Pick<Landmark, 'name' | 'center'>;
  camera: CameraStore;
  showBoundary: boolean;
}) {
  const { t } = useCampusLocale();
  const [open, setOpen] = useState(false);
  // A closed minimap ignores camera samples instead of re-rendering for them.
  const camera = useSyncExternalStore(
    cameraStore.subscribe,
    () => (open ? cameraStore.get() : null),
    () => null,
  );
  const [boundary, setBoundary] = useState<number[][][]>([]);
  useEffect(() => {
    if (!open || !showBoundary || boundary.length) return;
    const c = new AbortController();
    void loadCampusBoundary(c.signal)
      .then((d: { rings: number[][][] }) => setBoundary(d.rings))
      .catch(() => {});
    return () => c.abort();
  }, [open, showBoundary, boundary.length]);
  const [publicRoad, setPublicRoad] = useState<number[][]>([]);
  useEffect(() => {
    if (!open || publicRoad.length) return;
    const controller = new AbortController();
    void fetch(asset('data/infrastructure-map.json'), {
      signal: controller.signal,
    })
      .then((r) => {
        if (!r.ok) throw new Error('map');
        return r.json();
      })
      .then((data: { path: number[][] }) => setPublicRoad(data.path))
      .catch(() => {});
    return () => controller.abort();
  }, [open, publicRoad.length]);
  const map = useMemo(() => {
    const bounds = buildings.filter((b) => b.insideCampus).map((b) => b.bounds);
    if (!bounds.length) return null;
    if (boundary.length) {
      const points = boundary.flat();
      bounds.push([
        Math.min(...points.map((p) => p[0])),
        Math.min(...points.map((p) => p[1])),
        Math.max(...points.map((p) => p[0])),
        Math.max(...points.map((p) => p[1])),
      ]);
    }
    const x0 = Math.min(...bounds.map((b) => b[0])) - 70,
      y0 = Math.min(...bounds.map((b) => b[1])) - 70;
    const x1 = Math.max(...bounds.map((b) => b[2])) + 70,
      y1 = Math.max(...bounds.map((b) => b[3])) + 70;
    const scale = 170 / Math.max(x1 - x0, y1 - y0);
    const point = (x: number, y: number) => [
      14 + (x - x0) * scale,
      14 + (y1 - y) * scale,
    ];
    return {
      point,
      width: (x1 - x0) * scale + 28,
      height: (y1 - y0) * scale + 28,
      shapes: buildings
        .filter((b) => b.insideCampus)
        .map((b) => ({
          id: b.id,
          path: b.polygons
            .map((poly) =>
              poly
                .map(
                  (ring) =>
                    ring
                      .map(
                        ([x, y], i) =>
                          `${i ? 'L' : 'M'}${point(x, y)
                            .map((n) => n.toFixed(1))
                            .join(',')}`,
                      )
                      .join(' ') + ' Z',
                )
                .join(' '),
            )
            .join(' '),
        })),
    };
  }, [buildings, boundary]);
  // Hundreds of footprints stay unchanged while the camera marker moves.
  const footprints = useMemo(
    () =>
      map?.shapes.map((shape) => (
        <path
          key={shape.id}
          d={shape.path}
          className="minimap-building"
          fillRule="evenodd"
        />
      )),
    [map],
  );
  if (!map) return null;
  const point = current ? map.point(...current.center) : null;
  const target = camera ? map.point(camera.target[0], -camera.target[2]) : null;
  const outside =
    target &&
    (target[0] < 0 ||
      target[0] > map.width ||
      target[1] < 0 ||
      target[1] > map.height);
  return (
    <section
      className={`campus-minimap ${open ? 'open' : ''}`}
      aria-label={t('小地图')}
    >
      <button
        className="minimap-toggle"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <MapPin size={16} />
        <span>{t('小地图')}</span>
        <ChevronDown size={14} />
      </button>
      {open && (
        <div className="minimap-body">
          <svg
            viewBox={`0 0 ${map.width} ${map.height}`}
            aria-label={t('北向朝上的校园建筑分布与镜头方向')}
          >
            {footprints}
            {showBoundary &&
              boundary.map((ring, i) => (
                <path
                  key={`boundary-${i}`}
                  d={ring
                    .map(
                      ([x, y], j) =>
                        `${j ? 'L' : 'M'}${map.point(x, y).join(',')}`,
                    )
                    .join(' ')}
                  fill="none"
                  stroke="white"
                  strokeWidth={1.8}
                  style={{ filter: 'drop-shadow(0 0 1px var(--sage-9))' }}
                >
                  <title>{t('校园大致边界')}</title>
                </path>
              ))}
            {publicRoad.length > 0 && (
              <path
                d={publicRoad
                  .map(
                    ([x, y], i) =>
                      `${i ? 'L' : 'M'}${map.point(x, y).join(',')}`,
                  )
                  .join(' ')}
                fill="none"
                stroke="var(--brown-9)"
                strokeWidth={2.4}
                strokeLinecap="round"
              >
                <title>{t('农院路（公共道路）')}</title>
              </path>
            )}
            {point && (
              <circle
                cx={point[0]}
                cy={point[1]}
                r={6}
                fill="var(--red-9)"
                stroke="white"
                strokeWidth={2}
              />
            )}
            {target && (
              <g
                transform={`translate(${Math.max(10, Math.min(map.width - 10, target[0]))},${Math.max(10, Math.min(map.height - 10, target[1]))}) rotate(${-cameraBearing(camera)})`}
              >
                <path
                  d="M0 -13 L-7 7 L0 4 L7 7 Z"
                  className="minimap-camera"
                  stroke="white"
                  strokeWidth={1.5}
                />
              </g>
            )}
            <text
              x={map.width - 16}
              y={16}
              fontSize="12"
              className="minimap-north"
            >
              N
            </text>
          </svg>
          <ul className="minimap-legend">
            {point && (
              <li>
                <i className="legend-place" />
                {t('当前地点')}
              </li>
            )}
            {target && (
              <li>
                <i className="legend-camera" />
                {outside ? t('视角（在图外）') : t('视角')}
              </li>
            )}
            {publicRoad.length > 0 && (
              <li>
                <i className="legend-road" />
                {t('农院路（公共道路）')}
              </li>
            )}
            {showBoundary && boundary.length > 0 && (
              <li>
                <i className="legend-boundary" />
                {t('校园大致边界')}
              </li>
            )}
          </ul>
        </div>
      )}
    </section>
  );
});
