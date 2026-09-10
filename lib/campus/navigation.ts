import type { Building, Category, Landmark } from './types';

export const LANDMARK_ALIASES: Record<string, string[]> = {
  'south-gate': ['南门', '大学东路校门'],
  library: ['校图书馆', '西大图书馆'],
  'teaching-six': ['六教', '6教'],
  'teaching-two': ['二教', '2教', '南宁楼'],
  'student-center': ['大活', '学生活动中心'],
  computer: ['计电', '计电学院', '计算机学院'],
  'international-residence': ['留学生', '国际学生公寓'],
  'new-east-gate': ['新东园门', '新东园入口', '秀灵西一里'],
  'east-gate': ['秀灵路东门'],
  'west-gate': ['鲁班路西门'],
  'chongzuo-bridge': ['崇左', '农院路', '桥下通道'],
  'bocui-bridge': ['博萃', '博翠桥', '农院路'],
  'huixian-bridge': ['荟贤', '汇贤桥', '农院路'],
};

/** All navigation surfaces share the curated catalogue, never the footprint index. */
export function searchLandmarks(
  landmarks: Landmark[],
  query: string,
  category: Category | 'all' = 'all',
): Landmark[] {
  const term = query.trim().toLocaleLowerCase();
  return landmarks.filter(
    (place) =>
      (category === 'all' || place.category === category) &&
      [place.name, ...(LANDMARK_ALIASES[place.id] ?? [])].some((name) =>
        name.toLocaleLowerCase().includes(term),
      ),
  );
}

export function navigableBuildings(
  buildings: Building[],
  landmarks: Landmark[],
): Building[] {
  const ids = new Set(landmarks.map((place) => place.id));
  return buildings.filter(
    (building) => building.landmark !== null && ids.has(building.landmark),
  );
}

/** Independent gate POIs have estimated pick bounds, never OSM building IDs. */
export function navigationFootprints(
  buildings: Building[],
  landmarks: Landmark[],
) {
  return [
    ...navigableBuildings(buildings, landmarks).map((b) => ({
      ...b,
      layer: 'buildings' as const,
    })),
    ...landmarks
      .filter((l) => l.placeKind === 'gate' || l.placeKind === 'bridge')
      .map((l) => {
        const [x0, y0, x1, y1] = l.bounds;
        return {
          id: l.id,
          landmark: l.id,
          insideCampus: true,
          layer:
            l.placeKind === 'bridge'
              ? ('roads' as const)
              : ('buildings' as const),
          height: l.height,
          elevation: l.elevation,
          polygons: [
            [
              l.pickPolygon ?? [
                [x0, y0],
                [x1, y0],
                [x1, y1],
                [x0, y1],
                [x0, y0],
              ],
            ],
          ],
        };
      }),
  ];
}
