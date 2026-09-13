import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { treeRotation, treeGroundHeight, treeElevation } from '../lib/campus/vegetation.ts';

const trees = JSON.parse(readFileSync(new URL('../public/data/vegetation.json', import.meta.url)));
test('删除、重排或跨区块分组不改变保留树位的朝向', () => {
  const angles = new Map(trees.map(([x,y]) => [`${x},${y}`, treeRotation(x,y)]));
  for (const rows of [trees.slice(1), [...trees].reverse(), trees.filter((_,i) => i % 3)]) {
    for (const [x,y] of rows) {
      const rotation = treeRotation(x,y);
      assert.equal(rotation, angles.get(`${x},${y}`));
      assert.ok(rotation >= 0 && rotation < Math.PI * 2);
    }
  }
});
test('负坐标、零点和正坐标得到确定的有限角度', () => {
  for (const [x,y] of [[-450.1,-0.1], [0,0], [450.1,900.2]]) {
    assert.ok(Number.isFinite(treeRotation(x,y)));
  }
  assert.equal(treeRotation(-0,0), treeRotation(0,-0));
  assert.notEqual(treeRotation(-450.1,-0.1), treeRotation(450.1,0.1));
});

test('树木在坡面内插值取高，不能沿用左下网格角点的高度', () => {
  const terrain = { bounds: [-10,-10,10,10], cols: 2, rows: 2, heights: [0,4,6,10] };
  assert.equal(treeGroundHeight(terrain,0,0),5);
  assert.equal(treeGroundHeight(terrain,-5,5),5.5);
  assert.equal(treeGroundHeight(terrain,-20,-20),0);
  assert.ok(Number.isFinite(treeGroundHeight(terrain,20,20)));
  assert.equal(treeElevation([0,0,9,0,2.75],terrain),2.75);
  assert.equal(treeElevation([0,0,9,0],terrain),5);
});
