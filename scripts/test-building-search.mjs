import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import {
  buildingLocationLabel,
  searchableBuildings,
  searchBuildings,
  searchLandmarks,
} from '../lib/campus/navigation.ts';
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

test('internal model descriptions and the disputed footprint are not destinations', () => {
  const evidence = read('../data/i18n-name-sources.json');
  const internal = buildings.filter(
    (b) => evidence.entries[b.name]?.status === '技',
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
        searchBuildings(buildings, landmarks, placeName(b.name, locale), locale)
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
    assert.doesNotMatch(b.name, /^校内建筑 \d+$/);
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
