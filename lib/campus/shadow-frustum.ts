import type { DirectionalLight, Vector3 } from 'three';
import { LIGHTING } from './lighting.ts';
import type { Preset } from './types';

/** Cache only an unchanged light volume; camera rotation is not an invalidation. */
export class ShadowFrustum {
  private previous: number[] | null = null;
  private preset = '';

  changed(x: number, y: number, z: number, size: number, preset: string) {
    const next = [x, y, z, size];
    if (
      this.previous &&
      this.preset === preset &&
      next.every((v, i) => Math.abs(v - this.previous![i]) < 1e-6)
    )
      return false;
    this.previous = next;
    this.preset = preset;
    return true;
  }

  /**
   * Fits the sun's shadow camera around the orbit target, sized by viewing
   * distance. Returns whether the shadow map needs a redraw.
   */
  fit(
    sun: DirectionalLight,
    target: Vector3,
    distance: number,
    preset: Preset,
  ) {
    const size = Math.min(1700, Math.max(100, distance * 0.8));
    const t = target;
    if (!this.changed(t.x, t.y, t.z, size, preset)) return false;
    sun.shadow.normalBias = preset === 'evening' ? 1.2 : size < 350 ? 0.3 : 0.8;
    sun.shadow.bias = preset === 'evening' ? -0.00025 : -0.00012;
    sun.target.position.copy(t);
    const dir = LIGHTING[preset].direction;
    sun.position.set(t.x + dir[0], t.y + dir[1], t.z + dir[2]);
    Object.assign(sun.shadow.camera, {
      left: -size,
      right: size,
      top: size,
      bottom: -size,
      near: 1,
      far: 5000,
    });
    sun.shadow.camera.updateProjectionMatrix();
    return true;
  }
}
