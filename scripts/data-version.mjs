import { createHash } from 'node:crypto';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

export async function dataVersion(directory, transformSource) {
  const hash = createHash('sha256').update(transformSource);
  for (const file of (await readdir(directory))
    .filter((f) => f.endsWith('.json'))
    .sort()) {
    hash
      .update(file)
      .update('\0')
      .update(await readFile(path.join(directory, file)))
      .update('\0');
  }
  return hash.digest('hex');
}
