// Read the encoded lattice; decoded bounds shrink after each display trim.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import { createPrimitiveDecoder } from './draco-geometry.mjs';

export async function roadPositionDomain(file) {
  const raw = fs.readFileSync(file), size = raw.readUInt32LE(12);
  const doc = JSON.parse(raw.subarray(20, 20 + size));
  const decode = await createPrimitiveDecoder(doc, raw.subarray(28 + size));
  const nodes = doc.nodes.filter((n) => n.name.replace(/\.\d{3,}$/, '') === 'roads');
  assert.equal(nodes.length, 1);
  const domains = doc.meshes[nodes[0].mesh].primitives.map((p) =>
    decode(p, { positionDomainOnly: true }),
  );
  assert.equal(domains[0].bits, 18);
  for (const domain of domains) assert.deepEqual(domain, domains[0]);
  return domains[0];
}

if (process.argv[1]?.endsWith('/road-position-domain.mjs')) {
  assert(process.argv[2], 'Usage: node scripts/road-position-domain.mjs BASE_GLB');
  console.log(JSON.stringify(await roadPositionDomain(process.argv[2])));
}
