import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
const read = (n) =>
  JSON.parse(fs.readFileSync(new URL('../public/data/' + n, import.meta.url)));
const data = read('basketball.json');
test('篮球场使用独立运动场节点，保持精选目录稳定且来源可查询', () => {
  const bytes = fs.readFileSync(
    new URL('../public/models/base.glb', import.meta.url),
  );
  const size = bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.subarray(20, 20 + size).toString());
  for (const bank of data.banks) {
    const roots = gltf.nodes.filter((n) => n.name === bank.id);
    assert.equal(roots.length, 1);
    assert.equal(roots[0].extras.layer, 'sports');
  }
  for (const id of ['basketball-bank-1379222486', 'basketball-bank-1379222488'])
    assert.ok(
      !gltf.nodes.some((n) => n.name === id),
      `校外球场仍在模型中：${id}`,
    );
  assert.ok(
    !read('landmarks.json').some((l) => l.id.startsWith('basketball-')),
  );
  assert.equal(
    new Set(data.courts.filter((c) => c.osmId).map((c) => c.osmId)).size,
    16,
  );
  const sources = new Set(read('sources.json').sources.map((s) => s.id));
  for (const id of data.sourceRefs) assert.ok(sources.has(id), id);
  assert.equal(read('overview.json').trees, read('vegetation.json').length);
});

test('basketball LODs keep the same ground and full near hardware within the initial budget', () => {
  const manifest = read('models.json');
  const parse = (url) => {
    const raw = fs.readFileSync(new URL('../public/' + url, import.meta.url));
    const end = 20 + raw.readUInt32LE(12);
    const doc = JSON.parse(raw.subarray(20, end));
    return { raw, doc, bin: raw.subarray(end + 8) };
  };
  const base = parse(manifest.base.url);
  assert.equal(manifest.sports.length, data.banks.length);
  assert.ok(manifest.base.bytes + manifest.trees.bytes < 6_000_000);
  for (const asset of manifest.sports) {
    const near = parse(asset.url);
    assert.equal(near.raw.length, asset.bytes);
    assert.equal(createHash('sha256').update(near.raw).digest('hex'), asset.sha256);
    assert.deepEqual(
      asset.bounds,
      data.banks.find((b) => b.id === asset.id).bounds,
    );
    const primitives = (gltf) => {
      const node = gltf.doc.nodes.find((n) => n.name === asset.id);
      assert.equal(node.extras.layer, 'sports');
      return new Map(
        gltf.doc.meshes[node.mesh].primitives.map((p) => [
          gltf.doc.materials[p.material].name,
          p,
        ]),
      );
    };
    const far = primitives(base),
      full = primitives(near);
    assert(!far.has('goalNet'));
    assert(full.has('goalNet'));
    assert(
      base.doc.accessors[far.get('courtOrange').indices].count <
        near.doc.accessors[full.get('courtOrange').indices].count / 4,
    );
    for (const [material, p] of far) {
      if (material === 'courtOrange') continue;
      const payload = (gltf, primitive) => {
        const view =
          gltf.doc.bufferViews[
            primitive.extensions.KHR_draco_mesh_compression.bufferView
          ];
        return gltf.bin.subarray(
          view.byteOffset ?? 0,
          (view.byteOffset ?? 0) + view.byteLength,
        );
      };
      assert.deepEqual(
        payload(base, p),
        payload(near, full.get(material)),
        material,
      );
      assert.deepEqual(
        base.doc.materials[p.material],
        near.doc.materials[full.get(material).material],
      );
    }
  }
});
