import test from 'node:test';
import assert from 'node:assert/strict';
import {
  BufferGeometry,
  Float32BufferAttribute,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
} from 'three';
import { windowLights, createNightStyle } from '../lib/campus/night.ts';

test('独立窗片固定抽样、同片两三角一致，亮窗比例30–60%', () => {
  const positions = [];
  for (let i = 0; i < 1000; i++) {
    const x = (i % 50) * 3,
      y = Math.floor(i / 50) * 3.6;
    positions.push(
      x,
      y,
      0,
      x + 1,
      y,
      0,
      x + 1,
      y + 1,
      0,
      x,
      y,
      0,
      x + 1,
      y + 1,
      0,
      x,
      y + 1,
      0,
    );
  }
  const geometry = new BufferGeometry().setAttribute(
    'position',
    new Float32BufferAttribute(positions, 3),
  );
  const a = windowLights(geometry, new Matrix4());
  assert.deepEqual(windowLights(geometry, new Matrix4()), a);
  let lit = 0;
  for (let i = 0; i < 1000; i++) {
    const pane = Array.from(a.slice(i * 6, i * 6 + 6));
    assert.equal(new Set(pane).size, 1);
    if (pane[0] > 0) lit++;
  }
  assert.ok(lit > 300 && lit < 600, `${lit}/1000`);
  geometry.dispose();
});

test('日夜往返不累积压暗，玻璃只在夜间启用亮窗属性', () => {
  const style = createNightStyle();
  const mat = new MeshStandardMaterial({ name: 'grass', color: '#829963' });
  const mesh = new Mesh(new BufferGeometry(), mat),
    original = mat.color.clone();
  for (let i = 0; i < 3; i++) {
    style.apply(mesh, true);
    style.apply(mesh, false);
    assert.ok(mat.color.equals(original));
  }
  const glass = new MeshStandardMaterial({ name: 'glass' });
  const geo = new BufferGeometry().setAttribute(
    'position',
    new Float32BufferAttribute([0, 0, 0, 1, 0, 0, 1, 1, 0], 3),
  );
  const pane = new Mesh(geo, glass);
  style.apply(pane, false);
  assert.equal(geo.hasAttribute('windowLight'), false);
  style.apply(pane, true);
  assert.equal(glass.defines.CAMPUS_NIGHT_WINDOWS, 1);
  assert.equal(geo.hasAttribute('windowLight'), true);
  style.apply(pane, false);
  assert.equal(glass.emissiveIntensity, 0);
  assert.equal(glass.defines.CAMPUS_NIGHT_WINDOWS, 0);
});
