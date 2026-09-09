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
