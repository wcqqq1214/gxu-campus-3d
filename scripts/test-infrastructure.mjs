import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  searchLandmarks,
  navigationFootprints,
} from '../lib/campus/navigation.ts';

const read = async (name) =>
  JSON.parse(
    await readFile(new URL(`../public/data/${name}`, import.meta.url)),
  );
const data = await read('infrastructure.json');
const geo = await read('geography.geojson');
const landmarks = await read('landmarks.json');
const buildings = await read('buildings.json');
const terrain = await read('terrain.json');
const sources = await read('sources.json');
const ids = ['chongzuo-bridge', 'bocui-bridge', 'huixian-bridge'];

test('农院路保留来源几何，公共道路属性与校界展示掩膜分开', () => {
  assert.equal(data.corridor.publicRoad, true);
  assert.equal(data.corridor.insideCampus, false);
  assert.ok(
    data.corridor.lengthMeters > 2000 && data.corridor.lengthMeters < 2400,
  );
  assert.equal(data.snapshotAt, '2026-09-10T16:33:06Z');
  for (const ref of data.corridor.sourceWays) {
    const feature = geo.features.find((f) => f.id === ref.osmId);
    assert.equal(feature.properties.insideCampus, false);
    assert.equal(feature.properties.osmVersion, ref.osmVersion);
    assert.ok(ref.osmEditedAt <= data.snapshotAt);
  }
  assert.ok(geo.features.find((f) => f.id === 'campus'));
  assert.ok(
    geo.features.find((f) => f.id === 'campus-display-area').properties.derived,
  );
  assert.ok(
    geo.features.find((f) => f.id === 'nongyuan-public-corridor').properties
      .derived,
  );
});

test('立交上下层分离，短坡道也连续接回原校道', () => {
  assert.deepEqual(
    data.bridges.map((b) => b.id),
    ids,
  );
  for (const b of data.bridges) {
    assert.ok(
      Math.abs(
        b.deckElevation -
          b.slabThickness -
          b.beamDepth -
          b.floorElevation -
          b.clearance,
      ) < 1e-6,
    );
    assert.ok(b.clearance >= 4.2);
    for (const p of [b.underpass[0], b.underpass.at(-1)])
      assert.ok(Math.abs(p[2] - p[3]) < 0.005, `${b.name} ramp endpoint`);
    assert.ok(
      b.underpass.some((p) => Math.abs(p[2] - b.floorElevation) < 0.005),
    );
    assert.equal(
      geo.features.find((f) => f.id === b.osmId).properties.tags.layer,
      '1',
    );
    assert.ok(b.dimensionBasis.includes('估算'));
  }
});

test('桥上沥青覆盖完整桥段并在两端等高接回道路', () => {
  const path = data.corridor.path;
  for (let i = 1; i < path.length; i++)
    assert.ok(
      Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]) > 1.4,
      'bridge endpoint must not create a tiny segment with folded road edges',
    );
  for (const b of data.bridges) {
    const ends = [b.upper[0], b.upper.at(-1)].map((q) => {
      const index = path.findIndex(
        (p) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-6,
      );
      assert.ok(index >= 0, `${b.name}: missing exact deck endpoint`);
      return index;
    });
    const [start, end] = ends.sort((a, b) => a - b);
    for (const p of path.slice(start, end + 1))
      assert.ok(
        Math.abs(p[2] - b.deckElevation) < 0.001,
        `${b.name}: asphalt dips into deck near an end`,
      );
  }
});

function inTriangle(p, a, b, c) {
  const sign = (a, b, p) =>
    (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
  const signs = [sign(a, b, p), sign(b, c, p), sign(c, a, p)];
  return signs.every((n) => n >= -1e-7) || signs.every((n) => n <= 1e-7);
}
test('粗 DEM 与替换三角形不会填住三处桥洞', () => {
  const [x0, y0, x1, y1] = terrain.bounds;
  for (const b of data.bridges) {
    const bearing = (b.frontBearing * Math.PI) / 180;
    for (const side of [-1, 1])
      for (const offset of [2.5, 7.4]) {
        // Both traffic lanes AND the raised pedestrian paths need terrain cuts.
        const p = [
          b.center[0] + Math.cos(bearing) * side * offset,
          b.center[1] - Math.sin(bearing) * side * offset,
        ];
        const i = Math.floor(((p[0] - x0) / (x1 - x0)) * (terrain.cols - 1));
        const j = Math.floor(((p[1] - y0) / (y1 - y0)) * (terrain.rows - 1));
        assert.ok(
          data.terrainCells.includes(j * (terrain.cols - 1) + i),
          b.name,
        );
        for (const patch of data.terrainPatch)
          for (let k = 0; k < patch.triangles.length; k += 3)
            assert.ok(
              !inTriangle(
                p,
                ...patch.triangles
                  .slice(k, k + 3)
                  .map((n) => patch.vertices[n]),
              ),
              `${b.name}: filled terrain void`,
            );
      }
  }
});

test('仅三座主要桥梁加入精选导航，拾取跟随道路图层与真实桥轴', () => {
  assert.deepEqual(
    searchLandmarks(landmarks, '农院路').map((l) => l.id),
    ids,
  );
  assert.deepEqual(
    searchLandmarks(landmarks, '', 'infrastructure').map((l) => l.id),
    ids,
  );
  const picks = navigationFootprints(buildings, landmarks);
  for (const id of ids) {
    assert.equal(picks.find((p) => p.id === id).layer, 'roads');
    const l = landmarks.find((l) => l.id === id);
    assert.deepEqual(
      picks.find((p) => p.id === id).polygons[0][0],
      l.pickPolygon,
    );
    assert.ok(l.detail.includes('估算'));
    for (const ref of l.sourceRefs)
      assert.ok(
        sources.sources.some((s) => s.id === ref),
        ref,
      );
  }
  assert.equal(data.lakeBridges.length, 7);
  for (const b of data.lakeBridges) {
    assert.ok(!landmarks.some((l) => l.id === b.id));
    assert.ok(data.replaceSurfaceIds.includes(b.osmId));
  }
});

test('农院路分段首尾衔接，近景桥梁模型可以独立流送', async () => {
  const manifest = await read('models.json');
  const roads = data.chunks.filter((c) => c.kind === 'corridor');
  for (let i = 1; i < roads.length; i++) {
    assert.deepEqual(roads[i - 1].path.at(-1), roads[i].path[0]);
    // Shared normals also keep the two sidewalk edges aligned on curves.
    assert.deepEqual(roads[i - 1].frames.at(-1), roads[i].frames[0]);
  }
  assert.equal(manifest.infrastructure.length, data.chunks.length);
  for (const id of ids) assert.ok(manifest.landmarks.some((l) => l.id === id));
  assert.ok(
    manifest.infrastructure.every(
      (a) => a.bytes < 1_000_000 && a.bounds?.length === 4,
    ),
  );
});
