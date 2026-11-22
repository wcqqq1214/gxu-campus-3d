import test from 'node:test';
import assert from 'node:assert/strict';
import { BoxGeometry, Group, Mesh } from 'three';
import { landmarkLabelAnchor } from '../lib/campus/labels.ts';
const landmark = {
  center: [-50, 30],
  bounds: [0, 0, 20, 40],
  elevation: 0,
  height: 30,
};
test('锚点以高处主体而非入口铺装或错误中心定位', () => {
  const model = new Group();
  const body = new Mesh(new BoxGeometry(20, 30, 40));
  body.position.set(10, 15, -20);
  model.add(body);
  const apron = new Mesh(new BoxGeometry(120, 1, 120));
  apron.position.set(-35, 0, 0);
  model.add(apron);
  assert.deepEqual(
    landmarkLabelAnchor(landmark, model).toArray(),
    [10, 30.6, -20],
  );
  assert.deepEqual(landmarkLabelAnchor(landmark).toArray(), [10, 30.6, -20]);
  model.position.x = 25;
  assert.deepEqual(
    landmarkLabelAnchor(landmark, model).toArray(),
    [35, 30.6, -20],
  );
});
