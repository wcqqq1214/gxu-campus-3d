import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, stat } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import {
  project,
  unproject,
  isTap,
  nextTourIndex,
} from '../lib/campus/math.ts';
const json = async (name) =>
  JSON.parse(
    await readFile(
      new URL(`../public/data/${name}.json`, import.meta.url),
      'utf8',
    ),
  );
const buildings = await json('buildings'),
  landmarks = await json('landmarks'),
  manifest = await json('models');
const geo = JSON.parse(
  await readFile(
    new URL('../public/data/geography.geojson', import.meta.url),
    'utf8',
  ),
);
function glbJson(buffer) {
  assert.equal(buffer.toString('ascii', 0, 4), 'glTF');
  assert.equal(buffer.readUInt32LE(4), 2);
  assert.equal(buffer.readUInt32LE(8), buffer.length);
  return JSON.parse(buffer.toString('utf8', 20, 20 + buffer.readUInt32LE(12)));
}
test('米制坐标往返与南北方向', () => {
  for (const p of [
    [108.28453, 22.83677],
    [108.297, 22.859],
    [108.279, 22.849],
  ]) {
    const q = unproject(...project(...p));
    assert.ok(Math.abs(q[0] - p[0]) < 1e-10 && Math.abs(q[1] - p[1]) < 1e-10);
  }
  assert.ok(project(108.2882, 22.84715 + 0.001)[1] > 111);
  assert.ok(Math.abs(project(108.2892, 22.84715)[0] - 102.6) < 0.5);
});
test('拖拽、长按和双指不触发点选', () => {
  const p = { x: 100, y: 200, time: 0 };
  assert.ok(isTap(p, { x: 102, y: 203, time: 200 }, 4));
  assert.ok(!isTap(p, { ...p, time: 200 }, 70));
  assert.ok(!isTap(p, { ...p, time: 700 }, 0));
  assert.ok(!isTap(p, { ...p, time: 200 }, 999));
  assert.equal(nextTourIndex(9, 10), 0);
  assert.equal(nextTourIndex(0, 0), 0);
});
test('关系去重、要素 ID 与目录互相对应', async () => {
  const ids = buildings.map((b) => b.id);
  assert.equal(new Set(ids).size, ids.length);
  const raw = JSON.parse(
    gunzipSync(
      await readFile(
        new URL('../data/snapshots/osm-2026-09-09.json.gz', import.meta.url),
      ),
    ),
  );
  for (const e of raw.elements.filter(
    (e) => e.type === 'relation' && ids.includes(`relation/${e.id}`),
  )) {
    for (const member of e.members.filter((m) => m.type === 'way'))
      assert.ok(
        !ids.includes(`way/${member.ref}`),
        `重复关系成员 ${member.ref}`,
      );
  }
  for (const b of buildings) {
    const f = geo.features.find((f) => f.id === b.id);
    assert.ok(f);
    assert.equal(f.properties.osmEditedAt, b.osmEditedAt);
    assert.ok(b.height > 0 && Number.isFinite(b.elevation));
    assert.equal(b.sourceUrl, `https://www.openstreetmap.org/${b.id}`);
  }
});
test('庭院内环、三角面与真实轮廓保留', () => {
  let holes = 0;
  for (const b of buildings) {
    b.polygons.forEach((poly, i) => {
      holes += poly.length - 1;
      const vertices = poly.reduce((n, r) => n + r.length - 1, 0);
      for (const ring of poly) assert.deepEqual(ring[0], ring.at(-1));
      assert.equal(b.roofTriangles[i].length % 3, 0);
      assert.ok(
        b.roofTriangles[i].every(
          (v) => Number.isInteger(v) && v >= 0 && v < vertices,
        ),
      );
    });
  }
  assert.ok(holes >= 15, `内院数量异常 ${holes}`);
  assert.ok(
    buildings
      .find((b) => b.landmark === 'teaching-six')
      .polygons.some((p) => p.length > 1),
  );
});
test('地标定位与校园南北关系', () => {
  assert.equal(landmarks.length, 10);
  assert.ok(
    landmarks.find((l) => l.id === 'south-gate').center[1] <
      landmarks.find((l) => l.id === 'laboratory').center[1],
  );
  assert.ok(
    landmarks.find((l) => l.id === 'library').center[0] >
      landmarks.find((l) => l.id === 'stadium').center[0],
  );
  for (const l of landmarks) {
    assert.ok(l.sourceUrl.startsWith('https://'));
    assert.ok(l.reference);
    if (l.osmId)
      assert.equal(buildings.find((b) => b.id === l.osmId)?.landmark, l.id);
  }
});
test('GLB 资源、压缩、自包含纹理和分区映射', async () => {
  for (const a of [
    manifest.base,
    manifest.trees,
    ...manifest.zones,
    ...manifest.landmarks,
  ]) {
    const bytes = await readFile(
      new URL(`../public/${a.url}`, import.meta.url),
    );
    assert.equal(bytes.length, a.bytes);
    const d = glbJson(bytes);
    assert.ok(d.extensionsRequired.includes('KHR_draco_mesh_compression'));
    assert.ok(d.nodes?.length);
    for (const image of d.images ?? [])
      assert.ok(image.bufferView !== undefined, '纹理必须嵌入 GLB');
    if (a.id && manifest.landmarks.includes(a))
      assert.ok(d.nodes.some((n) => n.extras?.landmark === a.id));
  }
  const assigned = manifest.zones.flatMap((z) => z.featureIds);
  assert.equal(new Set(assigned).size, assigned.length);
  assert.deepEqual(
    new Set(assigned),
    new Set(
      buildings.filter((b) => b.insideCampus && !b.landmark).map((b) => b.id),
    ),
  );
});
test('基础模型和纹理同时满足精细 12 MB、流畅 6 MB 预算', async () => {
  const total = manifest.base.bytes + manifest.trees.bytes;
  assert.ok(total <= 6_000_000, `${total} bytes`);
  assert.ok(total <= 12_000_000);
  assert.ok(
    (await stat(new URL('../blender/gxu-campus.blend', import.meta.url))).size >
      1_000_000,
  );
});
test('来源日期字段和高程原始值可追溯', async () => {
  const sources = await json('sources');
  for (const s of sources.sources) {
    assert.ok(
      'publishedAt' in s && 'capturedAt' in s && s.retrievedAt && s.url,
    );
  }
  const terrain = await json('terrain');
  assert.equal(terrain.heights.length, terrain.cols * terrain.rows);
  assert.equal(terrain.rawHeights.length, terrain.heights.length);
  assert.ok(terrain.heights.every(Number.isFinite));
});
