import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { treeRotation, treeGroundHeight, treeElevation, prioritizeTreeRows } from '../lib/campus/vegetation.ts';

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

test('流畅档在原有数量预算内保留庭院和行道树布局', () => {
  const manifest = JSON.parse(readFileSync(new URL('../public/data/models.json', import.meta.url)));
  const priority = manifest.treePriorityPositions;
  assert.ok(priority.length >= 16);
  const key = ([x,y]) => `${x},${y}`;
  const sectors = new Map();
  for (const row of trees) {
    const sector = `${Math.floor(row[0]/450)},${Math.floor(row[1]/450)},${row[3]}`;
    if (!sectors.has(sector)) sectors.set(sector,[]);
    sectors.get(sector).push(row);
  }
  const retained = new Set();
  for (const rows of sectors.values()) {
    const ordered = prioritizeTreeRows(rows,priority);
    assert.equal(ordered.length,rows.length);
    assert.deepEqual(new Set(ordered),new Set(rows));
    for (const density of [.55,.75,1]) {
      const shown = ordered.slice(0,Math.ceil(rows.length*density));
      assert.equal(shown.length,Math.ceil(rows.length*density));
      if (density===.55) for (const row of shown) retained.add(key(row));
    }
  }
  for (const point of priority) assert.ok(retained.has(key(point)),`Source tree disappeared: ${point}`);
});

test('优先排列保留旧数据顺序和实例属性，不修改输入', () => {
  const rows=[[0,0,9,0,2],[10,10,11,0,3],[20,20,8,0,4]];
  const before=structuredClone(rows);
  assert.equal(prioritizeTreeRows(rows,[]),rows);
  assert.deepEqual(prioritizeTreeRows(rows,[[20,20],[999,999]]),[rows[2],rows[0],rows[1]]);
  assert.deepEqual(rows,before);
});
