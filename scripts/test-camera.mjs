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

test('竖屏桥下镜头沿实际弯曲坡道定位，避免停在挡墙外', async () => {
  const { bridgeEntrancePose } = await import('../lib/campus/camera.ts');
  for (const l of landmarks.filter((l) => l.placeKind === 'bridge')) {
    const pose = bridgeEntrancePose(
      l,
      fitBox(
        entranceBox(l, landmarkBox(l), false),
        landmarkDirection(l, 'entrance'),
        { left: 18, top: 94, width: 298, height: 310 },
        { width: 390, height: 844 },
      ),
    );
    assert.ok(pose.position.distanceTo(pose.target) < 50, l.name);
    let distance = Infinity;
    for (let i = 1; i < l.approachPath.length; i++) {
      const a = l.approachPath[i - 1],
        b = l.approachPath[i];
      const dx = b[0] - a[0],
        dy = b[1] - a[1];
      const t = Math.max(
        0,
        Math.min(
          1,
          ((pose.position.x - a[0]) * dx + (-pose.position.z - a[1]) * dy) /
            (dx * dx + dy * dy),
        ),
      );
      distance = Math.min(
        distance,
        Math.hypot(
          pose.position.x - a[0] - dx * t,
          pose.position.z + a[1] + dy * t,
        ),
      );
    }
    assert.ok(distance < 0.01, `${l.name}: camera is outside the ramp`);
  }
});

test('雕塑近景保留银色主体的脚部、三足和顶部突起', async () => {
  const l = landmarks.find((p) => p.id === 'time-gate');
  const bytes = await readFile(
    new URL('../public/models/time-gate.glb', import.meta.url),
  );
  const gltf = JSON.parse(
    bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)),
  );
  const box = entranceBox(l, landmarkBox(l), false);
  for (const primitive of gltf.meshes.flatMap((m) => m.primitives)) {
    if (gltf.materials[primitive.material].name !== 'timeSilver') continue;
    const bounds = gltf.accessors[primitive.attributes.POSITION];
    assert.ok(
      box.containsPoint(new Vector3(...bounds.min)),
      '脚部不应被近景裁切',
    );
    assert.ok(
      box.containsPoint(new Vector3(...bounds.max)),
      '顶部不应被近景裁切',
    );
  }
});

test('六教南北门近景沿建筑轴线定位，四向入口与三个内院保留', async () => {
  const l = landmarks.find((p) => p.id === 'teaching-six');
  const b = buildings.find((p) => p.landmark === l.id);
  const south = entranceBox(l, landmarkBox(l), false, b.architecture).getCenter(
    new Vector3(),
  );
  const north = entranceBox(l, landmarkBox(l), true, b.architecture).getCenter(
    new Vector3(),
  );
  assert.ok(Math.abs(south.distanceTo(north) - 60) < 0.001);
  assert.ok(north.z < south.z - 58);
  const direction = landmarkDirection(l, 'rear-entrance', b.architecture);
  assert.ok(direction.z < -0.85 && direction.x < 0);
  assert.ok(b.architecture);
  assert.deepEqual(
    b.architecture.entrances.map((e) => e.id),
    ['south', 'north', 'west', 'east'],
  );
  assert.equal(b.polygons[0].length - 1, 3);
  assert.ok(l.additionalReferences.includes('teachingSixEntrances2025'));
});
