import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createNightStyle } from '../lib/campus/night.ts';
import { createPalette } from '../lib/campus/palette.ts';
import { disposeObject } from '../lib/campus/resources.ts';
import { createModelPipeline } from '../lib/campus/scene-models.ts';

// Run the real model pipeline without a WebGL context. Only transport, the
// decoder and task scheduling are replaced; each styling slice is observable.
function makeLoader({ root, initialPreset, onYield }) {
  const scene = new THREE.Scene();
  const lifecycle = new AbortController();
  let preset = initialPreset,
    yields = 0;
  const models = createModelPipeline({
    loader: { parseAsync: async () => ({ scene: root }) },
    palette: createPalette([]),
    contextStyle: { apply() {} },
    nightStyle: createNightStyle(),
    landmarks: [],
    preset: () => preset,
    lifetime: lifecycle.signal,
    onProgress() {},
    schedule: (resume) =>
      setTimeout(() => {
        onYield(++yields, {
          // Like the scene, a preset change restyles only attached models.
          setPreset(value) {
            preset = value;
            models.applyLighting(scene);
          },
          abort: () => lifecycle.abort(),
        });
        resume();
      }, 0),
  });
  const download = {
    base: Promise.resolve(new ArrayBuffer(0)),
    onProgress: () => () => {},
  };
  return async (key) => {
    const gltf = await models.load(
      { url: 'fixture.glb', bytes: 1 },
      key,
      undefined,
      download,
    );
    scene.add(gltf.scene);
    return { preset, yields };
  };
}
function model() {
  const root = new THREE.Group();
  const materials = {};
  for (const name of [
    'glass',
    'grass',
    'path',
    'lampGlass',
    'timeLight',
    'timeSilver',
  ]) {
    const material = new THREE.MeshStandardMaterial({ name });
    materials[name] = material;
    root.add(new THREE.Mesh(new THREE.BoxGeometry(), material));
  }
  return { root, materials };
}

for (const key of ['base', 'landmark-test'])
  for (const initialPreset of ['day', 'night'])
    for (const switchAt of [1, 2, 3])
      test(`${key}: ${initialPreset} switches during loading slice ${switchAt}`, async () => {
        const { root, materials } = model();
        const target = initialPreset === 'day' ? 'night' : 'day';
        const night = target === 'night';
        try {
          const run = makeLoader({
            root,
            initialPreset,
            onYield(index, controls) {
              if (index === switchAt) controls.setPreset(target);
            },
          });
          assert.equal((await run(key)).preset, target);
          assert.equal(materials.glass.emissiveIntensity, night ? 1.5 : 0);
          assert.equal(
            materials.glass.defines?.CAMPUS_NIGHT_WINDOWS ?? 0,
            Number(night),
          );
          if (night)
            assert.ok(root.children[0].geometry.hasAttribute('windowLight'));
          assert.equal(materials.lampGlass.emissiveIntensity, night ? 3.5 : 0);
          assert.equal(materials.timeLight.emissiveIntensity, night ? 1.8 : 0);
          assert.equal(
            materials.timeSilver.emissiveIntensity,
            night ? 0.16 : 0,
          );
          assert.equal(materials.grass.color.r, 1.02 * (night ? 0.6 : 1));
          assert.equal(materials.path.color.r, 1.13 * (night ? 0.6 : 1));
        } finally {
          disposeObject(root);
        }
      });

test('cancellation during the last slice still disposes the unpublished model', async () => {
  const { root } = model();
  let released = 0;
  root.children.forEach((mesh) =>
    mesh.geometry.addEventListener('dispose', () => released++),
  );
  const run = makeLoader({
    root,
    initialPreset: 'day',
    onYield(index, controls) {
      if (index === 3) {
        controls.setPreset('night');
        controls.abort();
      }
    },
  });
  await assert.rejects(run('landmark-test'), { name: 'AbortError' });
  assert.equal(root.parent, null);
  assert.equal(released, root.children.length);
});
