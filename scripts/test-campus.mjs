import {
  searchLandmarks,
  navigableBuildings,
} from '../lib/campus/navigation.ts';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, stat } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import { createHash } from 'node:crypto';
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
  assert.equal(landmarks.length, 11);
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
test('现南门绑定真实门楼且不重复导出，汇学堂从东侧进入', async () => {
  const gate = landmarks.find((l) => l.id === 'south-gate');
  const mapped = buildings.find((b) => b.id === gate.osmId);
  assert.equal(mapped.tags.man_made, 'ceremonial_gate');
  assert.deepEqual(gate.bounds, mapped.bounds);
  assert.deepEqual(gate.center, mapped.center);
  assert.equal(mapped.landmark, gate.id);
  assert.equal(gate.reference, 'gate2026');
  assert.ok(gate.additionalReferences.includes('gate2024'));
  assert.ok(!manifest.zones.some((z) => z.featureIds.includes(gate.osmId)));
  const base = glbJson(
    await readFile(new URL('../public/models/base.glb', import.meta.url)),
  );
  assert.equal(
    base.nodes.filter((n) => n.extras?.landmark === gate.id).length,
    1,
  );
  for (const gltf of [
    base,
    glbJson(
      await readFile(
        new URL('../public/models/south-gate.glb', import.meta.url),
      ),
    ),
  ]) {
    const node = gltf.nodes.find((n) => n.extras?.landmark === gate.id);
    const positions = gltf.meshes[node.mesh].primitives.map(
      (p) => gltf.accessors[p.attributes.POSITION],
    );
    const minX = Math.min(...positions.map((p) => p.min[0]));
    const maxX = Math.max(...positions.map((p) => p.max[0]));
    assert.ok(
      Math.abs(minX - gate.bounds[0]) < 0.2 &&
        Math.abs(maxX - gate.bounds[2]) < 0.2,
      '基础与近景南门均须保持真实轮廓宽度',
    );
  }
  const hui = landmarks.find((l) => l.id === 'huixue');
  assert.equal(hui.frontBearing, 90);
  assert.ok(hui.cameraOffset[0] > Math.abs(hui.cameraOffset[2]));
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
    assert.equal(createHash('sha256').update(bytes).digest('hex'), a.sha256);
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

test('索引、搜索和拾取仅使用精选地标目录', () => {
  assert.equal(searchLandmarks(landmarks, '').length, 11);
  assert.deepEqual(
    searchLandmarks(landmarks, ' 图书馆 ').map((p) => p.id),
    ['library'],
  );
  assert.deepEqual(
    searchLandmarks(landmarks, '留学生').map((p) => p.id),
    ['international-residence'],
  );
  const ordinary = buildings.find(
    (b) => !b.landmark && b.name.startsWith('校内建筑'),
  );
  assert.equal(searchLandmarks(landmarks, ordinary.name).length, 0);
  assert.equal(searchLandmarks(landmarks, ordinary.id).length, 0);
  const picks = navigableBuildings(buildings, landmarks);
  assert.equal(picks.length, landmarks.filter((l) => l.osmId).length);
  assert.ok(picks.every((b) => landmarks.some((l) => l.id === b.landmark)));
  assert.ok(!picks.some((b) => b.id === ordinary.id));
});
test('新公寓绑定现有 24 层轮廓，图书馆局部裁剪保留内院', () => {
  const residence = landmarks.find((l) => l.id === 'international-residence');
  assert.equal(residence.osmId, 'way/1076517227');
  const b = buildings.find((b) => b.id === residence.osmId);
  assert.equal(b.levels, 24);
  assert.equal(b.category, 'living');
  const library = buildings.find((b) => b.landmark === 'library');
  assert.ok(
    Math.abs((library.architecture.angle * 180) / Math.PI - 11.615) < 0.01,
  );
  const parts = library.architecture.parts;
  assert.equal(parts.length, 5);
  const ringArea = (ring) =>
    ring
      .slice(1)
      .reduce((sum, b, i) => sum + ring[i][0] * b[1] - b[0] * ring[i][1], 0) /
    2;
  const area = (polys) =>
    polys.reduce(
      (sum, p) =>
        sum +
        Math.abs(ringArea(p[0])) -
        p.slice(1).reduce((s, r) => s + Math.abs(ringArea(r)), 0),
      0,
    );
  assert.ok(
    Math.abs(
      parts.reduce((s, p) => s + area(p.polygons), 0) - area(library.polygons),
    ) < 0.001,
  );
});
test('图书馆与公寓入口的树冠避让台阶和柱廊', async () => {
  const trees = await json('vegetation');
  for (const { key, bounds } of [
    { key: 'library', bounds: [-23, -45.5, 27, -35] },
    { key: 'international-residence', bounds: [-3, -32, 18, -24] },
  ]) {
    const e = buildings.find((b) => b.landmark === key).architecture;
    for (const [x, y, height] of trees) {
      const dx = x - e.origin[0],
        dy = y - e.origin[1];
      const u = dx * Math.cos(e.angle) + dy * Math.sin(e.angle),
        v = -dx * Math.sin(e.angle) + dy * Math.cos(e.angle);
      const distance = Math.hypot(
        Math.max(bounds[0] - u, 0, u - bounds[2]),
        Math.max(bounds[1] - v, 0, v - bounds[3]),
      );
      assert.ok(
        distance > (4 * height) / 9 + 1,
        `${key}: tree ${x},${y} blocks the entry`,
      );
    }
  }
});
