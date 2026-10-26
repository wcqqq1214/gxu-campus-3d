import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { createPrimitiveDecoder } from './draco-geometry.mjs';
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

test('basketball LODs keep the same ground and full near hardware within the initial budget', async () => {
  const manifest = read('models.json');
  const parse = (url) => {
    const raw = fs.readFileSync(new URL('../public/' + url, import.meta.url));
    const end = 20 + raw.readUInt32LE(12);
    const doc = JSON.parse(raw.subarray(20, end));
    return { raw, doc, bin: raw.subarray(end + 8) };
  };
  const base = parse(manifest.base.url);
  const decodeBase = await createPrimitiveDecoder(base.doc, base.bin);
  // Compression level and vertex deduplication may reorder the encoded stream.
  // Compare every decoded corner attribute and triangle winding instead.
  const triangles = (geometry) => {
    try {
      const attributes = Object.keys(geometry.attributes).sort();
      const corners = Array.from(
        { length: geometry.attributes.position.count },
        (_, i) =>
          JSON.stringify(
            attributes.map((name) => {
              const attribute = geometry.attributes[name];
              return [
                name,
                Array.from(
                  attribute.array.subarray(
                    i * attribute.itemSize,
                    (i + 1) * attribute.itemSize,
                  ),
                ),
              ];
            }),
          ),
      );
      const result = [];
      for (let i = 0; i < geometry.index.count; i += 3) {
        const face = [0, 1, 2].map((j) => corners[geometry.index.array[i + j]]);
        result.push(
          [face, [face[1], face[2], face[0]], [face[2], face[0], face[1]]]
            .map((rotation) => JSON.stringify(rotation))
            .sort()[0],
        );
      }
      return result.sort();
    } finally {
      geometry.dispose();
    }
  };
  assert.equal(manifest.sports.length, data.banks.length);
  const budget = JSON.parse(
    fs.readFileSync(
      new URL('../data/initial-model-budget.json', import.meta.url),
    ),
  );
  assert.ok(
    manifest.base.bytes + manifest.trees.bytes <= budget.hardLimitBytes,
  );
  for (const asset of manifest.sports) {
    const near = parse(asset.url);
    const decodeNear = await createPrimitiveDecoder(near.doc, near.bin);
    assert.equal(near.raw.length, asset.bytes);
    assert.equal(
      createHash('sha256').update(near.raw).digest('hex'),
      asset.sha256,
    );
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
      assert.deepEqual(
        triangles(decodeBase(p)),
        triangles(decodeNear(full.get(material))),
        material,
      );
      assert.deepEqual(
        base.doc.materials[p.material],
        near.doc.materials[full.get(material).material],
      );
    }
  }
});
