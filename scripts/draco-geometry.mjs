import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import * as THREE from 'three';

// Decode Draco primitives from one GLB using the bundled decoder.
export async function createPrimitiveDecoder(doc, bin) {
  const temporary = fs.mkdtempSync(
    path.join(os.tmpdir(), 'gxu-track-decoder-'),
  );
  let draco;
  try {
    const wrapper = path.join(temporary, 'decoder.cjs');
    fs.copyFileSync('public/draco/draco_wasm_wrapper.js', wrapper);
    const factory = createRequire(import.meta.url)(wrapper);
    draco = await factory({
      wasmBinary: fs.readFileSync('public/draco/draco_decoder.wasm'),
    });
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }

  function decode(primitive) {
    const ext = primitive.extensions.KHR_draco_mesh_compression;
    const view = doc.bufferViews[ext.bufferView];
    const bytes = bin.subarray(
      view.byteOffset ?? 0,
      (view.byteOffset ?? 0) + view.byteLength,
    );
    const decoder = new draco.Decoder(),
      input = new draco.DecoderBuffer(),
      mesh = new draco.Mesh();
    input.Init(new Int8Array(bytes), bytes.length);
    const status = decoder.DecodeBufferToMesh(input, mesh);
    assert(status.ok(), status.error_msg());
    const geometry = new THREE.BufferGeometry();
    for (const [semantic, id] of Object.entries(ext.attributes)) {
      const attribute = decoder.GetAttributeByUniqueId(mesh, id);
      const values = new draco.DracoFloat32Array(),
        size = attribute.num_components();
      assert(decoder.GetAttributeFloatForAllPoints(mesh, attribute, values));
      const array = new Float32Array(mesh.num_points() * size);
      for (let i = 0; i < array.length; i++) array[i] = values.GetValue(i);
      const name = {
        POSITION: 'position',
        NORMAL: 'normal',
        TEXCOORD_0: 'uv',
        COLOR_0: 'color',
      }[semantic];
      assert(name, `Unrecognized attribute ${semantic}`);
      geometry.setAttribute(name, new THREE.BufferAttribute(array, size));
      draco.destroy(values);
    }
    const indices = [],
      face = new draco.DracoInt32Array();
    for (let i = 0; i < mesh.num_faces(); i++) {
      assert(decoder.GetFaceFromMesh(mesh, i, face));
      for (let j = 0; j < 3; j++) indices.push(face.GetValue(j));
    }
    geometry.setIndex(indices);
    for (const object of [status, face, mesh, input, decoder])
      draco.destroy(object);
    return geometry;
  }

  return decode;
}
