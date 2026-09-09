export const ORIGIN = [108.2882, 22.84715] as const;
const METERS_X = 111320 * Math.cos((ORIGIN[1] * Math.PI) / 180);
export function project(lon: number, lat: number): [number, number] {
  return [(lon - ORIGIN[0]) * METERS_X, (lat - ORIGIN[1]) * 111320];
}
export function unproject(x: number, y: number): [number, number] {
  return [x / METERS_X + ORIGIN[0], y / 111320 + ORIGIN[1]];
}
export function isTap(
  start: { x: number; y: number; time: number },
  end: { x: number; y: number; time: number },
  maxTravel: number,
) {
  return (
    Math.hypot(end.x - start.x, end.y - start.y) < 8 &&
    end.time - start.time < 600 &&
    maxTravel < 8
  );
}
export function nextTourIndex(index: number, count: number) {
  return count > 0 ? (index + 1) % count : 0;
}
