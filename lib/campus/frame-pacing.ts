const INTERVAL = 1000 / 30;
// Allow sub-millisecond requestAnimationFrame timestamp jitter near a deadline.
const TOLERANCE = 1;

/** Limit scene updates without discarding the remainder of each refresh tick. */
export class FramePacer {
  private next: number | null = null;

  shouldUpdate(time: number, limited: boolean): boolean {
    if (!limited) {
      this.next = null;
      return true;
    }
    if (this.next === null || time - this.next > INTERVAL) {
      // Start fresh after an idle/hidden-tab gap; never replay missed frames.
      this.next = time + INTERVAL;
      return true;
    }
    if (time + TOLERANCE < this.next) return false;
    this.next += INTERVAL;
    return true;
  }
}

const SAMPLE_MS = 1500;

/**
 * Average frame rate over active rendering. Frames after an idle gap of a
 * second or more count only while the camera is moving, so a static map does
 * not report a low rate.
 */
export class FrameStats {
  fps = 0;
  private sampleStart: number;
  private lastRendered = 0;
  private activeMs = 0;
  private activeFrames = 0;

  constructor(now: number) {
    this.sampleStart = now;
  }

  rendered(time: number, moving: boolean) {
    if (this.lastRendered && (time - this.lastRendered < 1000 || moving)) {
      this.activeMs += time - this.lastRendered;
      this.activeFrames++;
    }
    this.lastRendered = time;
  }

  due(time: number) {
    return time - this.sampleStart > SAMPLE_MS;
  }

  /** Closes the current sample and returns the number of active frames in it. */
  sample(time: number) {
    const frames = this.activeFrames;
    if (frames > 0 && this.activeMs > 0)
      this.fps = (1000 * frames) / this.activeMs;
    this.activeMs = 0;
    this.activeFrames = 0;
    this.sampleStart = time;
    return frames;
  }

  /** Starts a fresh sample, discarding frames before `time`. */
  restart(time: number) {
    this.sampleStart = time;
    this.lastRendered = 0;
    this.activeMs = 0;
    this.activeFrames = 0;
  }
}
