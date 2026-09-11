import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { disposeObject } from '../lib/campus/resources.ts';

test('释放区块时保护共享几何、材质及图片，最后使用者移除后各释放一次', () => {
  const count = { geometry: 0, material: 0, texture: 0, image: 0 };
  const image = { close: () => count.image++ };
  const texture = new THREE.Texture(image);
  const geometry = new THREE.BoxGeometry();
  const material = new THREE.MeshStandardMaterial({ map: texture });
  geometry.addEventListener('dispose', () => count.geometry++);
  material.addEventListener('dispose', () => count.material++);
  texture.addEventListener('dispose', () => count.texture++);
  const first = new THREE.Mesh(geometry, material);
  const second = new THREE.Mesh(geometry, material);
  const scene = new THREE.Scene();
  scene.add(first, second);
  scene.remove(first);
  disposeObject(first, [scene]);
  assert.deepEqual(count, { geometry: 0, material: 0, texture: 0, image: 0 });
  scene.remove(second);
  disposeObject(second, [scene]);
  assert.deepEqual(count, { geometry: 1, material: 1, texture: 1, image: 1 });
});

test('不同纹理引用同一位图时，位图在最后一份纹理释放后只关闭一次', () => {
  let closes = 0;
  const image = { close: () => closes++ };
  const a = new THREE.Texture(image),
    b = new THREE.Texture(image);
  const first = new THREE.Mesh(
    new THREE.BoxGeometry(),
    new THREE.MeshBasicMaterial({ map: a }),
  );
  const second = new THREE.Mesh(
    new THREE.BoxGeometry(),
    new THREE.MeshBasicMaterial({ map: b }),
  );
  disposeObject(first, [second]);
  assert.equal(closes, 0);
  disposeObject(second);
  assert.equal(closes, 1);
});

test('实例缓冲和阴影render target在销毁时释放，重复挂载清理无遗漏', () => {
  let instances = 0,
    shadowMaps = 0,
    images = 0;
  for (let cycle = 0; cycle < 30; cycle++) {
    const texture = new THREE.Texture({ close: () => images++ });
    const inst = new THREE.InstancedMesh(
      new THREE.BoxGeometry(),
      new THREE.MeshStandardMaterial({ map: texture }),
      2,
    );
    inst.addEventListener('dispose', () => instances++);
    const sun = new THREE.DirectionalLight();
    sun.shadow.map = new THREE.WebGLRenderTarget(16, 16);
    sun.shadow.map.addEventListener('dispose', () => shadowMaps++);
    const scene = new THREE.Scene();
    scene.add(inst, sun);
    disposeObject(scene);
  }
  assert.deepEqual(
    { instances, shadowMaps, images },
    { instances: 30, shadowMaps: 30, images: 30 },
  );
});
