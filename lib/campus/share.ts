import type { LandmarkView, Preset } from './types';
export interface CameraSnapshot {
  selected: string | null;
  view: LandmarkView | null;
  preset: Preset;
  position: [number, number, number];
  target: [number, number, number];
  /** Half-span in meters at the target, used to adapt a shared view to another screen. */
  span: number;
}
const views = ['oblique', 'front', 'back', 'top', 'entrance', 'rear-entrance'];
const presets = ['morning', 'day', 'evening', 'night'];
export function encodeShare(snapshot: CameraSnapshot) {
  const params = new URLSearchParams();
  if (snapshot.selected) params.set('place', snapshot.selected);
  if (snapshot.view) params.set('view', snapshot.view);
  params.set('light', snapshot.preset);
  params.set(
    'camera',
    [...snapshot.position, ...snapshot.target]
      .map((v) => v.toFixed(2))
      .join(','),
  );
  params.set('span', snapshot.span.toFixed(2));
  return '#' + params.toString();
}
export function decodeShare(
  hash: string,
  ids: string[],
): Partial<CameraSnapshot> | null {
  const params = new URLSearchParams(hash.replace(/^#/, ''));
  const selected = params.get('place');
  const light = params.get('light'),
    view = params.get('view');
  const result: Partial<CameraSnapshot> = {};
  if (selected && ids.includes(selected)) result.selected = selected;
  if (presets.includes(light ?? '')) result.preset = light as Preset;
  if (views.includes(view ?? '')) result.view = view as LandmarkView;
  const numbers = params.get('camera')?.split(',').map(Number);
  const span = Number(params.get('span'));
  if (
    numbers?.length === 6 &&
    numbers.every(Number.isFinite) &&
    numbers.slice(0, 3).every((v) => Math.abs(v) < 25000) &&
    numbers.slice(3).every((v) => Math.abs(v) < 6000) &&
    numbers[1] > numbers[4] &&
    Math.hypot(...numbers.slice(0, 3).map((v, i) => v - numbers[i + 3])) >=
      18 &&
    span >= 1 &&
    span <= 10000
  ) {
    result.position = numbers.slice(0, 3) as CameraSnapshot['position'];
    result.target = numbers.slice(3) as CameraSnapshot['target'];
    result.span = span;
  }
  return result.selected || result.position || result.preset ? result : null;
}
export function cameraBearing(snapshot: CameraSnapshot | null) {
  if (!snapshot) return 0;
  return (
    (Math.atan2(
      snapshot.position[0] - snapshot.target[0],
      snapshot.position[2] - snapshot.target[2],
    ) *
      180) /
    Math.PI
  );
}
