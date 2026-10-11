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
    gradient.addColorStop(0.48, sky.horizon);
    gradient.addColorStop(0.52, sky.horizon);
    gradient.addColorStop(1, sky.lower);
    context.fillStyle = gradient;
    context.fillRect(0, 0, 256, 128);
    texture.needsUpdate = true;
    return new Fog(sky.horizon, preset === 'night' ? 2500 : 2700, sky.far);
  }
  const fog = setPreset('day');
  return { texture, fog, setPreset, dispose: () => texture.dispose() };
}
