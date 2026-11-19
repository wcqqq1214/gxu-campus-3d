import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  treeAppearance,
  treeCrownWidthFactor,
  treeInstanceCounts,
  treeRotation,
  treeGroundHeight,
  treeElevation,
  orderTreeGroup,
} from '../lib/campus/vegetation.ts';

const trees = JSON.parse(
  readFileSync(new URL('../public/data/vegetation.json', import.meta.url)),
);
test('删除、重排或跨区块分组不改变保留树位的朝向', () => {
  const angles = new Map(
    trees.map(([x, y]) => [`${x},${y}`, treeRotation(x, y)]),
  );
  for (const rows of [
    trees.slice(1),
    [...trees].reverse(),
    trees.filter((_, i) => i % 3),
  ]) {
    for (const [x, y] of rows) {
      const rotation = treeRotation(x, y);
      assert.equal(rotation, angles.get(`${x},${y}`));
      assert.ok(rotation >= 0 && rotation < Math.PI * 2);
    }
  }
});
test('负坐标、零点和正坐标得到确定的有限角度', () => {
  for (const [x, y] of [
    [-450.1, -0.1],
    [0, 0],
    [450.1, 900.2],
  ]) {
    assert.ok(Number.isFinite(treeRotation(x, y)));
  }
  assert.equal(treeRotation(-0, 0), treeRotation(0, -0));
  assert.notEqual(treeRotation(-450.1, -0.1), treeRotation(450.1, 0.1));
});

test('树木在坡面内插值取高，不能沿用左下网格角点的高度', () => {
  const terrain = {
    bounds: [-10, -10, 10, 10],
    cols: 2,
    rows: 2,
    heights: [0, 4, 6, 10],
  };
  assert.equal(treeGroundHeight(terrain, 0, 0), 5);
  assert.equal(treeGroundHeight(terrain, -5, 5), 5.5);
  assert.equal(treeGroundHeight(terrain, -20, -20), 0);
  assert.ok(Number.isFinite(treeGroundHeight(terrain, 20, 20)));
  assert.equal(treeElevation([0, 0, 9, 0, 2.75], terrain), 2.75);
  assert.equal(treeElevation([0, 0, 9, 0], terrain), 5);
});

test('流畅档在原有数量预算内保留庭院和行道树布局', () => {
  const manifest = JSON.parse(
    readFileSync(new URL('../public/data/models.json', import.meta.url)),
  );
  const priority = manifest.treePriorityPositions;
  assert.ok(priority.length >= 16);
  const key = ([x, y]) => `${x},${y}`;
  const priorityKeys = new Set(priority.map(key));
  const sectors = Map.groupBy(
    trees,
    (r) => `${Math.floor(r[0] / 450)},${Math.floor(r[1] / 450)}`,
  );
  const retained = new Set();
  for (const sector of sectors.values()) {
    const species = [...Map.groupBy(sector, (row) => row[3]).values()];
    const ordered = species.map((rows) => orderTreeGroup(rows, priorityKeys));
    ordered.forEach(({ rows }, i) => {
      assert.equal(rows.length, species[i].length);
      assert.deepEqual(new Set(rows), new Set(species[i]));
    });
    const groups = ordered.map(({ rows, priorityCount }) => ({
      total: rows.length,
      priority: priorityCount,
    }));
    for (const density of [0.55, 0.75, 1]) {
      const counts = treeInstanceCounts(groups, density);
      assert.equal(
        counts.reduce((sum, n) => sum + n, 0),
        groups.reduce((sum, g) => sum + Math.ceil(g.total * density), 0),
      );
      ordered.forEach(({ rows }, i) => {
        assert.ok(counts[i] >= 0 && counts[i] <= rows.length);
        if (density === 0.55)
          for (const row of rows.slice(0, counts[i])) retained.add(key(row));
      });
    }
  }
  for (const point of priority)
    assert.ok(retained.has(key(point)), `Source tree disappeared: ${point}`);
});

test('优先排列保留旧数据顺序和实例属性，不修改输入', () => {
  const rows = [
    [0, 0, 9, 0, 2],
    [10, 10, 11, 0, 3],
    [20, 20, 8, 0, 4],
  ];
  const before = structuredClone(rows);
  assert.equal(orderTreeGroup(rows, new Set()).rows, rows);
  assert.deepEqual(
    orderTreeGroup(rows, new Set(['20,20', '999,999'])),
    { rows: [rows[2], rows[0], rows[1]], priorityCount: 1 },
  );
  assert.deepEqual(rows, before);
});

test('树冠缩放与色调固定于坐标且不超过约定范围', () => {
  for (const [x, y] of trees) {
    const a = treeAppearance(x, y);
    assert.deepEqual(treeAppearance(x, y), a);
    assert.ok(a.width >= 0.75 && a.width <= 1.25);
    assert.ok(a.height >= 0.8 && a.height <= 1.2);
    assert.ok(a.tint.every((v) => Number.isFinite(v) && v > 0.7 && v < 1.2));
  }
  assert.notDeepEqual(treeAppearance(1, 2), treeAppearance(2, 1));
});

test('西宿舍局部冠幅调整只作用于表中阔叶树', () => {
  const widths = JSON.parse(
    readFileSync(new URL('../data/west-dorm-crown-widths.json', import.meta.url)),
  );
  const factors = new Map(widths.map(([x, y, width]) => [`${x},${y}`, width]));
  assert.equal(factors.size, widths.length);
  let adjusted = 0;
  for (const [x, y, , type] of trees) {
    const factor = treeCrownWidthFactor(x, y);
    assert.equal(factor, factors.get(`${x},${y}`) ?? 1);
    if (factor !== 1) {
      assert.ok(factor > 0 && factor < 1);
      assert.equal(type, 0);
      adjusted += 1;
    }
  }
  assert.equal(adjusted, widths.length);
});
