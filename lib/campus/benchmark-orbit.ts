import { Vector3 } from 'three';

const AXIS = new Vector3(0, 1, 0);
const SAMPLE_MS = 1500;

/** Measurement-only orbit: slow frames must not change the sampled route. */
export class BenchmarkOrbit {
  elapsedMs = 0;
  sampleIndex = 0;
  private readonly startedAt: number;
  private readonly offset: Vector3;

  constructor(startedAt: number, offset: Vector3) {
    this.startedAt = startedAt;
    this.offset = offset.clone();
  }

  position(time: number) {
    this.elapsedMs = Math.max(0, time - this.startedAt);
    return this.offset
      .clone()
      .applyAxisAngle(AXIS, (this.elapsedMs / 1000) * 0.13);
  }

  sampleDue() {
    const index = Math.floor(this.elapsedMs / SAMPLE_MS);
    if (index <= this.sampleIndex) return false;
    // Publish once after a stall; skipped indices remain visible to the check.
    this.sampleIndex = index;
    return true;
  }
}
