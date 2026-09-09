export type LayerKey =
  | 'buildings'
  | 'vegetation'
  | 'roads'
  | 'water'
  | 'sports'
  | 'context'
  | 'labels';
export type Quality = 'auto' | 'fine' | 'smooth';
export type Preset = 'morning' | 'day' | 'evening' | 'night';
export type Category =
  | 'academic'
  | 'living'
  | 'culture'
  | 'service'
  | 'landmark';
export interface Building {
  constructionStatus?: string | null;
  id: string;
  name: string;
  category: Category;
  center: [number, number];
  height: number;
  elevation: number;
  levels: number;
  insideCampus: boolean;
  landmark: string | null;
  polygons: number[][][][];
  bounds: number[];
  heightBasis: string;
  facadeBasis: string;
  osmEditedAt: string;
  sourceUrl: string;
  zone: string;
}
export interface Landmark {
  id: string;
  osmId?: string;
  name: string;
  category: Category;
  center: [number, number];
  height: number;
  elevation: number;
  bounds: number[];
  description: string;
  detail: string;
  sourceUrl: string;
  reference: string;
  distance: number;
  zone: string;
  osmEditedAt?: string;
}
export interface Overview {
  snapshotAt: string;
  buildings: number;
  campusBuildings: number;
  landmarks: number;
  trees: number;
  estimatedHeights: number;
  layers: Record<string, number>;
}
export interface Metrics {
  readyMs: number;
  heapMiB: number | null;
  fps: number;
  triangles: number;
  drawCalls: number;
  geometries: number;
  textures: number;
  pixelRatio: number;
  quality: string;
  loadedBytes: number;
}
export interface SceneController {
  clearSelection: () => void;
  focus: (id: string) => void;
  setLayer: (key: LayerKey, on: boolean) => void;
  setPreset: (p: Preset) => void;
  setQuality: (q: Quality) => void;
  view: (
    v: 'overview' | 'top' | 'tilt' | 'north' | 'zoomIn' | 'zoomOut',
  ) => void;
  exportImage: () => Promise<void>;
  retry: () => void;
  dispose: () => void;
  getMetrics: () => Metrics;
}
export const DEFAULT_LAYERS: Record<LayerKey, boolean> = {
  buildings: true,
  vegetation: true,
  roads: true,
  water: true,
  sports: true,
  context: true,
  labels: true,
};
export const CATEGORY_NAMES: Record<Category, string> = {
  academic: '教学科研',
  living: '校园生活',
  culture: '文化体育',
  service: '校园服务',
  landmark: '校园地标',
};
