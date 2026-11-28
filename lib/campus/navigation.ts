import { collegeSearchNames, collegeVenues } from './college-venues.ts';
import { placeName, translate, type Locale } from './i18n/index.ts';
import type { Building, Landmark } from './types';

const LANDMARK_ALIASES: Record<string, string[]> = {
  'north-campus-north-gate': [
    '北校园北门',
    '行健东门',
    '行健文理学院东门',
    'North Campus North Gate',
    'Xingjian East Gate',
  ],
  'north-public-gate': ['西校园北门', 'North Gate'],
  'quanxue-island': ['知行书院', 'Zhixing Academy'],
  'veterinary-hospital': [
    '广西大学教学动物医院',
    '教学动物医院',
    'Veterinary Hospital',
    'Teaching Animal Hospital',
  ],
  'time-gate': ['时空之门', '时光广场', '图书馆北广场'],
  'south-gate': ['南门', '大学东路校门'],
  'south-side-gate': ['西南门', '南大门西侧门'],
  library: ['校图书馆', '西大图书馆'],
  huixue: ['君武文化艺术教育中心'],
  huicui: [
    '荟萃楼酒店',
    '荟萃餐厅',
    '荟萃楼餐厅',
    '荟萃食堂',
    '西大荟萃楼',
    '新闻传播学院',
    '新闻与传播学院',
  ],
  'teaching-ten': ['十教', '10教', '教学十楼', '多媒体教学楼'],
  'teaching-six': ['六教', '6教'],
  'teaching-two': ['二教', '2教', '南宁楼'],
  'student-center': [
    '大活',
    '学生活动中心',
    '老水塔咖啡厅',
    '老水塔西餐厅',
    '水塔餐厅',
  ],
  computer: ['计电', '计电学院', '计算机学院'],
  'international-residence': ['留学生', '国际学生公寓'],
  'new-east-gate': ['新东园门', '新东园入口', '秀灵西一里'],
  'east-gate': ['秀灵路东门'],
  'west-gate': ['鲁班路西门'],
  'chongzuo-bridge': ['崇左', '农院路', '桥下通道'],
  'bocui-bridge': ['博萃', '博翠桥', '农院路'],
  'huixian-bridge': ['荟贤', '汇贤桥', '农院路'],
};

export function navigableBuildings(
  buildings: Building[],
  landmarks: Landmark[],
): (Building & { landmark: string })[] {
  const ids = new Set(landmarks.map((place) => place.id));
  return buildings.filter(
    (building): building is Building & { landmark: string } =>
      building.landmark !== null && ids.has(building.landmark),
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
        ['gate', 'bridge', 'sculpture', 'garden'].includes(l.placeKind ?? ''),
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
const ENGLISH_ALIASES: Record<string, string[]> = {
  'student-center': ['Old Water Tower Café', 'Old Water Tower Cafe'],
  computer: [
    'School of Computer and Electronic Information',
    'Computer Science',
  ],
  huixue: ['Huixuetang Hall', 'Junwu Center for Culture and Arts Education'],
  huicui: [
    'Huicui Building Hotel',
    'Huicui Dining Hall',
    'School of Journalism and Communication',
  ],
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
  'south-side-gate': ['Southwest Gate'],
  'chongzuo-bridge': ['Nongyuan Road'],
  'bocui-bridge': ['Nongyuan Road'],
  'huixian-bridge': ['Nongyuan Road'],
  'time-gate': ['Time Square', 'Library North Square'],
};

/** OSM objects without a usable name keep a numeric placeholder; they are not searchable. */
const PLACEHOLDER_NAME = /^校内建筑 \d+$/;

// Navigation eligibility is entity-specific; do not rename or merge source footprints.
const EXCLUDED_BUILDINGS = new Set([
  // data/i18n-name-sources.json marks these as internal modeling descriptions (技),
  // not named destinations. Retain their geometry until real building names are verified.
  'north-campus/office',
  'north-campus/link-west',
  'north-campus/teaching-ne',
  'north-campus/teaching-south-middle',
  'north-campus/teaching-se',
  'north-campus/link-middle',
  'north-campus/lab-east',
]);

/** Named campus buildings outside the curated catalogue: search-only destinations, not toured. */
export function searchableBuildings(
  buildings: Building[],
  landmarks: Landmark[],
): Building[] {
  const curated = new Set(landmarks.map((place) => place.id));
  return buildings.filter(
    (building) =>
      building.insideCampus &&
      !EXCLUDED_BUILDINGS.has(building.id) &&
      (collegeVenues.has(building.id) ||
        (building.name.trim() !== '' &&
          !PLACEHOLDER_NAME.test(building.name))) &&
      !curated.has(
        building.landmark ?? collegeVenues.get(building.id)?.landmark ?? '',
      ),
  );
}

const collators = {
  zh: new Intl.Collator('zh-CN', { numeric: true }),
  en: new Intl.Collator('en', { numeric: true }),
};

const DIRECTIONS = ['东', '东北', '北', '西北', '西', '西南', '南', '东南'];

/** Approximate map position, not a claim about campus membership or walking distance. */
export function buildingLocationLabel(
  building: Building,
  landmarks: Landmark[],
  locale: Locale = 'zh',
): string {
  let nearest: Landmark | undefined;
  let distance = Infinity;
  for (const landmark of landmarks) {
    const candidate = Math.hypot(
      building.center[0] - landmark.center[0],
      building.center[1] - landmark.center[1],
    );
    if (
      candidate < distance ||
      (candidate === distance && nearest && landmark.id < nearest.id)
    ) {
      nearest = landmark;
      distance = candidate;
    }
  }
  if (!nearest) return '';
  const name = placeName(nearest.name, locale);
  if (distance < 10) return translate(locale, '{name}附近', { name });
  const angle = Math.atan2(
    building.center[1] - nearest.center[1],
    building.center[0] - nearest.center[0],
  );
  const direction = DIRECTIONS[(Math.round(angle / (Math.PI / 4)) + 8) % 8];
  return translate(locale, '{name}{direction}侧约 {distance} 米', {
    name,
    direction: translate(locale, direction),
    distance: Math.round(distance / 10) * 10,
  });
}

const BUILDING_ALIASES: Record<string, string[]> = {
  'relation/12874252': ['东校园学生宿舍17栋', '东17宿舍'],
  'way/948683801': ['东28栋教职工住房', '东28学生公寓', '东28北栋'],
  'way/948683803': ['东28栋教职工住房', '东28学生公寓', '东28南栋'],
  'way/759140894': ['西23栋供餐点', '西23供餐点', 'West 23 Dining Point'],
  'way/759140893': ['西22栋供餐点', '西22供餐点', 'West 22 Dining Point'],
  'relation/12774256': [
    '东27栋供餐点',
    '东27栋B区供餐点',
    '东27食堂',
    'East 27 Dining Point',
  ],
  'way/1544361473': ['博萃餐厅', '博萃食堂', 'Bocui Dining Hall'],
  'way/759337794': ['萃苑食堂', 'Cuiyuan Dining Hall'],
  'way/759191485': ['东苑食堂', 'Dongyuan Dining Hall'],
  'way/822812186': ['秀苑食堂', 'Xiuyuan Dining Hall'],
  'way/759609659': [
    '碧湖苑食堂',
    '碧湖苑风味餐厅',
    '风味食堂',
    'Bihuyuan Dining Hall',
    'Bihuyuan Specialty Dining Hall',
  ],
  'way/760187419': ['北苑食堂', 'Beiyuan Dining Hall'],
  'way/948683821': ['南苑', '南苑食堂', '南苑二餐厅', '南苑第二食堂'],
};

type Place = Landmark | Building;

function normalizeName(value: string) {
  return value
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[\s,，·‐‑‒–—−-]+/gu, '');
}

const venueTerms = new Map(
  [...new Set(collegeVenues.values())].map((venue) => [
    venue,
    collegeSearchNames(venue).map(normalizeName),
  ]),
);

/** Use the original landmark name on the explore tab and for its original purpose. */
export function destinationName(place: Place, locale: Locale, query = '') {
  const venue = collegeVenues.get(place.id);
  const original = placeName(place.name, locale);
  if (!venue) return original;
  if (place.id === venue.landmark) {
    const term = normalizeName(query);
    if (
      !term ||
      !venueTerms.get(venue)?.some((n) => n.includes(term)) ||
      [
        place.name,
        placeName(place.name, 'en'),
        placeName(place.name, 'zh'),
      ].some((n) => normalizeName(n).includes(term))
    )
      return original;
  }
  return venue[locale];
}

function indexPlace<T extends Place>(place: T, aliases: string[]) {
  const venue = collegeVenues.get(place.id);
  const named =
    Boolean(place.name.trim()) && !PLACEHOLDER_NAME.test(place.name);
  const names = [
    ...(named
      ? [place.name, placeName(place.name, 'zh'), placeName(place.name, 'en')]
      : []),
    ...aliases,
  ];

  return {
    place,
    names: [
      ...new Set(
        [
          ...names.map(normalizeName),
          ...(venue ? (venueTerms.get(venue) ?? []) : []),
        ].filter(Boolean),
      ),
    ],
    zh: venue?.zh ?? placeName(place.name, 'zh'),
    en: venue?.en ?? placeName(place.name, 'en'),
    secondary: venue?.secondary ? 1 : 0,
  };
}

function matchesFor<T extends Place>(
  entries: ReturnType<typeof indexPlace<T>>[],
  term: string,
  locale?: Locale,
) {
  const matches = [];
  for (const entry of entries) {
    let rank = 3;
    for (const name of entry.names) {
      if (name === term) {
        rank = 0;
        break;
      }
      if (name.startsWith(term)) rank = 1;
      else if (rank > 2 && name.includes(term)) rank = 2;
    }
    if (rank < 3) matches.push({ entry, rank });
  }
  if (locale)
    matches.sort(
      (a, b) =>
        a.rank - b.rank ||
        a.entry.secondary - b.entry.secondary ||
        collators[locale].compare(a.entry[locale], b.entry[locale]) ||
        a.entry.place.id.localeCompare(b.entry.place.id),
    );
  return matches;
}

function buildSearchIndex(buildings: Building[], landmarks: Landmark[]) {
  const featured = landmarks.map((p) =>
    indexPlace(p, [
      ...(LANDMARK_ALIASES[p.id] ?? []),
      ...(ENGLISH_ALIASES[p.id] ?? []),
    ]),
  );
  const ordinary = searchableBuildings(buildings, landmarks).map((b) =>
    indexPlace(b, BUILDING_ALIASES[b.id] ?? []),
  );
  return {
    query(value: string, locale: Locale = 'zh') {
      const term = normalizeName(value);
      if (!term)
        return {
          places: value.trim() ? [] : landmarks,
          buildings: [] as Building[],
          buildingsFirst: false,
        };
      const places = matchesFor(featured, term);
      const matches = matchesFor(ordinary, term, locale);
      const buildingsFirst =
        places.length > 0 &&
        matches.length > 0 &&
        Boolean(collegeVenues.get(matches[0].entry.place.id)) &&
        (matches[0].rank < places[0].rank ||
          (matches[0].rank === places[0].rank &&
            matches[0].entry.secondary < places[0].entry.secondary));
      return {
        places: places.map((m) => m.entry.place),
        buildings: matches.map((m) => m.entry.place),
        buildingsFirst,
      };
    },
  };
}

// Arrays are replaced on data refresh. A WeakMap lets a retired snapshot be collected.
type PlaceSearchIndex = ReturnType<typeof buildSearchIndex>;
const indices = new WeakMap<
  Building[],
  WeakMap<Landmark[], PlaceSearchIndex>
>();
export function getPlaceSearchIndex(
  buildings: Building[],
  landmarks: Landmark[],
): PlaceSearchIndex {
  let snapshots = indices.get(buildings);
  if (!snapshots) {
    snapshots = new WeakMap();
    indices.set(buildings, snapshots);
  }
  let index = snapshots.get(landmarks);
  if (!index) {
    index = buildSearchIndex(buildings, landmarks);
    snapshots.set(landmarks, index);
  }
  return index;
}

const noBuildings: Building[] = [];
export function searchLandmarks(
  landmarks: Landmark[],
  query: string,
): Landmark[] {
  return getPlaceSearchIndex(noBuildings, landmarks).query(query).places;
}
export function searchBuildings(
  buildings: Building[],
  landmarks: Landmark[],
  query: string,
  locale: Locale = 'zh',
): Building[] {
  return getPlaceSearchIndex(buildings, landmarks).query(query, locale)
    .buildings;
}
