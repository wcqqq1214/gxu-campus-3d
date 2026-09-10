import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createBoundary } from '../lib/campus/boundary.ts';
import { DEFAULT_LAYERS } from '../lib/campus/types.ts';
const data = JSON.parse(
  fs.readFileSync(
    new URL('../public/data/campus-boundary.json', import.meta.url),
  ),
);
test('校园边界默认显示，两段闭合轮廓转换为可见虚线且独立于建筑图层', () => {
  const root = createBoundary(data);
  assert.equal(DEFAULT_LAYERS.boundary, true);
  assert.equal(root.children.length, data.rings.length * 2);
  root.children.forEach((line, i) => {
    assert.equal(line.material.depthWrite, false);
    assert.equal(line.material.dashed, i % 2 === 1);
    const positions = line.geometry.getAttribute('instanceStart');
    assert.ok(
      Math.abs(positions.getX(0) - data.rings[Math.floor(i / 2)][0][0]) < 0.001,
    );
    assert.ok(
      Math.abs(positions.getZ(0) + data.rings[Math.floor(i / 2)][0][1]) < 0.001,
    );
    line.geometry.dispose();
    line.material.dispose();
  });
  assert.throws(() => createBoundary({ rings: [[[NaN, 0, 0]]] }));
});
