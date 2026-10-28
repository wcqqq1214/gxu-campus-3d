import { asset } from './boot';
import type { CampusBoundary } from './boundary';
import { createSharedJson } from './shared-json';

export const loadCampusBoundary = createSharedJson<CampusBoundary>(
  asset('data/campus-boundary.json'),
);
