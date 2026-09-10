import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { PerspectiveCamera, Vector3 } from 'three';
import {
  fitBox,
  landmarkBox,
  landmarkDirection,
  entranceBox,
} from '../lib/campus/camera.ts';
const landmarks = JSON.parse(
  await readFile(new URL('../public/data/landmarks.json', import.meta.url)),
);
const buildings = JSON.parse(
  await readFile(new URL('../public/data/buildings.json', import.meta.url)),
);
test('手机、桌面及横屏的完整建筑构图避开面板，不截断楼翼或塔楼', () => {
  for (const [width, height, left, top, w, h] of [
    [1280, 720, 368, 106, 816, 572],
    [390, 844, 18, 94, 298, 310],
    [390, 844, 18, 94, 298, 664],
    [844, 390, 328, 106, 446, 242],
  ])
    for (const l of landmarks)
      for (const view of ['oblique', 'front', 'back', 'top']) {
        const frame = { left, top, width: w, height: h };
        const box = landmarkBox(l);
        const { position, target } = fitBox(
          box,
          landmarkDirection(l, view),
          frame,
          { width, height },
        );
        const camera = new PerspectiveCamera(41, width / height, 1, 30000);
        camera.setViewOffset(
          width,
          height,
          width / 2 - left - w / 2,
          height / 2 - top - h / 2,
          width,
          height,
        );
        camera.position.copy(position);
        camera.lookAt(target);
        camera.updateMatrixWorld();
        for (const x of [box.min.x, box.max.x])
          for (const y of [box.min.y, box.max.y])
            for (const z of [box.min.z, box.max.z]) {
              const p = new Vector3(x, y, z).project(camera);
              const px = ((p.x + 1) * width) / 2,
                py = ((1 - p.y) * height) / 2;
              assert.ok(
                px > left && px < left + w && py > top && py < top + h,
                `${l.id}/${view} at ${width}x${height}: ${px},${py}`,
              );
              assert.ok(p.z > 0 && p.z < 1);
            }
      }
});
test('汇学堂正面为东向；图书馆两侧入口沿实际建筑轴线定位', () => {
  assert.ok(
    landmarkDirection(
      landmarks.find((p) => p.id === 'huixue'),
      'front',
    ).x > 0.9,
  );
  const l = landmarks.find((p) => p.id === 'library');
  const b = buildings.find((p) => p.landmark === l.id);
  const south = entranceBox(l, landmarkBox(l), false, b.architecture).getCenter(
    new Vector3(),
  );
  const north = entranceBox(l, landmarkBox(l), true, b.architecture).getCenter(
    new Vector3(),
  );
  assert.ok(north.z < south.z - 65);
  assert.ok(north.x < south.x - 10);
  assert.ok(landmarkDirection(l, 'back').z < -0.9);
});
