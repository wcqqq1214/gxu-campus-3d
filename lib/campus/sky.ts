import {
  CanvasTexture,
  EquirectangularReflectionMapping,
  Fog,
  SRGBColorSpace,
} from 'three';
import type { Preset } from './types';

const SKIES = {
  morning: {
    zenith: '#adc9e3',
    horizon: '#e5e7e3',
    lower: '#99a5a0',
    far: 7000,
  },
  day: { zenith: '#a8cbe4', horizon: '#ece9dc', lower: '#a8ad97', far: 7800 },
  evening: {
    zenith: '#b7c5d8',
    horizon: '#edc7a8',
    lower: '#9d8e7c',
    far: 6500,
  },
  night: { zenith: '#101d32', horizon: '#344558', lower: '#1b2833', far: 5800 },
};

/** Keep the local haze band legible when fitting the campus into a narrow viewport. */
export function fogRange(preset: Preset, viewDistance: number) {
  // Desktop overview is about 3.7 km away; narrow screens need 9–11 km.
  // Compensate only the extra viewing distance, retaining the haze band's width.
  const offset = Math.max(0, viewDistance - 4000);
  return {
    near: (preset === 'night' ? 2500 : 2700) + offset,
    far: SKIES[preset].far + offset,
  };
}

/** A small, local equirectangular sky; reused for background and reflections. */
export function createSky() {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const context = canvas.getContext('2d')!;
  const texture = new CanvasTexture(canvas);
  texture.mapping = EquirectangularReflectionMapping;
  texture.colorSpace = SRGBColorSpace;
  function setPreset(preset: Preset) {
    const sky = SKIES[preset];
    const gradient = context.createLinearGradient(0, 0, 0, 128);
    gradient.addColorStop(0, sky.zenith);
    // Keep a blue upper sky visible in the low-angle views used by the map;
    // concentrate the warm haze within roughly 20 degrees of the horizon.
    gradient.addColorStop(0.38, sky.zenith);
    gradient.addColorStop(0.49, sky.horizon);
    gradient.addColorStop(0.51, sky.horizon);
    gradient.addColorStop(1, sky.lower);
    context.fillStyle = gradient;
    context.fillRect(0, 0, 256, 128);
    // Three caches equirectangular cubemaps/PMREM by texture identity.
    // Dispose that cache before uploading a changed canvas (no network request).
    texture.dispose();
    texture.needsUpdate = true;
    const range = fogRange(preset, 0);
    return new Fog(sky.horizon, range.near, range.far);
  }
  const fog = setPreset('day');
  return { texture, fog, setPreset, dispose: () => texture.dispose() };
}
