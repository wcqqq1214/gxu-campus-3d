/** Stable schematic orientation; matches scripts/vegetation_layout.py.
 * Stored positions have decimetre precision. Order, type and sector do not
 * change the orientation of a surviving tree.
 */
export function treeRotation(x: number, y: number): number {
  const key = `${Math.round(x * 10)},${Math.round(y * 10)}`;
  let value = 2166136261;
  for (let i = 0; i < key.length; i++) {
    value = Math.imul(value ^ key.charCodeAt(i), 16777619) >>> 0;
  }
  return (value / 4294967296) * Math.PI * 2;
}

export interface TreeTerrain {
  bounds: number[];
  cols: number;
  rows: number;
  heights: number[];
}

/** Legacy four-column fallback; current rows carry final terrain triangle heights. */
export function treeGroundHeight(terrain: TreeTerrain, x: number, y: number): number {
  const { bounds: [x0, y0, x1, y1], cols, rows, heights } = terrain;
  const u = Math.max(0, Math.min(cols - 1.001, ((x - x0) / (x1 - x0)) * (cols - 1)));
  const v = Math.max(0, Math.min(rows - 1.001, ((y - y0) / (y1 - y0)) * (rows - 1)));
  const i = Math.floor(u), j = Math.floor(v), a = u - i, b = v - j;
  return (heights[j * cols + i] * (1 - a) + heights[j * cols + i + 1] * a) * (1 - b)
    + (heights[(j + 1) * cols + i] * (1 - a) + heights[(j + 1) * cols + i + 1] * a) * b;
}

export function treeElevation(row: number[], terrain: TreeTerrain): number {
  return Number.isFinite(row[4]) ? row[4] : treeGroundHeight(terrain, row[0], row[1]);
}
