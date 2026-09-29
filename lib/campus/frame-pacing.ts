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
