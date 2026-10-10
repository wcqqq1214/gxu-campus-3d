/* Paving visual checks through production UI: retained layers and night. */
import { runLayerCheck } from './browser-check-helpers.mjs';

await runLayerCheck(
  {
    cameraFile: 'docs/model-checks/refinement/s4-paving-cameras.json',
    cameraId: '6b-paving-road-join',
  },
  async ({ visit, layers, layer, capture }) => {
    await visit('near', true);
    await layers();
    await layer('地点名称', false);
    const near = await capture('near-labels-off');
    await layer('道路与桥梁', false);
    const hidden = await capture('roads-off');
    if (hidden.triangles >= near.triangles)
      throw new Error('Road layer did not remove geometry');
    await layer('道路与桥梁', true);
    await layer('校园建筑', false);
    await capture('paving-with-buildings-off');
    await layer('校园建筑', true);
    const restored = await capture('layers-restored');
    await layer('树木', false);
    const noTrees = await capture('vegetation-off');
    if (noTrees.triangles >= restored.triangles)
      throw new Error('Vegetation layer did not remove geometry');
    await layer('树木', true);
    const treesRestored = await capture('vegetation-restored');
    if (treesRestored.triangles <= noTrees.triangles)
      throw new Error('Vegetation instances were not restored');
    await visit('night', true, 'night');
    await layers();
    await layer('地点名称', false);
    await capture('night-labels-off');
  },
);
