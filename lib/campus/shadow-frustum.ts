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
}
