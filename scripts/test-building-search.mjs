import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import {
  searchableBuildings,
  searchBuildings,
  searchLandmarks,
} from '../lib/campus/navigation.ts';
const read = (path) =>
  JSON.parse(fs.readFileSync(new URL(path, import.meta.url), 'utf8'));
const buildings = read('../public/data/buildings.json');
const landmarks = read('../public/data/landmarks.json');

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
