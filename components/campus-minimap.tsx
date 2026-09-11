'use client';
import { memo, useEffect, useMemo, useState } from 'react';
import { MapPin, ChevronDown } from 'lucide-react';
import type { Building, Landmark } from '@/lib/campus/types';
import { cameraBearing, type CameraSnapshot } from '@/lib/campus/share';

export const CampusMinimap = memo(function CampusMinimap({
  buildings,
  current,
  camera,
  showBoundary,
}: {
  buildings: Building[];
  current?: Landmark;
  camera: CameraSnapshot | null;
  showBoundary: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [boundary, setBoundary] = useState<number[][][]>([]);
  useEffect(() => {
    if (!open || !showBoundary || boundary.length) return;
    const c = new AbortController();
    void fetch(
      `${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/data/campus-boundary.json`,
      { signal: c.signal },
    )
      .then((r) => {
        if (!r.ok) throw new Error('boundary');
        return r.json();
      })
      .then((d: { rings: number[][][] }) => setBoundary(d.rings))
      .catch(() => {});
    return () => c.abort();
  }, [open, showBoundary, boundary.length]);
  const [publicRoad, setPublicRoad] = useState<number[][]>([]);
  useEffect(() => {
    if (!open || publicRoad.length) return;
    const controller = new AbortController();
    void fetch(
      `${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/data/infrastructure-map.json`,
      { signal: controller.signal },
    )
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
      aria-label="校园位置小图"
    >
      <button
        className="minimap-toggle"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <MapPin size={16} />
        <span>{current ? `${current.name}的位置` : '校园位置小图'}</span>
        <ChevronDown size={14} />
      </button>
      {open && (
        <div className="minimap-body">
          <svg
            viewBox={`0 0 ${map.width} ${map.height}`}
            aria-label="北向朝上的校园建筑分布与镜头方向"
          >
            {map.shapes.map((shape) => (
              <path
                key={shape.id}
                d={shape.path}
                fill="#a8bda4"
                fillRule="evenodd"
              />
            ))}
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
                  stroke="#ffffff"
                  strokeWidth={1.8}
                  strokeOpacity={1}
                  style={{ filter: 'drop-shadow(0 0 1px #45584c)' }}
                >
                  <title>校园大致边界</title>
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
                stroke="#b77d4b"
                strokeWidth={2.4}
                strokeLinecap="round"
              >
                <title>农院路 · 公共道路</title>
              </path>
            )}
            {point && (
              <circle
                cx={point[0]}
                cy={point[1]}
                r={6}
                fill="#cf9e38"
                stroke="#fff"
                strokeWidth={2}
              />
            )}
            {target && (
              <g
                transform={`translate(${Math.max(10, Math.min(map.width - 10, target[0]))},${Math.max(10, Math.min(map.height - 10, target[1]))}) rotate(${-cameraBearing(camera)})`}
              >
                <path
                  d="M0 -13 L-7 7 L0 4 L7 7 Z"
                  fill="#1a5743"
                  stroke="white"
                  strokeWidth={1.5}
                />
              </g>
            )}
            <text x={map.width - 16} y={16} fontSize="12" fill="#244d36">
              N
            </text>
          </svg>
          <small>
            {outside
              ? '观察中心位于图外，箭头显示朝向'
              : `${publicRoad.length ? '棕线为公共农院路 · ' : ''}${showBoundary && boundary.length ? '白色细线为校园大致边界 · ' : ''}金点为地标，箭头为观察中心与朝向`}
          </small>
        </div>
      )}
    </section>
  );
});
