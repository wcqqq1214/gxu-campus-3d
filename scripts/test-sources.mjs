import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { sourceIndex } from '../lib/campus/sources.ts';
const data = JSON.parse(
  await readFile(new URL('../public/data/sources.json', import.meta.url)),
);
const landmarks = JSON.parse(
  await readFile(new URL('../public/data/landmarks.json', import.meta.url)),
);

test('全部地标的主来源和附加来源均可解析，来源ID唯一且链接完整', () => {
  const refs = sourceIndex(data.sources);
  assert.equal(
    Object.keys(refs).length,
    data.sources.length,
    'duplicate source IDs',
  );
  for (const place of landmarks) {
    for (const id of [place.reference, ...(place.additionalReferences ?? [])]) {
      const source = refs[id];
      assert.ok(source, `${place.id}: missing ${id}`);
      assert.ok(source.name.trim(), `${id}: missing name`);
      assert.ok(['http:', 'https:'].includes(new URL(source.url).protocol), id);
    }
  }
  assert.ok(refs.huicuiExterior2020.name.includes('荟萃'));
});

test('建模依据分类覆盖全部地点，并与可再生成的源目录一致', async () => {
  const catalogue = JSON.parse(
    await readFile(new URL('../data/landmarks.json', import.meta.url)),
  );
  const sculptures = JSON.parse(
    await readFile(new URL('../data/sculptures.json', import.meta.url)),
  );
  for (const place of landmarks) {
    assert.ok(
      ['photo', 'type', 'inferred'].includes(place.modelingBasis),
      place.id,
    );
    const source = [...catalogue, ...sculptures].find(
      (item) => item.id === place.id,
    );
    if (source) {
      assert.equal(place.modelingBasis, source.modelingBasis, place.id);
      assert.equal(place.description, source.description, place.id);
    }
  }
  assert.equal(
    landmarks.find((p) => p.id === 'teaching-two').modelingBasis,
    'type',
  );
  for (const id of ['new-east-gate', 'bocui-bridge', 'huixian-bridge']) {
    assert.equal(landmarks.find((p) => p.id === id).modelingBasis, 'inferred');
  }
});
