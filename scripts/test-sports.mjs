import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { project } from '../lib/campus/math.ts';
const read = async (path) =>
  JSON.parse(
    await readFile(new URL(`../public/data/${path}`, import.meta.url), 'utf8'),
  );
const fields = await read('sports.json');
const trees = await read('vegetation.json');
const terrain = await read('terrain.json');
const geo = await read('geography.geojson');
test('发布 GLB 为两处场地保留独立压缩范围及运动场图层', async () => {
  const bytes = await readFile(
    new URL('../public/models/base.glb', import.meta.url),
  );
  const gltf = JSON.parse(
    bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)),
  );
  for (const field of fields) {
    const nodes = gltf.nodes.filter((n) => n.extras?.sportsId === field.id);
    assert.equal(nodes.length, 1);
    assert.equal(nodes[0].extras.layer, 'sports');
    for (const primitive of gltf.meshes[nodes[0].mesh].primitives) {
      const accessor = gltf.accessors[primitive.attributes.POSITION];
      assert.ok(
        accessor.max.every((v, i) => v - accessor.min[i] < 200),
        '量化范围不能扩展到整个校园',
      );
    }
  }
});
function inside(p, ring) {
  let yes = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i],
      b = ring[j];
    if (
      a[1] > p[1] !== b[1] > p[1] &&
      p[0] < ((b[0] - a[0]) * (p[1] - a[1])) / (b[1] - a[1]) + a[0]
    )
      yes = !yes;
  }
  return yes;
}
function elevation(x, y) {
  const [x0, y0, x1, y1] = terrain.bounds;
  const u = ((x - x0) / (x1 - x0)) * (terrain.cols - 1),
    v = ((y - y0) / (y1 - y0)) * (terrain.rows - 1);
  const i = Math.floor(u),
    j = Math.floor(v),
    a = u - i,
    b = v - j;
  const h = (dx, dy) => terrain.heights[(j + dy) * terrain.cols + i + dx];
  return (
    (h(0, 0) * (1 - a) + h(1, 0) * a) * (1 - b) +
    (h(0, 1) * (1 - a) + h(1, 1) * a) * b
  );
}
test('田径场保留原始内环、独立目录和真实轮廓位置', async () => {
  assert.deepEqual(fields.map((f) => f.osmId).sort(), [
    'relation/12774259',
    'way/759193119',
  ]);
  const sources = (await read('sources.json')).sources;
  for (const f of fields) {
    const raw = geo.features.find((g) => g.id === f.osmId);
    assert.equal(f.osmEditedAt, raw.properties.osmEditedAt);
    assert.ok(inside(f.center, f.ground));
    assert.equal(f.placeKind, 'sports');
    assert.ok(f.sourceRefs.every((id) => sources.some((s) => s.id === id)));
    assert.ok(f.precision.includes('估算'));
    raw.geometry.coordinates[0].forEach((point, i) => {
      const p = project(...point);
      assert.ok(
        Math.hypot(p[0] - f.ground[i][0], p[1] - f.ground[i][1]) < 0.001,
      );
    });
  }
  assert.equal(
    geo.features.find((g) => g.id === 'relation/12774259').geometry.coordinates
      .length,
    2,
  );
});
test('整个内场及跑道下方地形平整，树冠不侵入场内', () => {
  for (const f of fields) {
    let samples = 0;
    for (let x = f.bounds[0]; x < f.bounds[2]; x += 3)
      for (let y = f.bounds[1]; y < f.bounds[3]; y += 3)
        if (inside([x, y], f.ground)) {
          assert.ok(
            Math.abs(elevation(x, y) - f.elevation) < 0.011,
            `${f.id} terrain at ${x},${y}`,
          );
          samples++;
        }
    assert.ok(samples > 1000);
    for (const [x, y, h] of trees) {
      assert.ok(!inside([x, y], f.ground), `${f.id} tree inside`);
      for (let i = 0; i < f.ground.length - 1; i++) {
        const a = f.ground[i],
          b = f.ground[i + 1];
        const dx = b[0] - a[0],
          dy = b[1] - a[1];
        const t = Math.max(
          0,
          Math.min(
            1,
            ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy),
          ),
        );
        assert.ok(
          Math.hypot(x - a[0] - t * dx, y - a[1] - t * dy) > (4 * h) / 9 + 0.98,
        );
      }
    }
  }
});
test('足球场四角和球门位于跑道内侧，两个场地保持各自的方向', () => {
  assert.ok(fields[1].rotation > fields[0].rotation + 0.02);
  for (const f of fields) {
    const inner = f.outerRadius - f.laneCount * f.laneWidth;
    for (const [x, y] of [
      [f.pitchWidth / 2, f.pitchLength / 2],
      [3.66, f.pitchLength / 2 + 2],
    ])
      assert.ok(
        Math.hypot(x, Math.max(0, y - f.straightHalfLength)) < inner - 0.2,
      );
  }
});
