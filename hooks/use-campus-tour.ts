import { useEffect, useRef, useState } from 'react';
import { nextTourIndex } from '@/lib/campus/math';
import type { Landmark } from '@/lib/campus/types';

const TOUR_STOP_MS = 8500;

export type CampusTour = ReturnType<typeof useCampusTour>;

/**
 * Tour state over the landmark catalogue. `visit` must be stable; it moves the
 * camera to a stop without counting as a manual selection.
 */
export function useCampusTour(
  landmarks: Landmark[],
  visit: (id: string) => void,
) {
  const [playing, setPlaying] = useState(false);
  const [started, setStarted] = useState(false);
  const [index, setIndex] = useState(0);
  const progress = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!playing || !landmarks.length) return;
    visit(landmarks[index].id);
    // Both the station change and its indicator use this deadline. Updating the
    // DOM directly keeps progress running while the panel is display:none,
    // without re-rendering the entire map on every animation frame.
    const deadline = performance.now() + TOUR_STOP_MS;
    let frame = 0;
    const updateProgress = () => {
      const fraction = Math.min(
        1,
        Math.max(0, 1 - (deadline - performance.now()) / TOUR_STOP_MS),
      );
      if (progress.current)
        progress.current.style.transform = `scaleX(${fraction})`;
      if (fraction < 1) frame = requestAnimationFrame(updateProgress);
    };
    updateProgress();
    const timer = setTimeout(
      () => setIndex((i) => nextTourIndex(i, landmarks.length)),
      Math.max(0, deadline - performance.now()),
    );
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(frame);
    };
  }, [playing, index, landmarks, visit]);
  function jump(delta: number) {
    setStarted(true);
    setIndex((i) => (i + delta + landmarks.length) % landmarks.length);
    if (!playing && landmarks.length)
      visit(
        landmarks[(index + delta + landmarks.length) % landmarks.length].id,
      );
  }
  return {
    playing,
    setPlaying,
    started,
    setStarted,
    index,
    setIndex,
    progress,
    jump,
  };
}
