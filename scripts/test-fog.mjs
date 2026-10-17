import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { Vector3 } from 'three';
import { campusOverviewPoints, fitPoints } from '../lib/campus/camera.ts';
import { fogRange } from '../lib/campus/sky.ts';

const read = async (name) =>
  JSON.parse(
    await readFile(new URL(`../public/data/${name}.json`, import.meta.url)),
  );
const [boundary, buildings, landmarks] = await Promise.all(
  ['campus-boundary', 'buildings', 'landmarks'].map(read),
);
const points = campusOverviewPoints(boundary.rings, buildings, landmarks);

test('手机全景的实际校界与屋顶不能被雾完全遮蔽，包括展开列表后的取景', () => {
  for (const [width, height, frameWidth, frameHeight] of [
    [390, 844, 294, 311],
    [375, 667, 279, 219],
    [375, 667, 279, 100],
    [1280, 720, 816, 572],
    [1440, 900, 976, 752],
  ]) {
    const { position, target } = fitPoints(
      points,
      new Vector3(0.55, 1.1, 1),
      { left: 18, top: 94, width: frameWidth, height: frameHeight },
      { width, height },
    );
    const back = position.clone().sub(target).normalize();
    for (const preset of ['morning', 'day', 'evening', 'night']) {
      const { near, far } = fogRange(preset, position.distanceTo(target));
      for (const point of points) {
        const depth = position.clone().sub(point).dot(back);
        const t = Math.max(0, Math.min(1, (depth - near) / (far - near)));
        const opacity = t * t * (3 - 2 * t); // Three.js fog_fragment smoothstep
        assert.ok(
          opacity < 0.9,
          `${width}x${height}/${frameHeight} ${preset}: fog=${opacity}`,
        );
      }
      assert.ok(far < 30000, '雾仍在相机远裁剪面以内结束');
    }
  }
});

test('近景和常用桌面取景保留原有雾效，远距离补偿连续且可恢复', () => {
  for (const [preset, near, far] of [
    ['day', 2700, 7800],
    ['night', 2500, 5800],
  ]) {
    for (const distance of [18, 500, 3715, 4000])
      assert.deepEqual(fogRange(preset, distance), { near, far });
    const justOutside = fogRange(preset, 4000.01);
    assert.ok(Math.abs(justOutside.near - near) < 0.02);
    assert.equal(
      fogRange(preset, 12000).far - fogRange(preset, 12000).near,
      far - near,
    );
    assert.deepEqual(fogRange(preset, 500), { near, far });
  }
});
