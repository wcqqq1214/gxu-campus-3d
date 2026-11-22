import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import {
  buildingLocationLabel,
  destinationName,
  getPlaceSearchIndex,
  searchableBuildings,
  searchBuildings,
  searchLandmarks,
} from '../lib/campus/navigation.ts';
import { collegeVenues } from '../lib/campus/college-venues.ts';
import { runtimeBuildings } from './runtime-data.mjs';
import { placeName } from '../lib/campus/i18n/index.ts';
import { decodeShare, encodeShare } from '../lib/campus/share.ts';
const read = (path) =>
  JSON.parse(fs.readFileSync(new URL(path, import.meta.url), 'utf8'));
const buildings = read('../public/data/buildings.json');
const landmarks = read('../public/data/landmarks.json');

test('all confirmed Huixue aliases resolve only to the curated hall', () => {
  for (const query of [
    '汇学堂',
    '君武文化艺术教育中心',
    'Huixue Hall',
    'Huixuetang Hall',
    'Junwu Center for Culture and Arts Education',
  ]) {
    assert.deepEqual(
      [
        ...searchLandmarks(landmarks, query),
        ...searchBuildings(buildings, landmarks, query),
      ].map((place) => place.id),
      ['huixue'],
      query,
    );
  }
});

test('南苑食堂的常用搜索词定位到旧餐厅北侧的南苑第二餐厅', () => {
  for (const query of ['南苑食堂', '南苑第二食堂', '南苑二餐厅', '南苑']) {
    const [place] = searchBuildings(buildings, landmarks, query);
    assert.equal(place.id, 'way/948683821');
    assert.equal(place.name, '南苑第二餐厅');
  }
  assert.equal(
    searchBuildings(buildings, landmarks, '南苑餐厅')[0].id,
    'way/759147049',
  );
});

test('餐厅别名可定位到独立餐厅或其所在楼栋', () => {
  for (const [query, id] of [
    ['西23栋供餐点', 'way/759140894'],
    ['西22栋供餐点', 'way/759140893'],
    ['萃苑食堂', 'way/759337794'],
    ['博萃餐厅', 'way/1544361473'],
    ['东苑食堂', 'way/759191485'],
    ['秀苑食堂', 'way/822812186'],
    ['碧湖苑食堂', 'way/759609659'],
    ['风味餐厅', 'way/759609659'],
    ['碧湖苑风味餐厅', 'way/759609659'],
    ['北苑食堂', 'way/760187419'],
    ['荟萃餐厅', 'huicui'],
    ['Huicui Dining Hall', 'huicui'],
    ['老水塔咖啡厅', 'student-center'],
    ['Old Water Tower Café', 'student-center'],
  ]) {
    const matches = [
      ...searchLandmarks(landmarks, query),
      ...searchBuildings(buildings, landmarks, query),
    ];
    assert.deepEqual(
      matches.map((place) => place.id),
      [id],
      query,
    );
  }
});

test('internal model descriptions and the disputed footprint are not destinations', () => {
  const evidence = read('../data/i18n-name-sources.json');
  const internal = buildings.filter(
    (b) =>
      evidence.entries[b.name]?.status === '技' && !collegeVenues.has(b.id),
  );
  assert.ok(internal.length >= 7);
  const pool = searchableBuildings(buildings, landmarks);
  const ids = [...landmarks, ...pool].map((b) => b.id);
  for (const id of ['way/759337787', ...internal.map((b) => b.id)]) {
    assert.ok(!ids.includes(id), id);
    assert.equal(decodeShare(`#place=${encodeURIComponent(id)}`, ids), null);
  }
  // Withhold navigation, not the existing source geometry or its unverified name.
  assert.equal(
    buildings.find((b) => b.id === 'way/759337787').name,
    '君武文化艺术教育中心',
  );
  for (const name of [
    '物理资治楼',
    '广西碳酸钙产业化工工程院',
    '北8',
    '校长楼',
  ]) {
    assert.equal(placeName(name, 'zh'), name);
    assert.ok(
      searchBuildings(buildings, landmarks, name).some((b) => b.name === name),
    );
  }
});

test('map positions use east/north coordinates, independent of rendering zones', () => {
  const landmark = {
    ...landmarks[0],
    id: 'library',
    name: '图书馆',
    center: [0, 0],
  };
  const cases = [
    [100, 0, '东', 'east', 100],
    [100, 100, '东北', 'northeast', 140],
    [0, 100, '北', 'north', 100],
    [-100, 100, '西北', 'northwest', 140],
    [-100, 0, '西', 'west', 100],
    [-100, -100, '西南', 'southwest', 140],
    [0, -100, '南', 'south', 100],
    [100, -100, '东南', 'southeast', 140],
  ];
  for (const [x, y, zh, en, distance] of cases) {
    for (const zone of ['east', 'west', 'north']) {
      const b = { ...buildings[0], center: [x, y], zone };
      assert.equal(
        buildingLocationLabel(b, [landmark]),
        `图书馆${zh}侧约 ${distance} 米`,
      );
      assert.equal(
        buildingLocationLabel(b, [landmark], 'en'),
        `About ${distance} m ${en} of University Library`,
      );
    }
  }
  assert.equal(
    buildingLocationLabel({ ...buildings[0], center: [0, 0] }, [landmark]),
    '图书馆附近',
  );
  assert.equal(buildingLocationLabel(buildings[0], []), '');
});

test('same-name buildings remain distinct in the result and detail location labels', () => {
  const pool = searchableBuildings(buildings, landmarks);
  for (const locale of ['zh', 'en']) {
    const seen = new Set();
    for (const b of pool) {
      const label = `${placeName(b.name, locale)} · ${buildingLocationLabel(b, landmarks, locale)}`;
      assert.ok(!seen.has(label), `${b.id}: ${label}`);
      seen.add(label);
    }
  }
  const ones = searchBuildings(buildings, landmarks, '1号楼').filter(
    (b) => b.name === '1号楼',
  );
  assert.equal(ones.length, 4);
  assert.equal(
    new Set(ones.map((b) => buildingLocationLabel(b, landmarks))).size,
    4,
  );
});

test('ordering is stable across input order and arbitrary modeling zone changes', () => {
  const expected = searchBuildings(buildings, landmarks, '1号楼').map(
    (b) => b.id,
  );
  const changed = [...buildings]
    .reverse()
    .map((b) => ({ ...b, zone: b.zone === 'east' ? 'west' : 'east' }));
  assert.deepEqual(
    searchBuildings(changed, landmarks, '1号楼').map((b) => b.id),
    expected,
  );
});

test('every eligible full name stays reachable within 40 results in both languages and can be shared', () => {
  const pool = searchableBuildings(buildings, landmarks);
  const ids = [...landmarks, ...pool].map((b) => b.id);
  for (const b of pool) {
    for (const locale of ['zh', 'en']) {
      assert.ok(
        searchBuildings(
          buildings,
          landmarks,
          destinationName(b, locale),
          locale,
        )
          .slice(0, 40)
          .some((result) => result.id === b.id),
        b.id,
      );
    }
    assert.equal(
      decodeShare(
        encodeShare({
          selected: b.id,
          view: 'top',
          preset: 'day',
          position: [0, 100, 100],
          target: [0, 0, 0],
          span: 80,
        }),
        ids,
      ).selected,
      b.id,
    );
  }
});

test('named campus buildings are searchable in both languages', () => {
  const zh = searchBuildings(buildings, landmarks, '电气');
  assert.ok(zh.some((b) => b.name === '电气工程学院'));
  const en = searchBuildings(buildings, landmarks, 'electrical engineering');
  assert.ok(en.some((b) => b.name === '电气工程学院'));
  assert.deepEqual(searchBuildings(buildings, landmarks, '  '), []);
});

test('exact names rank before prefixes and substrings', () => {
  const results = searchBuildings(buildings, landmarks, '电气工程学院');
  assert.equal(results[0].name, '电气工程学院');
});

test('placeholders, outside buildings and curated landmarks stay out of building search', () => {
  const pool = searchableBuildings(buildings, landmarks);
  const curated = new Set(landmarks.map((place) => place.id));
  assert.ok(pool.length > 200);
  for (const b of pool) {
    assert.ok(b.insideCampus, b.id);
    assert.doesNotMatch(destinationName(b, 'zh'), /^校内建筑 \d+$/);
    assert.ok(!(b.landmark && curated.has(b.landmark)), b.id);
  }
  // The library is found once, through the curated catalogue.
  assert.ok(
    searchLandmarks(landmarks, '图书馆').some((p) => p.id === 'library'),
  );
  assert.ok(
    !searchBuildings(buildings, landmarks, '图书馆').some(
      (b) => b.landmark === 'library',
    ),
  );
});

const index = getPlaceSearchIndex(buildings, landmarks);
function ids(query, search = index) {
  const { places, buildings, buildingsFirst } = search.query(query);
  return (
    buildingsFirst ? [...buildings, ...places] : [...places, ...buildings]
  ).map((p) => p.id);
}

test('one index per snapshot serves both locales and rebuilds on replacement', () => {
  assert.equal(getPlaceSearchIndex(buildings, landmarks), index);
  const refreshed = buildings.map((b) =>
    b.id === 'way/759079683' ? { ...b, name: '刷新后的名称' } : b,
  );
  assert.deepEqual(
    ids('刷新后的名称', getPlaceSearchIndex(refreshed, landmarks)),
    ['way/759079683'],
  );
  assert.deepEqual(ids('刷新后的名称'), []);
  assert.deepEqual(index.query('').places, landmarks);
  assert.deepEqual(index.query('').buildings, []);
});

test('college names and shared venues select the correct destination in both data formats', () => {
  const compact = getPlaceSearchIndex(runtimeBuildings(buildings), landmarks);
  for (const [id, ...queries] of [
    [
      'relation/11970573',
      '文学院',
      '法学院',
      '国际中文教育学院',
      'School of Liberal Arts',
      'School of Law',
      '育林楼',
    ],
    [
      'relation/11564915',
      '公管',
      '工商学院',
      'School of Public Policy and Management',
      'Business School',
    ],
    [
      'huicui',
      '新传',
      '新闻与传播学院',
      'School of Journalism and Communication',
      '融媒体中心',
    ],
    ['laboratory', '海洋学院', 'Marine Science', '电工电子实验教学示范中心'],
    [
      'international-residence',
      '经济学院',
      '中国-东盟金融合作学院',
      'China–ASEAN Institute of Financial Cooperation',
    ],
    ['way/759096575', '经济学院旧址'],
    ['relation/11564999', '特色金属材料与组合结构全寿命安全国家重点实验室'],
    ['relation/11564998', '马院', 'Zizhi Building'],
    ['way/957404989', '物理学院'],
    ['relation/12875607', '外院', '逸夫楼'],
    ['way/759096564', '外院小红楼'],
    ['way/759165563', '九教'],
    ['way/759165562', '艺术学院附楼'],
    ['way/759609659', '舞蹈排练厅'],
    ['way/759079685', '原四教工程训练中心'],
    ['way/1501460953', '继教院'],
    ['way/759090371', '化工1号楼附楼'],
    ['way/759080586', '化工二号楼'],
    ['way/759080587', '原无机楼'],
    ['way/759079682', '君武学堂'],
    ['relation/20510975', '东区电气实验中心'],
    ['relation/20369638', '农林动中心'],
    ['way/1502723420', '农林动报告厅'],
    ['way/948683813', '体育训练翼'],
    ['way/759170251', '水生动物病害诊断实验室'],
    ['way/759129515', '广西数学研究中心'],
    ['computer', '计电'],
    ['huixue', '汇学堂'],
    ['huicui', '荟萃楼'],
  ])
    for (const query of queries) {
      const result = ids(query);
      assert.equal(result[0], id, query);
      assert.equal(result.filter((x) => x === id).length, 1, query);
      assert.deepEqual(ids(query, compact), result, query);
    }
});

test('unverified subdivisions are absent and historical destinations are labelled', () => {
  for (const q of [
    '经济学院A座',
    '经济学院B座',
    'B203',
    '化工3号楼',
    '物理学院C座',
    '生科院南楼306',
    '校内建筑 759096564',
  ])
    assert.deepEqual(ids(q), [], q);
  const raw = (id) => buildings.find((b) => b.id === id);
  assert.match(
    destinationName(raw('way/759096575'), 'en'),
    /former map label/i,
  );
  assert.match(destinationName(raw('way/759170251'), 'zh'), /环境工程/);
  assert.ok(!ids('国际中文教育学院').includes('way/842784665'));
  assert.ok(!ids('物理学院').includes('relation/11564998'));
  const residence = landmarks.find((p) => p.id === 'international-residence');
  for (const locale of ['zh', 'en']) {
    assert.equal(
      destinationName(residence, locale),
      placeName(residence.name, locale),
    );
    assert.match(
      destinationName(residence, locale, '经济学院'),
      locale === 'zh' ? /鸪江路入口候选/ : /probable street entrance/,
    );
    assert.match(
      destinationName(raw('way/759096575'), locale),
      locale === 'zh' ? /西校园旧图标注/ : /former map label/,
    );
  }
  const news = landmarks.find((p) => p.id === 'huicui');
  assert.equal(destinationName(news, 'zh', '荟萃餐厅'), '荟萃楼');
  assert.equal(destinationName(news, 'en'), 'Huicui Building');
  assert.match(destinationName(news, 'en', '新传'), /Journalism/);
  const old = { ...raw('relation/11970574'), landmark: null };
  assert.deepEqual(ids('新闻学院', getPlaceSearchIndex([old], [])), [old.id]);
  assert.deepEqual(ids('新闻学院', getPlaceSearchIndex([old], [news])), [
    'huicui',
  ]);
  assert.deepEqual(ids('公管', getPlaceSearchIndex([], landmarks)), []);
  assert.deepEqual(
    ids(
      '公管',
      getPlaceSearchIndex(
        [{ ...raw('relation/11564915'), insideCampus: false }],
        [],
      ),
    ),
    [],
  );
});

test('every verified venue has a bilingual title that reaches its shipped building or landmark', () => {
  for (const b of buildings.filter((b) => collegeVenues.has(b.id))) {
    const venue = collegeVenues.get(b.id);
    for (const locale of ['zh', 'en'])
      assert.ok(ids(venue[locale]).includes(venue.landmark ?? b.id), b.id);
  }
  for (const id of collegeVenues.keys())
    assert.ok(
      [...buildings, ...landmarks].some((p) => p.id === id),
      id,
    );
});
