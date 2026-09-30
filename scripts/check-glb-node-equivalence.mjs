// Compare actual Draco-decoded oriented faces of one node, including all attributes.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const args = process.argv.slice(2);
assert(
  [6, 8].includes(args.length),
  'Use --before FILE --after FILE --report FILE [--node NAME]',
);
const options = Object.fromEntries(
  Array.from({ length: args.length / 2 }, (_, i) => i * 2).map((i) => [
    args[i],
    args[i + 1],
  ]),
);
for (const key of ['--before', '--after', '--report']) assert(options[key]);
const nodeName = options['--node'] ?? 'terrain';
const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'gxu-node-decoder-'));
let draco;
try {
  const wrapper = path.join(temporary, 'decoder.cjs');
  fs.copyFileSync('public/draco/draco_wasm_wrapper.js', wrapper);
  draco = await createRequire(import.meta.url)(wrapper)({
    wasmBinary: fs.readFileSync('public/draco/draco_decoder.wasm'),
  });
} finally {
  fs.rmSync(temporary, { recursive: true, force: true });
}

function read(file) {
  const raw = fs.readFileSync(file),
    length = raw.readUInt32LE(12);
  const doc = JSON.parse(raw.subarray(20, 20 + length)),
    bin = raw.subarray(28 + length);
  const nodes = doc.nodes.filter(
    (n) => n.name.replace(/\.\d{3,}$/, '') === nodeName,
  );
  assert.equal(nodes.length, 1);
  const node = nodes[0];
  assert(!node.matrix && !node.scale && !node.rotation && !node.translation);
  const rows = [],
    validRows = [],
    materials = [];
  let vertices = 0;
  for (const p of doc.meshes[node.mesh].primitives) {
    assert(p.mode === undefined || p.mode === 4);
    const material = doc.materials[p.material].name;
    materials.push(material);
    const ext = p.extensions.KHR_draco_mesh_compression;
    const view = doc.bufferViews[ext.bufferView],
      start = view.byteOffset ?? 0;
    const data = bin.subarray(start, start + view.byteLength);
    const decoder = new draco.Decoder(),
      input = new draco.DecoderBuffer(),
      mesh = new draco.Mesh();
    input.Init(new Int8Array(data), data.length);
    const status = decoder.DecodeBufferToMesh(input, mesh);
    assert(status.ok(), status.error_msg());
    vertices += mesh.num_points();
    const attributes = {};
    for (const name of Object.keys(ext.attributes).sort()) {
      const attribute = decoder.GetAttributeByUniqueId(
        mesh,
        ext.attributes[name],
      );
      const values = new draco.DracoFloat32Array(),
        size = attribute.num_components();
      assert(decoder.GetAttributeFloatForAllPoints(mesh, attribute, values));
      const array = new Float32Array(mesh.num_points() * size);
      for (let i = 0; i < array.length; i++) array[i] = values.GetValue(i);
      attributes[name] = { array, size };
      draco.destroy(values);
    }
    const schema = JSON.stringify(
      Object.entries(attributes).map(([name, a]) => [name, a.size]),
    );
    const face = new draco.DracoInt32Array();
    for (let i = 0; i < mesh.num_faces(); i++) {
      assert(decoder.GetFaceFromMesh(mesh, i, face));
      const ids = [0, 1, 2].map((j) => face.GetValue(j));
      const corners = ids.map((id) => {
        const values = Object.values(attributes).flatMap((a) =>
          Array.from(a.array.subarray(id * a.size, (id + 1) * a.size)),
        );
        const bytes = Buffer.alloc(values.length * 4);
        values.forEach((v, k) => bytes.writeFloatLE(v === 0 ? 0 : v, k * 4));
        return bytes.toString('hex');
      });
      const row =
        material +
        schema +
        [0, 1, 2]
          .map((j) => corners.slice(j).concat(corners.slice(0, j)).join(''))
          .sort()[0];
      rows.push(row);
      const xyz = ids.map((id) =>
        Array.from(attributes.POSITION.array.subarray(id * 3, id * 3 + 3)),
      );
      const u = xyz[1].map((v, j) => v - xyz[0][j]),
        v = xyz[2].map((w, j) => w - xyz[0][j]);
      const cross = [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
      ];
      if (cross.some((n) => n !== 0)) validRows.push(row);
    }
    for (const object of [face, status, mesh, input, decoder])
      draco.destroy(object);
  }
  rows.sort();
  validRows.sort();
  return {
    file,
    fileSHA256: sha(raw),
    bytes: raw.length,
    vertices,
    materials,
    triangles: rows.length,
    zeroAreaTriangles: rows.length - validRows.length,
    allFacesSHA256: sha(rows.join('\n')),
    validFacesSHA256: sha(validRows.join('\n')),
  };
}

const before = read(options['--before']),
  after = read(options['--after']);
const passed =
  before.triangles === after.triangles &&
  before.allFacesSHA256 === after.allFacesSHA256;
const report = {
  node: nodeName,
  passed,
  before,
  after,
  scope:
    'Exact multiset of oriented Draco-decoded selected-node faces, including zero-area faces, material names and every Float32 vertex attribute; signed zero normalized. Texture payloads and material parameters are outside this check.',
};
fs.mkdirSync(path.dirname(options['--report']), { recursive: true });
fs.writeFileSync(options['--report'], JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
assert(passed, 'Decoded node face attributes changed');
