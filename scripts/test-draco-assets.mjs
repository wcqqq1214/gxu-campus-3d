import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { campusDracoAssets } from './vite-draco-assets.mjs';
const id = 'node_modules/three/examples/jsm/loaders/DRACOLoader.js';
const source = fs.readFileSync(id, 'utf8');
test('all upstream Draco defaults use the single public decoder directory', () => {
  for (const prefix of ['', '/gxu-campus-3d']) {
    const plugin = campusDracoAssets(prefix);
    const { code } = plugin.transform(source, id);
    assert.ok(!code.includes('new URL('));
    assert.equal(code.match(/\/draco\/draco_/g).length, 5);
    assert.ok(
      code.includes(JSON.stringify(`${prefix}/draco/draco_decoder.wasm`)),
    );
    assert.equal(plugin.transform(source, 'another-loader.js'), undefined);
    assert.throws(() => plugin.transform('', id), /Unexpected/);
  }
});
