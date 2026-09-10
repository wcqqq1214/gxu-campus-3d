import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  encodeShare,
  decodeShare,
  cameraBearing,
} from '../lib/campus/share.ts';
import { searchLandmarks } from '../lib/campus/navigation.ts';
const landmarks = JSON.parse(
  await readFile(new URL('../public/data/landmarks.json', import.meta.url)),
);
const ids = landmarks.map((l) => l.id);
test('别名与分类仍限于精选目录', () => {
  assert.deepEqual(
    searchLandmarks(landmarks, '六教').map((l) => l.id),
    ['teaching-six'],
  );
  assert.deepEqual(
    searchLandmarks(landmarks, '新东园门', 'landmark').map((l) => l.id),
    ['new-east-gate'],
  );
  assert.deepEqual(
    searchLandmarks(landmarks, '南宁楼').map((l) => l.id),
    ['teaching-two'],
  );
  assert.equal(searchLandmarks(landmarks, '六教', 'living').length, 0);
  assert.equal(searchLandmarks(landmarks, '', 'landmark').length, 4);
});
test('分享保留地标、相机与光照，输入异常不会生成无效镜头', () => {
  const snapshot = {
    selected: 'library',
    view: 'back',
    preset: 'evening',
    position: [185, 85, 240],
    target: [204, 20, 480],
    span: 70,
  };
  assert.deepEqual(decodeShare(encodeShare(snapshot), ids), snapshot);
  assert.equal(
    decodeShare('#place=way/123&camera=NaN,0,0,0,0,0&span=4', ids),
    null,
  );
  assert.deepEqual(
    decodeShare('#place=library&light=unknown&camera=1,2,3,0,0,0&span=-3', ids),
    { selected: 'library' },
  );
  assert.equal(decodeShare('#camera=0,990000,0,0,0,0&span=10', ids), null);
  assert.equal(cameraBearing({ ...snapshot, position: [204, 85, 580] }), 0);
  assert.equal(cameraBearing({ ...snapshot, position: [304, 85, 480] }), 90);
});
