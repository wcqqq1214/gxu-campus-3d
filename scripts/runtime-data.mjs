/**
 * The page needs only part of each building record. The full
 * public/data/buildings.json remains the modelling and validation source; the
 * static build publishes this reduced copy under the same URL.
 *
 * Keep this list equal to the fields of `Building` in lib/campus/types.ts.
 */
export const RUNTIME_BUILDING_FIELDS = [
  'id',
  'name',
  'category',
  'center',
  'height',
  'elevation',
  'levels',
  'insideCampus',
  'landmark',
  'polygons',
  'bounds',
  'architecture',
];

// Footprints only drive picking, outlines and the minimap. The shortest
// published edge is about 0.37 m, so centimetre rounding cannot merge vertices.
const roundCentimetres = (value) =>
  Array.isArray(value)
    ? value.map(roundCentimetres)
    : Math.round(value * 100) / 100;

export function runtimeBuildings(buildings) {
  return buildings.map((building) => {
    const record = {};
    for (const field of RUNTIME_BUILDING_FIELDS) {
      if (!(field in building)) continue;
      record[field] =
        field === 'polygons'
          ? roundCentimetres(building.polygons)
          : building[field];
    }
    return record;
  });
}
