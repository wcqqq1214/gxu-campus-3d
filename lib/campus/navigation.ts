import { placeName } from './i18n/index.ts';
import type { Building, Category, Landmark } from './types';

export const LANDMARK_ALIASES: Record<string, string[]> = {
  'time-gate': ['时空之门', '时光广场', '图书馆北广场'],
  'south-gate': ['南门', '大学东路校门'],
  library: ['校图书馆', '西大图书馆'],
  huicui: ['荟萃楼酒店', '西大荟萃楼', '新闻传播学院', '新闻与传播学院'],
  'teaching-ten': ['十教', '10教', '教学十楼', '多媒体教学楼'],
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
      [
        place.name,
        placeName(place.name, 'zh'),
        placeName(place.name, 'en'),
        ...(LANDMARK_ALIASES[place.id] ?? []),
        ...(ENGLISH_ALIASES[place.id] ?? []),
      ].some((name) => name.toLocaleLowerCase().includes(term)),
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

/** Independent landmark POIs have estimated pick bounds, never OSM building IDs. */
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
      .filter((l) =>
        ['gate', 'bridge', 'sculpture'].includes(l.placeKind ?? ''),
      )
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

/** Search associations do not change the canonical name or merge physical places. */
export const ENGLISH_ALIASES: Record<string, string[]> = {
  computer: [
    'School of Computer and Electronic Information',
    'Computer Science',
  ],
  huixue: ['Huixuetang Hall', 'Junwu Center for Culture and Arts Education'],
  huicui: ['Huicui Building Hotel', 'School of Journalism and Communication'],
  'teaching-ten': [
    'Multimedia Teaching Building',
    'Teaching Building 10',
    'Shijiao',
  ],
  'teaching-six': ['Teaching Building 6', 'Liu Jiao'],
  'teaching-two': ['Nanning Building', 'Teaching Building 2'],
  'international-residence': [
    'International Students Dormitory',
    'International Students’ Dormitory',
  ],
  'new-east-gate': ['New East Gate', 'Xiuling Road West Lane 1'],
  'chongzuo-bridge': ['Nongyuan Road'],
  'bocui-bridge': ['Nongyuan Road'],
  'huixian-bridge': ['Nongyuan Road'],
  'time-gate': ['Time Square', 'Library North Square'],
};

/** OSM objects without a usable name keep a numeric placeholder; they are not searchable. */
const PLACEHOLDER_NAME = /^校内建筑 \d+$/;

/** Named campus buildings outside the curated catalogue: searchable, hoverable, not toured. */
export function searchableBuildings(
  buildings: Building[],
  landmarks: Landmark[],
): Building[] {
  const curated = new Set(landmarks.map((place) => place.id));
  return buildings.filter(
    (building) =>
      building.insideCampus &&
      building.name.trim() !== '' &&
      !PLACEHOLDER_NAME.test(building.name) &&
      !(building.landmark && curated.has(building.landmark)),
  );
}

const ZONE_ORDER: Record<string, number> = { east: 0, west: 1, north: 2 };
const collators = {
  zh: new Intl.Collator('zh-CN', { numeric: true }),
  en: new Intl.Collator('en', { numeric: true }),
};

/** Exact names first, then prefixes, then any substring in either language; ties sort by displayed name. */
export function searchBuildings(
  buildings: Building[],
  landmarks: Landmark[],
  query: string,
  locale: 'zh' | 'en' = 'zh',
): Building[] {
  const term = query.trim().toLocaleLowerCase();
  if (!term) return [];
  const rank = (building: Building) => {
    const names = [
      building.name,
      placeName(building.name, 'zh'),
      placeName(building.name, 'en'),
    ].map((name) => name.toLocaleLowerCase());
    if (names.some((name) => name === term)) return 0;
    if (names.some((name) => name.startsWith(term))) return 1;
    return names.some((name) => name.includes(term)) ? 2 : -1;
  };
  return searchableBuildings(buildings, landmarks)
    .map((building) => ({ building, rank: rank(building) }))
    .filter(({ rank }) => rank >= 0)
    .sort(
      (a, b) =>
        a.rank - b.rank ||
        (ZONE_ORDER[a.building.zone] ?? 3) -
          (ZONE_ORDER[b.building.zone] ?? 3) ||
        collators[locale].compare(
          placeName(a.building.name, locale),
          placeName(b.building.name, locale),
        ),
    )
    .map(({ building }) => building);
}
