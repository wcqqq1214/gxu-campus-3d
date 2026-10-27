import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { RUNTIME_BUILDING_FIELDS, runtimeBuildings } from './runtime-data.mjs';

const read = async (path) =>
  readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const buildings = JSON.parse(await read('public/data/buildings.json'));

test('运行时建筑字段与前端 Building 类型一致', async () => {
  const types = await read('lib/campus/types.ts');
  const body = types.match(/export interface Building \{([\s\S]*?)\n\}/)?.[1];
  assert.ok(body, 'Building interface not found');
  const fields = [...body.matchAll(/^ {2}(\w+)\??:/gm)].map((m) => m[1]);
  const order = (a, b) => a.localeCompare(b);
  assert.deepEqual(
    [...fields].sort(order),
    [...RUNTIME_BUILDING_FIELDS].sort(order),
  );
});

test('运行时建筑数据保留前端字段，轮廓只做厘米级取整', () => {
  const slim = runtimeBuildings(buildings);
  assert.equal(slim.length, buildings.length);
  slim.forEach((record, i) => {
    const source = buildings[i];
    for (const field of Object.keys(record))
      assert.ok(RUNTIME_BUILDING_FIELDS.includes(field), field);
    for (const field of RUNTIME_BUILDING_FIELDS) {
      assert.equal(field in record, field in source, `${source.id} ${field}`);
      if (field !== 'polygons' && field in source)
        assert.deepEqual(record[field], source[field]);
    }
    assert.equal(record.polygons.length, source.polygons.length);
    record.polygons.forEach((polygon, p) => {
      assert.equal(polygon.length, source.polygons[p].length);
      polygon.forEach((ring, r) => {
        const original = source.polygons[p][r];
        assert.equal(ring.length, original.length);
        ring.forEach((vertex, v) => {
          for (let k = 0; k < 2; k++)
            assert.ok(Math.abs(vertex[k] - original[v][k]) <= 0.005 + 1e-9);
          // Rounding must not collapse an edge that existed in the source.
          const next = ring[(v + 1) % ring.length];
          const sourceNext = original[(v + 1) % original.length];
          if (
            original[v][0] !== sourceNext[0] ||
            original[v][1] !== sourceNext[1]
          )
            assert.ok(vertex[0] !== next[0] || vertex[1] !== next[1]);
        });
      });
    });
  });
});

test('运行时建筑数据不超过完整记录的一半', () => {
  const full = JSON.stringify(buildings).length;
  const slim = JSON.stringify(runtimeBuildings(buildings)).length;
  assert.ok(slim < full / 2, `${slim} / ${full}`);
});
