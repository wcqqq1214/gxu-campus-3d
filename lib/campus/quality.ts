import type { Quality } from './types';
export type QualityLevel = 0 | 1 | 2;

/** Only active, visible samples count; recovery is deliberately slower than degradation. */
export class AdaptiveQuality {
  level: QualityLevel = 0;
  private low = 0;
  private good = 0;
  private cooldown = 0;
  reset() {
    this.level = 0;
    this.low = 0;
    this.good = 0;
    this.cooldown = 0;
  }
  sample(fps: number, frames: number): boolean {
    this.cooldown = Math.max(0, this.cooldown - 1);
    if (frames < 6 || !Number.isFinite(fps) || fps <= 0) {
      this.low = 0;
      this.good = 0;
      return false;
    }
    this.low = fps < 23 ? this.low + 1 : 0;
    // The smooth tier intentionally caps rendering at about 30 fps.
    this.good = fps >= (this.level === 2 ? 28 : 48) ? this.good + 1 : 0;
    if (this.low >= 2 && this.level < 2) {
      this.level = (this.level + 1) as QualityLevel;
    } else if (this.good >= 10 && !this.cooldown && this.level > 0) {
      this.level = (this.level - 1) as QualityLevel;
    } else return false;
    this.low = 0;
    this.good = 0;
    this.cooldown = 20;
    return true;
  }
}

export function qualityProfile(
  quality: Quality,
  compact: boolean,
  saveData: boolean,
  adaptive: QualityLevel,
) {
  const level: QualityLevel =
    quality === 'fine'
      ? 0
      : quality === 'smooth' || (quality === 'auto' && (compact || saveData))
        ? 2
        : adaptive;
  return {
    level,
    pixelRatio: [1.75, 1.4, 1.25][level],
    shadows: level === 0,
    nearTrees: level === 0,
    treeDensity: [1, 0.75, 0.55][level],
    detailBudgetMiB: Math.min(compact ? 32 : 64, [64, 48, 24][level]),
  };
}
