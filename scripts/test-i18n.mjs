import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import ts from 'typescript';
import { campusNames } from '../lib/campus/i18n/names.ts';
import { englishMessages } from '../lib/campus/i18n/messages.ts';
import { englishDescriptions } from '../lib/campus/i18n/descriptions.ts';
import { placeName, statusText, translate } from '../lib/campus/i18n/index.ts';
import { searchLandmarks } from '../lib/campus/navigation.ts';
const read = (path) =>
  JSON.parse(fs.readFileSync(new URL(path, import.meta.url), 'utf8'));
const landmarks = read('../public/data/landmarks.json');
test('every named map feature has an explicit bilingual entry and provenance', () => {
  const evidence = read('../data/i18n-name-sources.json');
  function walk(value) {
    if (Array.isArray(value)) value.forEach(walk);
    else if (value && typeof value === 'object') {
      if (typeof value.name === 'string' && value.name.trim()) {
        assert.ok(campusNames[value.name], value.name);
        assert.ok(evidence.entries[value.name], value.name);
        assert.ok(
          !/\p{Script=Han}/u.test(placeName(value.name, 'en')),
          value.name,
        );
      }
      Object.values(value).forEach(walk);
    }
  }
  for (const file of fs.readdirSync(
    new URL('../public/data/', import.meta.url),
  )) {
    if (/\.(json|geojson)$/.test(file) && file !== 'sources.json')
      walk(read('../public/data/' + file));
  }
  for (const row of Object.values(evidence.entries))
    for (const source of row.sources)
      assert.ok(evidence.sources[source], source);
});
test('agreed names override presentation while unresolved Chinese names remain intact', () => {
  assert.equal(placeName('新东门', 'zh'), '新东园门');
  assert.equal(placeName('新东门', 'en'), 'Xindongyuan Gate');
  assert.equal(placeName('数学与信息科学学院', 'en'), 'School of Mathematics');
  assert.equal(placeName('国际学院', 'zh'), '原国际学院楼');
  assert.equal(
    placeName('计算机与电子信息学院', 'en'),
    'School of Computer, Electronics and Information',
  );
  for (const name of [
    '广西碳酸钙产业化工工程院',
    '物理资治楼',
    '北8',
    '学员楼',
    '校长楼',
  ])
    assert.equal(placeName(name, 'zh'), name);
  assert.notEqual(placeName('镜湖', 'en'), placeName('鉴湖', 'en'));
  assert.notEqual(placeName('荷湖', 'en'), placeName('莲湖', 'en'));
});
test('English and Chinese search resolve the same stable landmark IDs', () => {
  for (const [term, id] of [
    ['LIBRARY', 'library'],
    ['图书馆', 'library'],
    ['六教', 'teaching-six'],
    ['No. 6', 'teaching-six'],
    ['计电', 'computer'],
    ['School of Computer and Electronic Information', 'computer'],
    ['新东门', 'new-east-gate'],
    ['Xindongyuan', 'new-east-gate'],
  ]) {
    assert.ok(
      searchLandmarks(landmarks, term).some((place) => place.id === id),
      term,
    );
  }
  assert.equal(searchLandmarks(landmarks, '').length, 20);
  assert.deepEqual(searchLandmarks(landmarks, 'Mathematics'), []); // No new navigable entities.
});
test('in-flight progress is translated from the same message after switching language', () => {
  assert.equal(translate('en', '{count} 处', { count: 1 }), '1 place');
  const message = {
    text: '正在细化{name} · {percent}%',
    values: { name: '新东门', percent: 42 },
  };
  assert.equal(statusText('zh', message), '正在细化新东园门 · 42%');
  assert.equal(
    statusText('en', message),
    'Loading details: Xindongyuan Gate · 42%',
  );
  assert.equal(
    translate('en', '返回 {name}', { name: 'Library' }),
    'Back to Library',
  );
});
test('all displayed landmark descriptions and static UI messages have English translations', () => {
  for (const place of landmarks)
    assert.ok(englishDescriptions[place.id], place.id);
  for (const [zh, en] of Object.entries(englishMessages)) {
    assert.deepEqual(
      [...zh.matchAll(/\{\w+\}/g)].map((x) => x[0]).sort(),
      [...en.matchAll(/\{\w+\}/g)].map((x) => x[0]).sort(),
      zh,
    );
  }
  for (const path of [
    '../app/page.tsx',
    '../components/campus-minimap.tsx',
    '../components/campus-locale.tsx',
    '../components/ui/dialog.tsx',
    '../lib/campus/scene.ts',
  ]) {
    const source = fs.readFileSync(new URL(path, import.meta.url), 'utf8');
    const ast = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true);
    function walk(node) {
      if (
        ts.isCallExpression(node) &&
        ['t', 'setStatus', 'notify'].includes(node.expression.getText(ast)) &&
        ts.isStringLiteral(node.arguments[0]) &&
        /\p{Script=Han}/u.test(node.arguments[0].text)
      )
        assert.ok(
          englishMessages[node.arguments[0].text],
          node.arguments[0].text,
        );
      if (ts.isJsxText(node))
        assert.ok(!/\p{Script=Han}/u.test(node.text), node.text);
      ts.forEachChild(node, walk);
    }
    walk(ast);
  }
});
