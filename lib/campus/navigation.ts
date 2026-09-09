import type { Building, Landmark } from './types';

/** All navigation surfaces share the curated catalogue, never the footprint index. */
export function searchLandmarks(
  landmarks: Landmark[],
  query: string,
): Landmark[] {
  const term = query.trim().toLocaleLowerCase();
  return landmarks.filter((place) =>
    place.name.toLocaleLowerCase().includes(term),
  );
}

export function navigableBuildings(
  buildings: Building[],
  landmarks: Landmark[],
): Building[] {
  const ids = new Set(landmarks.map((place) => place.id));
  return buildings.filter(
    (building) => building.landmark !== null && ids.has(building.landmark),
  );
}

/** Independent gate POIs have estimated pick bounds, never OSM building IDs. */
export function navigationFootprints(
  buildings: Building[],
  landmarks: Landmark[],
) {
  return [
    ...navigableBuildings(buildings, landmarks),
    ...landmarks
      .filter((l) => l.placeKind === 'gate')
      .map((l) => {
        const [x0, y0, x1, y1] = l.bounds;
        return {
          id: l.id,
          landmark: l.id,
          insideCampus: true,
          height: l.height,
          elevation: l.elevation,
          polygons: [
            [
              [
                [x0, y0],
                [x1, y0],
                [x1, y1],
                [x0, y1],
                [x0, y0],
              ],
            ],
          ],
        };
      }),
  ];
}
