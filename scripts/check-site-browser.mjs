/* Forecourt visual checks through production UI: both LODs, night and layers. */
import { runLayerCheck } from './browser-check-helpers.mjs';

await runLayerCheck(
  {
    cameraFile: 'docs/model-checks/refinement/cameras.json',
    cameraId: 'library-side',
    selected: 'library',
  },
  async ({ visit, layers, layer, capture }) => {
    await visit('base', false);
    await layers();
    await layer('地点名称', false);
    const low = await capture('base-labels-off');
    if (low.loadedDetails.includes('landmark-library'))
      throw new Error('Base check unexpectedly loaded library detail');
    await visit('near', true);
    await layers();
    await layer('地点名称', false);
    const near = await capture('near-labels-off');
    if (!near.loadedDetails.includes('landmark-library'))
      throw new Error('Near library missing');
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
