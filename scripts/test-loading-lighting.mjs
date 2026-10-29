import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { compileFunction } from 'node:vm';
import ts from 'typescript';
import * as THREE from 'three';
import { LIGHTING } from '../lib/campus/lighting.ts';
import { createNightStyle } from '../lib/campus/night.ts';
import { createPalette } from '../lib/campus/palette.ts';
import { batchSportsSurfaces } from '../lib/campus/sports-batching.ts';
import { batchStaticRoadSurfaces } from '../lib/campus/road-batching.ts';
import { pruneGroundTriangles } from '../lib/campus/ground-triangles.ts';
import { disposeObject } from '../lib/campus/resources.ts';

// Run the actual loading and preset functions without requiring a WebGL context.
// Only transport, scheduling and unrelated scene services are replaced.
const source = fs.readFileSync(
  new URL('../lib/campus/scene.ts', import.meta.url),
  'utf8',
);
const ast = ts.createSourceFile(
  'scene.ts',
  source,
  ts.ScriptTarget.Latest,
  true,
);
const sceneFunction = ast.statements.find(
  (node) => ts.isFunctionDeclaration(node) && node.name?.text === 'createScene',
);
const names = ['styleMeshes', 'applyModelLighting', 'loadGLB', 'setPreset'];
const functions = sceneFunction.body.statements.filter(
  (node) => ts.isFunctionDeclaration(node) && names.includes(node.name?.text),
);
for (const name of ['styleMeshes', 'loadGLB', 'setPreset'])
  assert.ok(functions.some((node) => node.name.text === name));
const compiled = ts.transpileModule(
  functions.map((node) => node.getText(ast)).join('\n'),
  {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ESNext,
    },
  },
).outputText;
const makeLoader = compileFunction(
  `
  const { THREE, LIGHTING, createNightStyle, createPalette, batchSportsSurfaces,
    batchStaticRoadSurfaces, pruneGroundTriangles, disposeObject } = services;
  const { root, initialPreset, onYield } = fixture;
  const scene = new THREE.Scene(), palette = createPalette([]), nightStyle = createNightStyle();
  const contextStyle = { apply() {} }, lifecycle = new AbortController();
  const progresses = new Map(), landmarks = [], loaded = new Map(), geometryCosts = new Map();
  const sky = { setPreset() {} }, sun = { color: new THREE.Color() };
  const ambient = { color: new THREE.Color(), groundColor: new THREE.Color() };
  const fill = { color: new THREE.Color() }, renderer = {}, effects = { setNight() {} };
  const labels = { dataset: {} }, syncRoadLights = () => {}, reconcileDetails = () => {};
  const updateLoadStatus = () => {}, asset = x => x, modelUrl = x => x.url;
  const fetchModel = async () => new ArrayBuffer(0), loader = { parseAsync: async () => ({ scene: root }) };
  let preset = initialPreset, disposed = false, loadedBytes = 0, dirty = false, yields = 0;
  const setTimeout = resume => globalThis.setTimeout(() => {
    onYield(++yields, { setPreset, abort: () => lifecycle.abort() });
    resume();
  }, 0);
  ${compiled}
  return async key => {
    const gltf = await loadGLB({ url: 'fixture.glb', bytes: 1 }, key);
    scene.add(gltf.scene);
    return { preset, yields };
  };
`,
  ['services', 'fixture'],
);
const services = {
  THREE,
  LIGHTING,
  createNightStyle,
  createPalette,
  batchSportsSurfaces,
  batchStaticRoadSurfaces,
  pruneGroundTriangles,
  disposeObject,
};
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
          const run = makeLoader(services, {
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
  const run = makeLoader(services, {
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
