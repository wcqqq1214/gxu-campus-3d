import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { sourceIndex, sourceDates } from '../lib/campus/sources.ts';
const data = JSON.parse(
  await readFile(new URL('../public/data/sources.json', import.meta.url)),
);
const landmarks = JSON.parse(
  await readFile(new URL('../public/data/landmarks.json', import.meta.url)),
);

test('全部地标的主来源和附加来源均可显示，来源ID唯一且链接完整', () => {
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

test('发布时间、拍摄时间与查阅时间分开，不用来源ID或查阅日期冒充拍摄时间', () => {
  assert.equal(
    sourceDates({
      id: 'x2026',
      name: 'x',
      url: 'https://example.com',
      retrievedAt: '2026-09-11',
    }),
    '发布日期未注明 · 拍摄日期未注明 · 查阅：2026-09-11',
  );
  assert.match(
    sourceDates({
      id: 'x',
      name: 'x',
      url: 'https://example.com',
      publishedAt: '2020-01-01',
      capturedAt: '2019',
    }),
    /发布：2020-01-01 · 拍摄：2019/,
  );
});
