import type { CameraSnapshot } from './share';
export type LayerKey =
  | 'buildings'
  | 'vegetation'
  | 'roads'
  | 'boundary'
  | 'water'
  | 'sports'
  | 'context'
  | 'labels';
export type SelectionOrigin = 'manual' | 'tour' | 'restore';
export type Quality = 'auto' | 'fine' | 'smooth';
export type Preset = 'morning' | 'day' | 'evening' | 'night';
export type LandmarkView =
  | 'oblique'
  | 'front'
  | 'back'
  | 'top'
  | 'entrance'
  | 'rear-entrance';
export interface ViewportFrame {
  left: number;
  top: number;
  width: number;
  height: number;
}
export type Category =
  | 'academic'
  | 'living'
  | 'culture'
  | 'service'
  | 'infrastructure'
  | 'landmark';
export interface Building {
  architecture?: { origin: [number, number]; angle: number };
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
  modelingBasis: 'photo' | 'type' | 'inferred';
  placeKind?: 'sports' | 'gate' | 'bridge' | 'sculpture';
  pickPolygon?: number[][];
  portalCenter?: [number, number];
  approachPath?: number[][];
  additionalReferences?: string[];
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
  cameraOffset?: [number, number, number];
  frontBearing?: number;
  zone: string;
  osmEditedAt?: string;
}
export interface Overview {
  infrastructureSnapshotAt?: string;
  publicRoadMeters?: number;
  bridges?: number;
  snapshotAt: string;
  buildings: number;
  campusBuildings: number;
  landmarks: number;
  trees: number;
  estimatedHeights: number;
  layers: Record<string, number>;
}
export interface Metrics {
  benchmark?: {
    orbiting: boolean;
    camera: {
      position: [number, number, number];
      target: [number, number, number];
      span: number;
    };
    viewport: number[];
    frame: ViewportFrame;
  };
  readyMs: number;
  heapMiB: number | null;
  fps: number;
  triangles: number;
  drawCalls: number;
  geometries: number;
  textures: number;
  pixelRatio: number;
  quality: string;
  automaticQualityLevel: number;
  shadows: boolean;
  nearTrees: boolean;
  detailBudgetMiB: number;
  loadedBytes: number;
  loadedDetails: string[];
  queuedDetails: number;
  residentDetailBytes: number;
  detailGeometryMiB: number;
}
export interface SceneController {
  setHovered: (id: string | null) => void;
  clearSelection: () => void;
  focus: (id: string, origin?: SelectionOrigin) => void;
  landmarkView: (view: LandmarkView) => void;
  setOrbit: (on: boolean) => void;
  setViewport: (frame: ViewportFrame, reframe?: boolean) => void;
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
  getSnapshot: () => CameraSnapshot;
  restoreSnapshot: (snapshot: Partial<CameraSnapshot>) => void;
}
export const DEFAULT_LAYERS: Record<LayerKey, boolean> = {
  buildings: true,
  vegetation: true,
  roads: true,
  boundary: true,
  water: true,
  sports: true,
  context: true,
  labels: true,
};
export const CATEGORY_NAMES: Record<Category, string> = {
  academic: '教学',
  living: '生活',
  culture: '文体',
  service: '校园服务',
  infrastructure: '路桥',
  landmark: '校门',
};
