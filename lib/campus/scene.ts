import { placeName, translate, type Locale, type Message } from './i18n';
import { landmarkLabelAnchor } from './labels';
import { createNightStyle, createRoadLights } from './night';
import { createPalette } from './palette';
import { createSky, fogRange } from './sky';
import { LIGHTING } from './lighting';
import { navigationFootprints, searchableBuildings } from './navigation';
import {
  treeAppearance,
  treeRotation,
  treeElevation,
  prioritizeTreeRows,
} from './vegetation';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { batchSportsSurfaces } from './sports-batching';
import { batchStaticRoadSurfaces } from './road-batching';
import { pruneGroundTriangles } from './ground-triangles';
import { createConvexCulling } from './convex-culling';
import { isTap } from './math';
import type { CameraSnapshot } from './share';
import {
  fetchModel,
  fetchJson,
  nearbyChunks,
  planDetails,
  ResourceQueue,
} from './streaming';
import type { StreamAsset as Asset } from './streaming';
import {
  asset,
  modelUrl,
  type BasePrefetch,
  type ModelManifest as Manifest,
} from './boot';
import {
  bridgeEntrancePose,
  entranceBox,
  fitBox,
  fitPoints,
  campusOverviewPoints,
  landmarkBox,
  landmarkDirection,
  benchmarkOrbitEnabled,
} from './camera';
import { DEFAULT_LAYERS } from './types';
import { AdaptiveQuality, qualityProfile } from './quality';
import { FramePacer } from './frame-pacing';
import { BenchmarkOrbit } from './benchmark-orbit';
import { ShadowFrustum } from './shadow-frustum';
import { disposeObject } from './resources';
import { createBoundary } from './boundary';
import { createContextStyle } from './context-style';
import type { CampusBoundary } from './boundary';
import type {
  Building,
  Landmark,
  Quality,
  Preset,
  SceneController,
  Metrics,
  LayerKey,
  LandmarkView,
  ViewportFrame,
} from './types';
interface Callbacks {
  onStatus: (message: Message, error?: boolean, progress?: number) => void;
  onReady: () => void;
  onHover: (id: string | null) => void;
  onSelect: (
    id: string | null,
    origin?: import('./types').SelectionOrigin,
  ) => void;
  onInteract: () => void;
  /** Optional: building the report is skipped when nobody reads it. */
  onMetrics?: (m: Metrics) => void;
  onOrbit: (on: boolean) => void;
  onCamera: (snapshot: CameraSnapshot) => void;
}
export function createScene(
  host: HTMLElement,
  buildings: Building[],
  landmarks: Landmark[],
  callbacks: Callbacks,
  /** Consumed by the first initialization only; retries fetch again. */
  prefetch?: BasePrefetch,
): SceneController {
  let locale: Locale = 'zh';
  const t = (source: string, values?: Record<string, string | number>) =>
    translate(locale, source, values);
  const benchmarkOrbit = benchmarkOrbitEnabled(location.search);
  const scene = new THREE.Scene();
  let convexCulling: ReturnType<typeof createConvexCulling> | null = null;
  let convexPreparation: ReturnType<typeof setTimeout> | undefined;
  const contextStyle = createContextStyle();
  const palette = createPalette(buildings);
  const nightStyle = createNightStyle();
  let roadLights: ReturnType<typeof createRoadLights> | null = null;
  const sky = createSky();
  scene.background = sky.texture;
  scene.fog = sky.fog;
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: false,
  });
  renderer.info.autoReset = false;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.shadowMap.autoUpdate = false;
  renderer.shadowMap.needsUpdate = true;
  const shadowVolume = new ShadowFrustum();
  let shadowUpdates = 0;
  const canvas = renderer.domElement;
  canvas.setAttribute(
    'aria-label',
    '广西大学三维校园，方向键平移，加减键缩放，Home返回全景',
  );
  canvas.tabIndex = 0;
  host.appendChild(canvas);
  const camera = new THREE.PerspectiveCamera(41, 1, 1, 30000);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.09;
  controls.minDistance = 18;
  controls.maxDistance = 18000;
  controls.maxPolarAngle = Math.PI * 0.475;
  controls.minPolarAngle = 0.02;
  controls.mouseButtons = {
    LEFT: THREE.MOUSE.ROTATE,
    MIDDLE: THREE.MOUSE.DOLLY,
    RIGHT: THREE.MOUSE.PAN,
  };
  const wheelHost = host.parentElement ?? host;
  function onOverlayWheel(event: WheelEvent) {
    if (event.target === canvas || event.defaultPrevented) return;
    if (!(event.target instanceof Element)) return;
    // Scrollable menus keep their wheel gestures; other overlays zoom the map.
    for (let el: Element | null = event.target; el; el = el.parentElement) {
      const style = getComputedStyle(el);
      if (
        (/(auto|scroll)/.test(style.overflowY) &&
          el.scrollHeight > el.clientHeight) ||
        (/(auto|scroll)/.test(style.overflowX) &&
          el.scrollWidth > el.clientWidth) ||
        el.matches('[role="dialog"], dialog')
      )
        return;
      if (el === wheelHost) break;
    }
    // Retain wheel units, cursor position and pinch modifiers for OrbitControls.
    if (!canvas.dispatchEvent(new WheelEvent('wheel', event)))
      event.preventDefault();
  }
  wheelHost.addEventListener('wheel', onOverlayWheel, { passive: false });
  const ambient = new THREE.HemisphereLight('#d4e6fa', '#818363', 0.72);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight('#fff3de', 3.35);
  sun.position.set(-700, 1400, 600);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.bias = -0.00008;
  sun.shadow.normalBias = 0.18;
  scene.add(sun);
  scene.add(sun.target);
  const fill = new THREE.DirectionalLight('#c3dcec', 0.18);
  fill.position.set(1000, 600, -700);
  scene.add(fill);
  const layers = { ...DEFAULT_LAYERS };
  const boundaryRoot = new THREE.Group();
  let overviewPoints: THREE.Vector3[] | null = null;
  scene.add(boundaryRoot);
  let boundaryReady = false,
    boundaryLoading = false,
    boundaryFailed = false;
  const dynamic = new THREE.Group();
  scene.add(dynamic);
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(30000, 30000),
    new THREE.MeshStandardMaterial({ color: '#b8c9a9', roughness: 1 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -22;
  scene.add(ground);
  scene.environment = sky.texture;
  scene.environmentIntensity = 0.24;
  const loader = new GLTFLoader();
  let decoderFailed = false;
  function createDecoder() {
    const decoder = new DRACOLoader();
    decoder.setDecoderPath(asset('draco/'));
    // The base model carries hundreds of Draco primitives. Phone-sized layouts
    // keep two decoder heaps; larger screens use spare cores, at most four.
    decoder.setWorkerLimit(
      window.innerWidth < 760
        ? 2
        : Math.min(4, Math.max(2, (navigator.hardwareConcurrency || 2) - 1)),
    );
    // Fetch the decoder while the base model is still downloading. Model loads
    // still await this request; observing it here only avoids an unhandled
    // rejection when it fails before the first decode.
    (
      decoder.preload() as DRACOLoader & { decoderPending?: Promise<unknown> }
    ).decoderPending?.catch(() => {
      if (draco === decoder) decoderFailed = true;
    });
    return decoder;
  }
  let draco = createDecoder();
  loader.setDRACOLoader(draco);
  let manifest: Manifest | null = null;
  let pendingPrefetch = prefetch;
  let baseRoot: THREE.Group | null = null;
  let treesRoot: THREE.Group | null = null;
  let highTreesReady = false;
  let highTreesFailed = false;
  let treesFailed = false;
  let treeData: {
    data: number[][];
    terrain: {
      bounds: number[];
      cols: number;
      rows: number;
      heights: number[];
    };
  } | null = null;
  let disposed = false;
  let quality: Quality = 'auto';
  let preset: Preset = 'day';
  let selected: string | null = null;
  let hovered: string | null = null;
  let initialReady = false;
  let readyMs = 0;
  let loadedBytes = 0;
  let loop = 0;
  let modeSmooth = false;
  const adaptive = new AdaptiveQuality();
  let profile = qualityProfile('auto', false, false, adaptive.level);
  let effects: ReturnType<
    typeof import('./postprocessing').createPostprocessing
  > | null = null;
  let effectsLoading = false;
  let effectsFailed = false;
  function syncEffects() {
    if (!profile.postprocessing) {
      effects?.dispose();
      effects = null;
      return;
    }
    if (effects) {
      effects.resize();
      return;
    }
    if (effectsLoading || effectsFailed || !initialReady) return;
    effectsLoading = true;
    void import('./postprocessing')
      .then(({ createPostprocessing }) => {
        if (!disposed && profile.postprocessing) {
          effects = createPostprocessing(renderer, scene, camera);
          effects.setNight(preset === 'night');
          dirty = true;
        }
      })
      .catch(() => {
        effectsFailed = true;
      })
      .finally(() => {
        effectsLoading = false;
      });
  }
  function renderScene() {
    if (scene.fog instanceof THREE.Fog) {
      Object.assign(
        scene.fog,
        fogRange(preset, camera.position.distanceTo(controls.target)),
      );
    }
    renderer.setRenderTarget(null);
    renderer.info.reset();
    if (renderer.shadowMap.enabled && renderer.shadowMap.needsUpdate)
      shadowUpdates++;
    if (effects && profile.postprocessing) effects.render();
    else renderer.render(scene, camera);
  }
  const saveData = () =>
    Boolean(
      (navigator as Navigator & { connection?: { saveData?: boolean } })
        .connection?.saveData,
    );
  let lastFrame = 0;
  let benchmarkRun: BenchmarkOrbit | null = null;
  const framePacer = new FramePacer();
  let sampleStart = performance.now();
  let fps = 0;
  let lastRendered = 0;
  let activeFrameMs = 0;
  let activeFrames = 0;
  let dirty = true;
  let pendingRequest = 0;
  let frame: ViewportFrame = {
    left: 20,
    top: 100,
    width: Math.max(200, host.clientWidth - 100),
    height: Math.max(200, host.clientHeight - 160),
  };
  // UI occlusion can change without changing the current camera composition.
  let cameraFrame = frame;
  let framedWidth = host.clientWidth;
  let framedHeight = host.clientHeight;
  let selectedView: LandmarkView = 'oblique';
  let autoFramed = true;
  let orbiting = false;
  let restoredPose: Partial<CameraSnapshot> | null = null;
  let frameReady = false;
  let cameraChanged = true;
  let cameraSampleAt = 0;
  const compact = () => window.innerWidth < 760;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const loaded = new Map<string, THREE.Group>();
  const loading = new Set<string>();
  const failed = new Map<string, Asset>();
  const detailQueue = new ResourceQueue<void>(2);
  const lifecycle = new AbortController();
  const progresses = new Map<
    string,
    { label: string; name?: string; fraction: number }
  >();
  const geometryCosts = new Map<string, number>();
  const wanted = new Set<string>();
  const recentlyUsed = new Map<string, number>();
  let tween: {
    from: THREE.Vector3;
    to: THREE.Vector3;
    fromTarget: THREE.Vector3;
    toTarget: THREE.Vector3;
    start: number;
  } | null = null;
  const labels = document.createElement('div');
  labels.className = 'scene-labels';
  host.appendChild(labels);
  const labelNodes = landmarks.map((l, i) => {
    const el = document.createElement('button');
    el.className = 'map-label';
    el.dataset.placeId = l.id;
    el.onpointerenter = () => setHovered(l.id);
    el.onpointerleave = () => setHovered(null);
    el.onfocus = () => setHovered(l.id);
    el.onblur = () => setHovered(null);
    const number = document.createElement('span');
    number.textContent = String(i + 1).padStart(2, '0');
    el.appendChild(number);
    const caption = document.createElement('span');
    caption.className = 'map-label-name';
    caption.textContent = placeName(l.name, locale);
    el.appendChild(caption);
    el.title = t('查看{name}', { name: placeName(l.name, locale) });
    el.onclick = () => {
      callbacks.onInteract();
      focus(l.id);
    };
    labels.appendChild(el);
    return {
      l,
      el,
      caption,
      width: 0,
      height: 0,
      point: landmarkLabelAnchor(l),
      bounds: [0, 0, 0, 0],
    };
  });
  const labelOrder = [...labelNodes];
  let orderedHover: string | null | undefined;
  let orderedSelection: string | null | undefined;
  const labelProjection = new THREE.Vector3();
  const orbitOffset = new THREE.Vector3();
  const orbitAxis = new THREE.Vector3(0, 1, 0);
  const occupiedLabels: number[][] = [];
  const labelViewport = { width: 0, height: 0 };
  function measureLabels() {
    const layerDisplay = labels.style.display;
    labels.style.display = '';
    const displays = labelNodes.map(({ el }) => el.style.display);
    for (const { el } of labelNodes) el.style.display = '';
    for (const node of labelNodes) {
      node.width = node.el.offsetWidth;
      node.height = node.el.offsetHeight;
    }
    labelNodes.forEach(({ el }, i) => {
      el.style.display = displays[i];
    });
    labels.style.display = layerDisplay;
    dirty = true;
  }
  function setLocale(value: Locale) {
    locale = value;
    labels.lang = value === 'zh' ? 'zh-CN' : 'en';
    canvas.setAttribute(
      'aria-label',
      t('广西大学三维校园，方向键平移，加减键缩放，Home返回全景'),
    );
    for (const { l, el, caption } of labelNodes) {
      const name = placeName(l.name, locale);
      caption.textContent = name;
      el.title = t('查看{name}', { name });
      el.setAttribute('aria-label', el.title);
    }
    measureLabels();
  }
  function updateLabelAnchors(id?: string) {
    for (const node of labelNodes) {
      if (id && node.l.id !== id) continue;
      const key = 'landmark-' + node.l.id;
      const model = loaded.get(key) ?? baseRoot?.getObjectByName(key);
      node.point.copy(landmarkLabelAnchor(node.l, model));
      node.el.dataset.anchor = node.point
        .toArray()
        .map((v) => v.toFixed(2))
        .join(',');
    }
    dirty = true;
  }
  function setHovered(id: string | null) {
    if (hovered === id) return;
    hovered = id;
    for (const { l, el } of labelNodes)
      el.classList.toggle('linked-hover', l.id === id);
    callbacks.onHover(id);
    dirty = true;
  }
  const proxies: THREE.Mesh[] = [];
  function footprintMesh(b: {
    polygons: number[][][][];
    height: number;
    elevation: number;
  }) {
    const groupShapes = b.polygons.map((poly) => {
      const s = new THREE.Shape(
        poly[0].map((v) => new THREE.Vector2(v[0], v[1])),
      );
      for (const ring of poly.slice(1))
        s.holes.push(
          new THREE.Path(ring.map((v) => new THREE.Vector2(v[0], v[1]))),
        );
      return s;
    });
    const geo = new THREE.ExtrudeGeometry(groupShapes, {
      depth: b.height,
      bevelEnabled: false,
      steps: 1,
    });
    geo.rotateX(-Math.PI / 2);
    const mesh = new THREE.Mesh(
      geo,
      new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }),
    );
    mesh.position.y = b.elevation;
    mesh.updateMatrixWorld();
    return mesh;
  }
  let proxiesReady = false;
  function ensurePickProxies() {
    if (proxiesReady) return;
    for (const b of navigationFootprints(buildings, landmarks)) {
      const mesh = footprintMesh(b);
      mesh.userData = { id: b.landmark ?? b.id, layer: b.layer };
      proxies.push(mesh);
    }
    proxiesReady = true;
  }
  const namedBuildings = new Map(
    searchableBuildings(buildings, landmarks).map((b) => [b.id, b]),
  );
  // Only curated places participate in map hover and click selection.
  function pickTargets() {
    ensurePickProxies();
    return proxies.filter((p) => layers[p.userData.layer as LayerKey]);
  }
  function pick(clientX: number, clientY: number) {
    const rect = canvas.getBoundingClientRect();
    pointer.set(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      (-(clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, camera);
    return raycaster.intersectObjects(pickTargets(), false)[0]?.object
      .userData as { id: string } | undefined;
  }
  let hoverFrame = 0;
  let hoverPoint: { x: number; y: number } | null = null;
  function clearPointerHover() {
    canvas.style.cursor = '';
    setHovered(null);
  }
  function updatePointerHover() {
    hoverFrame = 0;
    if (!hoverPoint || tween || downPointers > 0) return;
    const hit = pick(hoverPoint.x, hoverPoint.y);
    setHovered(hit?.id ?? null);
    canvas.style.cursor = hit ? 'pointer' : '';
  }
  const highlight = new THREE.Group();
  scene.add(highlight);
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let down = { x: 0, y: 0, time: 0 };
  let maxTravel = 0;
  let downPointers = 0;
  function onDown(e: PointerEvent) {
    downPointers++;
    down = { x: e.clientX, y: e.clientY, time: performance.now() };
    maxTravel = downPointers > 1 ? 999 : 0;
  }
  function onMove(e: PointerEvent) {
    maxTravel = Math.max(
      maxTravel,
      Math.hypot(e.clientX - down.x, e.clientY - down.y),
    );
    if (e.pointerType !== 'mouse' || e.buttons) {
      clearPointerHover();
      return;
    }
    hoverPoint = { x: e.clientX, y: e.clientY };
    if (!hoverFrame) hoverFrame = requestAnimationFrame(updatePointerHover);
  }
  function onLeave() {
    hoverPoint = null;
    clearPointerHover();
  }
  function onUp(e: PointerEvent) {
    if (e.button !== 0) {
      downPointers = Math.max(0, downPointers - 1);
      return;
    }
    downPointers = Math.max(0, downPointers - 1);
    if (
      !isTap(
        down,
        { x: e.clientX, y: e.clientY, time: performance.now() },
        maxTravel,
      )
    )
      return;
    const hit = pick(e.clientX, e.clientY);
    clearPointerHover();
    if (hit) focus(hit.id);
  }
  function onCancel() {
    downPointers = 0;
    maxTravel = 999;
  }
  canvas.addEventListener('pointerdown', onDown);
  canvas.addEventListener('pointermove', onMove);
  canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointercancel', onCancel);
  canvas.addEventListener('pointerleave', onLeave);
  function moveTo(target: THREE.Vector3, position: THREE.Vector3) {
    dirty = true;
    tween = null;
    if (reduced.matches) {
      controls.target.copy(target);
      camera.position.copy(position);
      controls.update();
    } else
      tween = {
        from: camera.position.clone(),
        to: position,
        fromTarget: controls.target.clone(),
        toTarget: target,
        start: performance.now(),
      };
  }
  function focus(
    id: string,
    origin: import('./types').SelectionOrigin = 'manual',
  ) {
    const l = landmarks.find((l) => l.id === id);
    if (!l) {
      if (namedBuildings.has(id)) focusBuilding(id, origin);
      return;
    }
    setHovered(null);
    selected = id;
    restoredPose = null;
    selectedView = 'oblique';
    autoFramed = true;
    setOrbit(false);
    const c = l;
    composeViewport();
    frameLandmark();
    const radius = Math.max(
      12,
      Math.hypot(c.bounds[2] - c.bounds[0], c.bounds[3] - c.bounds[1]) * 0.54,
    );
    clearGroup(highlight);
    const mark = new THREE.Mesh(
      new THREE.RingGeometry(radius, radius + 0.6, 64),
      new THREE.MeshBasicMaterial({
        color: '#d9ae56',
        transparent: true,
        opacity: 0.8,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    mark.rotation.x = -Math.PI / 2;
    mark.position.set(c.center[0], c.elevation + 0.6, -c.center[1]);
    if (l?.placeKind === 'sports' || l?.placeKind === 'bridge') {
      mark.geometry.dispose();
      mark.material.dispose();
    } else highlight.add(mark);
    callbacks.onSelect(id, origin);
    reconcileDetails(true);
  }
  function buildingBox(b: Building) {
    const [x0, y0, x1, y1] = b.bounds;
    return new THREE.Box3(
      new THREE.Vector3(x0 - 4, b.elevation - 0.5, -y1 - 4),
      new THREE.Vector3(x1 + 4, b.elevation + b.height + 4, -y0 + 4),
    );
  }
  function focusBuilding(
    id: string,
    origin: import('./types').SelectionOrigin = 'manual',
  ) {
    const b = namedBuildings.get(id)!;
    clearPointerHover();
    selected = id;
    restoredPose = null;
    selectedView = 'oblique';
    autoFramed = true;
    setOrbit(false);
    composeViewport();
    frameLandmark();
    clearGroup(highlight);
    // A thin outline traces the footprint and roof so the building reads among its neighbours.
    const proxy = footprintMesh(b);
    const outline = new THREE.LineSegments(
      new THREE.EdgesGeometry(proxy.geometry, 30),
      new THREE.LineBasicMaterial({
        color: '#e0b552',
        transparent: true,
        opacity: 0.95,
        depthTest: false,
      }),
    );
    outline.position.copy(proxy.position);
    outline.renderOrder = 10;
    proxy.geometry.dispose();
    (proxy.material as THREE.Material).dispose();
    highlight.add(outline);
    const [x0, y0, x1, y1] = b.bounds;
    const radius = Math.max(10, Math.hypot(x1 - x0, y1 - y0) * 0.54);
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(radius, radius + 0.6, 64),
      new THREE.MeshBasicMaterial({
        color: '#d9ae56',
        transparent: true,
        opacity: 0.8,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(b.center[0], b.elevation + 0.6, -b.center[1]);
    highlight.add(ring);
    callbacks.onSelect(id, origin);
    reconcileDetails(true);
  }
  function frameLandmark(animate = true) {
    const place = landmarks.find((p) => p.id === selected);
    const building = place ? undefined : namedBuildings.get(selected ?? '');
    if (building) {
      const fit = fitBox(
        buildingBox(building),
        selectedView === 'top'
          ? new THREE.Vector3(0, 1, 0.025).normalize()
          : new THREE.Vector3(-0.5, 0.66, 1).normalize(),
        cameraFrame,
        { width: host.clientWidth, height: host.clientHeight },
        camera.fov,
      );
      if (animate) moveTo(fit.target, fit.position);
      else {
        tween = null;
        controls.target.copy(fit.target);
        camera.position.copy(fit.position);
        controls.update();
        dirty = true;
      }
      return;
    }
    if (!place) return;
    const detail = loaded.get('landmark-' + place.id);
    let box = detail
      ? new THREE.Box3().setFromObject(detail)
      : landmarkBox(place);
    if (selectedView === 'oblique') {
      const anchor = labelNodes.find((node) => node.l.id === place.id)!.point;
      // Full views include the label above small gates, which otherwise clips.
      box.expandByPoint(anchor.clone().add(new THREE.Vector3(0, 5, 0)));
    }
    if (selectedView === 'entrance' || selectedView === 'rear-entrance')
      box = entranceBox(
        place,
        box,
        selectedView === 'rear-entrance',
        buildings.find((b) => b.landmark === selected)?.architecture,
      );
    const framing = fitBox(
      box,
      landmarkDirection(
        place,
        selectedView,
        buildings.find((b) => b.landmark === selected)?.architecture,
      ),
      cameraFrame,
      { width: host.clientWidth, height: host.clientHeight },
      camera.fov,
    );
    const fitted =
      selectedView === 'entrance'
        ? bridgeEntrancePose(place, framing)
        : framing;
    if (animate) moveTo(fitted.target, fitted.position);
    else {
      tween = null;
      controls.target.copy(fitted.target);
      camera.position.copy(fitted.position);
      controls.update();
      dirty = true;
    }
  }
  function landmarkView(value: LandmarkView) {
    restoredPose = null;
    setOrbit(false);
    selectedView = value;
    composeViewport();
    autoFramed = true;
    frameLandmark();
  }
  function setOrbit(on: boolean) {
    restoredPose = null;
    orbiting =
      on && landmarks.some((p) => p.id === selected) && !reduced.matches;
    benchmarkRun = null;
    callbacks.onOrbit(orbiting);
    if (orbiting) {
      composeViewport();
      selectedView = 'oblique';
      // Asset bounds change during calibration. A benchmark must retain the
      // explicit shared camera instead of fitting each asset set differently.
      if (benchmarkOrbit) {
        tween = null;
        // Compare the same orbit directions across reloads. Otherwise the
        // page's existing 1.5 s metrics timer gives each run a different phase.
        const startedAt = performance.now();
        benchmarkRun = new BenchmarkOrbit(
          startedAt,
          camera.position.clone().sub(controls.target),
        );
        sampleStart = startedAt;
        lastFrame = startedAt;
        lastRendered = 0;
        activeFrameMs = 0;
        activeFrames = 0;
        return;
      }
      // A sphere fits through a complete rotation, including the wider sides.
      const place = landmarks.find((p) => p.id === selected)!;
      const detail = loaded.get('landmark-' + place.id);
      const box = detail
        ? new THREE.Box3().setFromObject(detail)
        : landmarkBox(place);
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      const fit = fitBox(
        new THREE.Box3().setFromCenterAndSize(
          sphere.center,
          new THREE.Vector3().setScalar(sphere.radius * 2),
        ),
        landmarkDirection(place, 'oblique'),
        cameraFrame,
        { width: host.clientWidth, height: host.clientHeight },
      );
      moveTo(fit.target, fit.position);
    }
  }
  function composeViewport() {
    cameraFrame = frame;
    camera.setViewOffset(
      host.clientWidth,
      host.clientHeight,
      host.clientWidth / 2 - (frame.left + frame.width / 2),
      host.clientHeight / 2 - (frame.top + frame.height / 2),
      host.clientWidth,
      host.clientHeight,
    );
    cameraChanged = true;
    dirty = true;
  }
  function setViewport(value: ViewportFrame, reframe = false) {
    frame = value;
    const resized =
      framedWidth !== host.clientWidth || framedHeight !== host.clientHeight;
    dirty = true;
    // A panel toggle only changes label occlusion. Preserve position, target and
    // projection, including during an orbit or an in-flight navigation tween.
    if (frameReady && !resized && !reframe) return;
    frameReady = true;
    framedWidth = host.clientWidth;
    framedHeight = host.clientHeight;
    composeViewport();
    if (restoredPose?.position) applyRestoredPose();
    else if (orbiting) setOrbit(true);
    else if (selected && autoFramed) frameLandmark();
    else if (!selected && autoFramed) overview();
    dirty = true;
  }
  function visibleTangent() {
    return (
      (Math.tan((camera.fov * Math.PI) / 360) *
        Math.min(cameraFrame.width, cameraFrame.height)) /
      host.clientHeight
    );
  }
  function getSnapshot(): CameraSnapshot {
    return {
      selected,
      view: autoFramed && !orbiting ? selectedView : null,
      preset,
      position: camera.position.toArray() as CameraSnapshot['position'],
      target: controls.target.toArray() as CameraSnapshot['target'],
      span: camera.position.distanceTo(controls.target) * visibleTangent(),
    };
  }
  function applyRestoredPose() {
    if (!restoredPose?.position || !restoredPose.target || !restoredPose.span)
      return;
    const target = new THREE.Vector3(...restoredPose.target);
    const offset = new THREE.Vector3(...restoredPose.position)
      .sub(target)
      .normalize();
    const distance = Math.max(
      controls.minDistance,
      Math.min(controls.maxDistance, restoredPose.span / visibleTangent()),
    );
    tween = null;
    autoFramed = false;
    controls.target.copy(target);
    camera.position.copy(target).addScaledVector(offset, distance);
    controls.update();
    dirty = true;
  }
  function restoreSnapshot(snapshot: Partial<CameraSnapshot>) {
    if (snapshot.preset) setPreset(snapshot.preset);
    if (snapshot.selected) {
      focus(snapshot.selected, 'restore');
      if (snapshot.view) landmarkView(snapshot.view);
    }
    restoredPose = snapshot.position ? snapshot : null;
    if (frameReady) applyRestoredPose();
  }
  function overview(animate = true) {
    const box = new THREE.Box3(
      new THREE.Vector3(-920, -10, -1260),
      new THREE.Vector3(1000, 65, 1300),
    );
    const direction = new THREE.Vector3(0.55, 1.1, 1);
    const viewport = { width: host.clientWidth, height: host.clientHeight };
    const { target: t, position: p } = overviewPoints
      ? fitPoints(overviewPoints, direction, cameraFrame, viewport)
      : fitBox(box, direction, cameraFrame, viewport);
    if (animate) moveTo(t, p);
    else {
      controls.target.copy(t);
      camera.position.copy(p);
      controls.update();
    }
  }
  overview(false);
  function classify(o: THREE.Object3D) {
    let p: THREE.Object3D | null = o;
    while (p) {
      if (p.userData.layer) return p.userData.layer as string;
      p = p.parent;
    }
    return '';
  }
  function styleMeshes(root: THREE.Object3D, refineTerrain = true) {
    root.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return;
      if (refineTerrain) palette.terrain(o);
      o.castShadow = true;
      o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (m instanceof THREE.MeshStandardMaterial) {
          palette.surface(m);
          contextStyle.apply(m);
          if (
            ['sportWhite', 'roadWhite', 'roadYellow', 'tactile'].includes(
              m.name,
            )
          ) {
            // Paint is a decal surface: bias its depth at oblique/distant views
            // as well as retaining geometric separation through Draco export.
            m.polygonOffset = true;
            m.polygonOffsetFactor = -2;
            m.polygonOffsetUnits = -2;
            o.castShadow = false;
          }
          if (m.name === 'water') {
            o.castShadow = false;
            m.roughness = 0.3;
            m.metalness = 0.28;
          }
          if (m.name === 'timeSilver') m.envMapIntensity = 1.5;
          if (m.name === 'timeLight' || m.name === 'timeSilver') {
            m.emissive.set('#83b6e2');
            m.emissiveIntensity =
              preset === 'night' ? (m.name === 'timeLight' ? 1.8 : 0.16) : 0;
          }
        }
      }
      nightStyle.apply(o, preset === 'night');
    });
  }
  function syncRoadLights() {
    if (preset === 'night' && baseRoot && !roadLights) {
      roadLights = createRoadLights(baseRoot);
      scene.add(roadLights);
    }
    if (roadLights) {
      roadLights.visible = preset === 'night' && layers.roads;
      roadLights.material.uniforms.pixelRatio.value = renderer.getPixelRatio();
    }
  }
  function detailLayer(key: string): LayerKey {
    if (key.startsWith('basketball-bank-')) return 'sports';
    return key.startsWith('infra-') ||
      landmarks.some(
        (l) => 'landmark-' + l.id === key && l.placeKind === 'bridge',
      )
      ? 'roads'
      : 'buildings';
  }
  function applyLayers() {
    for (const [key, root] of loaded) {
      const isZone =
        key.startsWith('chunk-') ||
        key.startsWith('infra-') ||
        key.startsWith('basketball-bank-');
      root.visible = layers[detailLayer(key)] && (!isZone || !modeSmooth);
    }
    if (baseRoot)
      for (const child of baseRoot.children)
        child.visible =
          (layers[classify(child) as LayerKey] ?? true) &&
          !loaded.get(child.name)?.visible;
    syncRoadLights();
    boundaryRoot.visible = layers.boundary;
    if (treesRoot) treesRoot.visible = layers.vegetation;
    labels.style.display = layers.labels ? '' : 'none';
    highlight.visible = layers[detailLayer('landmark-' + selected)];
    // Model attach/release, tree density, quality and layer changes all arrive here.
    renderer.shadowMap.needsUpdate = true;
    dirty = true;
  }
  function updateLoadStatus() {
    if (disposed) return;
    const foreground =
      progresses.get('landmark-' + selected) ??
      progresses.get('base') ??
      progresses.values().next().value;
    if (foreground) {
      const percent = Math.round(foreground.fraction * 100);
      // A request that has not reported bytes yet shows no misleading 0%.
      callbacks.onStatus(
        {
          text: foreground.name
            ? percent
              ? '正在加载{name} {percent}%'
              : '正在加载{name}'
            : percent
              ? '{label} {percent}%'
              : '{label}',
          values: {
            label: foreground.label,
            name: foreground.name ?? '',
            percent,
          },
        },
        false,
        foreground.fraction,
      );
    } else if (boundaryFailed && layers.boundary)
      callbacks.onStatus('校园边界加载失败，可重试', true);
    else if (treesFailed || (highTreesFailed && !modeSmooth))
      callbacks.onStatus('部分树木加载失败，可重试', true);
    else if ([...failed.keys()].some((key) => wanted.has(key)))
      callbacks.onStatus('部分细节加载失败，可重试', true);
    else if (initialReady) callbacks.onStatus('');
  }
  async function loadGLB(
    a: Asset,
    key = 'base',
    signal = lifecycle.signal,
    prefetched?: BasePrefetch,
  ) {
    const label =
      key === 'base'
        ? '正在加载校园'
        : key.startsWith('trees')
          ? '正在加载树木'
          : key.startsWith('landmark-')
            ? '正在加载{name}'
            : '正在加载周边细节';
    const progress = (fraction: number) => {
      progresses.set(key, {
        label,
        fraction,
        name: key.startsWith('landmark-')
          ? (landmarks.find((l) => 'landmark-' + l.id === key)?.name ?? '地标')
          : undefined,
      });
      updateLoadStatus();
    };
    let unsubscribe: (() => void) | undefined;
    try {
      let buffer: ArrayBuffer;
      if (prefetched) {
        unsubscribe = prefetched.onProgress(progress);
        buffer = await prefetched.base;
      } else buffer = await fetchModel(modelUrl(a), a.bytes, signal, progress);
      signal.throwIfAborted();
      const gltf = await loader.parseAsync(buffer, asset('models/'));
      if (disposed || signal.aborted) {
        disposeObject(gltf.scene);
        throw new DOMException('Request cancelled', 'AbortError');
      }
      loadedBytes += a.bytes;
      const yieldLoading = async () => {
        await new Promise<void>((resolve) => setTimeout(resolve, 0));
        signal.throwIfAborted();
        if (disposed) throw new DOMException('Scene disposed', 'AbortError');
      };
      try {
        if (key !== 'base') palette.buildings(gltf.scene, key);
        styleMeshes(gltf.scene, key !== 'base');
        await yieldLoading();
        batchSportsSurfaces(gltf.scene);
        await yieldLoading();
        batchStaticRoadSurfaces(gltf.scene);
        await yieldLoading();
        if (key === 'base') pruneGroundTriangles(gltf.scene);
        return gltf;
      } catch (error) {
        // A cancelled detail must not leak a decoded root while yielding.
        disposeObject(gltf.scene);
        throw error;
      }
    } finally {
      unsubscribe?.();
      progresses.delete(key);
      updateLoadStatus();
    }
  }
  function releaseDetail(key: string) {
    const root = loaded.get(key);
    if (!root) return;
    dynamic.remove(root);
    disposeObject(root, [scene]);
    loaded.delete(key);
    if (key.startsWith('landmark-'))
      updateLabelAnchors(key.slice('landmark-'.length));
    recentlyUsed.delete(key);
  }
  function detailCost(root: THREE.Object3D) {
    const buffers = new Set<ArrayBufferLike>();
    root.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return;
      for (const attribute of Object.values(o.geometry.attributes) as (
        | THREE.BufferAttribute
        | THREE.InterleavedBufferAttribute
      )[]) {
        const a =
          attribute instanceof THREE.InterleavedBufferAttribute
            ? attribute.data.array
            : attribute.array;
        buffers.add(a.buffer);
      }
      if (o.geometry.index) buffers.add(o.geometry.index.array.buffer);
    });
    return [...buffers].reduce((n, buffer) => n + buffer.byteLength, 0);
  }
  function reconcileDetails(focusing = false) {
    if (!manifest || disposed || !initialReady) return;
    const cap = profile.detailBudgetMiB * 1048576;
    const currentKey = 'landmark-' + selected;
    const foreground = manifest.landmarks.find((a) => a.id === selected);
    // A flight selects details around its destination, not the passing campus area.
    const destination = tween?.toTarget ?? controls.target;
    const destinationCamera = tween?.to ?? camera.position;
    const x = destination.x;
    const y = -destination.z;
    const near =
      !modeSmooth &&
      (focusing || destinationCamera.distanceTo(destination) < 1050);
    const candidates =
      near && layers.buildings ? nearbyChunks(manifest.zones, x, y) : [];
    // Keep in-flight building chunks ahead of new background work.
    candidates.sort(
      (a, b) =>
        Number(Boolean(detailQueue.tasks.get(b.asset.id!)?.started)) -
        Number(Boolean(detailQueue.tasks.get(a.asset.id!)?.started)),
    );
    const plan = planDetails({
      foreground:
        foreground && layers[detailLayer(currentKey)]
          ? [currentKey, foreground]
          : undefined,
      foregroundReady: loaded.has(currentKey),
      roads:
        near && layers.roads
          ? nearbyChunks(manifest.infrastructure ?? [], x, y, 230).map(
              ({ asset }) => asset,
            )
          : [],
      buildings: candidates.map(({ asset }) => asset),
      sports:
        near && layers.sports && destinationCamera.distanceTo(destination) < 300
          ? nearbyChunks(manifest.sports ?? [], x, y, 120).map(
              ({ asset }) => asset,
            )
          : [],
      costs: geometryCosts,
      cap,
    });
    const wantedAssets = plan.assets;
    let allocation = plan.allocation;
    wanted.clear();
    wantedAssets.forEach(([key]) => wanted.add(key));
    for (const key of detailQueue.tasks.keys())
      if (key !== 'trees-near' && !wanted.has(key)) detailQueue.cancel(key);
    for (const key of failed.keys()) if (!wanted.has(key)) failed.delete(key);
    // One recent landmark can stay warm if it fits the decoded-geometry budget.
    const older = [...loaded.keys()]
      .filter((key) => !wanted.has(key))
      .sort((a, b) => (recentlyUsed.get(b) ?? 0) - (recentlyUsed.get(a) ?? 0));
    let warm = false;
    for (const key of older) {
      const cost = geometryCosts.get(key) ?? 0;
      if (
        !warm &&
        key.startsWith('landmark-') &&
        layers[detailLayer(key)] &&
        allocation + cost <= cap
      ) {
        allocation += cost;
        warm = true;
      } else releaseDetail(key);
    }
    for (const [index, [key, a]] of wantedAssets.entries()) {
      if (loaded.has(key)) recentlyUsed.set(key, performance.now());
      else loadDetail(a, key, index);
    }
    if (
      profile.nearTrees &&
      treesRoot &&
      manifest.treesNear &&
      !highTreesReady &&
      !highTreesFailed &&
      !loading.has('trees') &&
      !detailQueue.tasks.has('trees-near') &&
      destinationCamera.distanceTo(destination) < 1000
    )
      void detailQueue
        .enqueue('trees-near', 5, (signal) => loadTrees(true, signal))
        .catch((error) => {
          if (!disposed && error?.name !== 'AbortError')
            callbacks.onStatus('近处树木加载失败，可重试', true);
        });
    applyLayers();
    updateLoadStatus();
  }
  function loadDetail(a: Asset, key: string, priority = 2) {
    if (
      loaded.has(key) ||
      detailQueue.tasks.has(key) ||
      failed.has(key) ||
      disposed
    )
      return;
    void detailQueue
      .enqueue(key, priority, async (signal) => {
        const g = await loadGLB(a, key, signal);
        if (disposed || !wanted.has(key)) {
          disposeObject(g.scene);
          return;
        }
        dynamic.add(g.scene);
        loaded.set(key, g.scene);
        if (key.startsWith('landmark-'))
          updateLabelAnchors(key.slice('landmark-'.length));
        recentlyUsed.set(key, performance.now());
        geometryCosts.set(key, detailCost(g.scene));
        failed.delete(key);
        if (key === 'landmark-' + selected && autoFramed && !orbiting)
          frameLandmark();
        reconcileDetails();
      })
      .catch((error) => {
        if (!disposed && error?.name !== 'AbortError') {
          failed.set(key, a);
          updateLoadStatus();
        }
      })
      .finally(() => {
        if (!disposed) pendingRequest = performance.now();
      });
  }
  async function loadTrees(near = false, signal = lifecycle.signal) {
    if (
      !manifest ||
      (near ? highTreesReady || !manifest.treesNear : treesRoot) ||
      loading.has('trees')
    )
      return;
    loading.add('trees');
    try {
      const [data, terrain] = treeData
        ? [treeData.data, treeData.terrain]
        : await Promise.all([
            fetch(asset('data/vegetation.json'), {
              signal: lifecycle.signal,
            }).then((r) => {
              if (!r.ok) throw new Error('vegetation');
              return r.json();
            }) as Promise<number[][]>,
            fetch(asset('data/terrain.json'), {
              signal: lifecycle.signal,
            }).then((r) => {
              if (!r.ok) throw new Error('terrain');
              return r.json();
            }) as Promise<{
              bounds: number[];
              cols: number;
              rows: number;
              heights: number[];
            }>,
          ]);
      if (disposed) return;
      treeData = { data, terrain };
      const g = await loadGLB(
        near ? manifest.treesNear! : manifest.trees,
        near ? 'trees-near' : 'trees',
        signal,
      );
      if (!treesRoot) {
        treesRoot = new THREE.Group();
        treesRoot.name = 'vegetation';
        treesRoot.userData.layer = 'vegetation';
        scene.add(treesRoot);
      }
      const parts: THREE.Mesh[] = [];
      g.scene.traverse((o) => {
        if (o instanceof THREE.Mesh) parts.push(o);
      });
      for (let typ = 0; typ < 3; typ++) {
        const partsForType = parts.filter((o) => {
          let p: THREE.Object3D | null = o;
          while (p) {
            if (
              p.userData.template === typ ||
              p.name === `Tree-template-${typ}`
            )
              return true;
            p = p.parent;
          }
          return false;
        });
        if (!partsForType.length) continue;
        const geometries = partsForType.map((part) => {
          const geometry = part.geometry.index
            ? part.geometry.toNonIndexed()
            : part.geometry.clone();
          const material = (
            Array.isArray(part.material) ? part.material[0] : part.material
          ) as THREE.MeshStandardMaterial;
          const color = material.color;
          const colors = new Float32Array(
            geometry.getAttribute('position').count * 3,
          );
          for (let i = 0; i < colors.length; i += 3) {
            colors[i] = color.r;
            colors[i + 1] = color.g;
            colors[i + 2] = color.b;
          }
          geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
          geometry.deleteAttribute('uv');
          return geometry;
        });
        const geometry = mergeGeometries(geometries)!;
        geometries.forEach((g) => g.dispose());
        const material = new THREE.MeshStandardMaterial({
          name: 'treeCanopy',
          vertexColors: true,
          roughness: 0.94,
          side: THREE.DoubleSide,
        });
        const sectors = new Map<string, number[][]>();
        for (const row of data) {
          if (row[3] !== typ) continue;
          const key = `${Math.floor(row[0] / 450)},${Math.floor(row[1] / 450)}`;
          if (!sectors.has(key)) sectors.set(key, []);
          sectors.get(key)!.push(row);
        }
        for (const sectorRows of sectors.values()) {
          const rows = prioritizeTreeRows(
            sectorRows,
            manifest.treePriorityPositions || [],
          );
          const inst = new THREE.InstancedMesh(geometry, material, rows.length);
          const transform = new THREE.Object3D();
          rows.forEach((row, i) => {
            const [x, y, h] = row;
            transform.position.set(x, treeElevation(row, terrain), -y);
            transform.rotation.set(0, treeRotation(x, y), 0);
            const appearance = treeAppearance(x, y);
            transform.scale.set(
              (appearance.width * h) / 9,
              (appearance.height * h) / 9,
              (appearance.width * h) / 9,
            );
            transform.updateMatrix();
            inst.setMatrixAt(i, transform.matrix);
            inst.setColorAt(i, new THREE.Color(...appearance.tint));
          });
          nightStyle.apply(inst, preset === 'night');
          inst.instanceMatrix.needsUpdate = true;
          inst.computeBoundingSphere();
          inst.castShadow = true;
          inst.receiveShadow = true;
          inst.userData.fullCount = rows.length;
          inst.userData.lod = near ? 1 : 0;
          inst.userData.center = new THREE.Vector3(
            rows.reduce((sum, r) => sum + r[0], 0) / rows.length,
            0,
            -rows.reduce((sum, r) => sum + r[1], 0) / rows.length,
          );
          treesRoot.add(inst);
        }
      }
      disposeObject(g.scene);
      if (near) highTreesReady = true;
      // Materials and geometry are shared with the instanced meshes and disposed once during teardown.
      setQuality(quality);
      applyLayers();
    } catch (error) {
      if (!disposed && !signal.aborted) {
        if (near) highTreesFailed = true;
        else treesFailed = true;
      }
      throw error;
    } finally {
      loading.delete('trees');
      pendingRequest = performance.now();
    }
  }
  function applyTreeLOD() {
    if (!treesRoot) return;
    for (const o of treesRoot.children) {
      const near =
        highTreesReady &&
        profile.nearTrees &&
        camera.position.distanceTo(o.userData.center) < 500;
      const visible = o.userData.lod === 1 ? near : !near;
      if (o.visible !== visible) renderer.shadowMap.needsUpdate = true;
      o.visible = visible;
    }
  }
  async function loadBoundary() {
    if (boundaryLoading || boundaryReady || disposed) return;
    boundaryLoading = true;
    try {
      const data = await fetchJson<CampusBoundary>(
        asset('data/campus-boundary.json'),
        lifecycle.signal,
      );
      if (disposed) return;
      boundaryRoot.add(createBoundary(data));
      contextStyle.setBoundary(data);
      overviewPoints = campusOverviewPoints(data.rings, buildings, landmarks);
      if (!selected && autoFramed && !restoredPose?.position) overview();
      boundaryReady = true;
      boundaryFailed = false;
      applyLayers();
    } catch {
      if (!disposed) boundaryFailed = true;
    } finally {
      boundaryLoading = false;
      if (!disposed) updateLoadStatus();
    }
  }
  async function initialize() {
    if (loading.has('base') || initialReady) return;
    loading.add('base');
    callbacks.onStatus('正在加载校园…');
    // A failed prefetch is not reused: retries go through the normal fetches.
    const boot = pendingPrefetch;
    pendingPrefetch = undefined;
    try {
      manifest = await (boot?.manifest ??
        fetchJson<Manifest>(asset('data/models.json'), lifecycle.signal));
      if (disposed) return;
      const gltf = await loadGLB(manifest.base, 'base', lifecycle.signal, boot);
      baseRoot = gltf.scene;
      scene.add(baseRoot);
      updateLabelAnchors();
      const terrainMesh: THREE.Mesh[] = [];
      baseRoot.traverse((o) => {
        if (
          o instanceof THREE.Mesh &&
          o.material instanceof THREE.MeshStandardMaterial &&
          o.material.name === 'grass'
        )
          terrainMesh.push(o);
      });
      if (terrainMesh[0]) {
        const mat = terrainMesh[0].material as THREE.MeshStandardMaterial;
        ground.material.dispose();
        ground.material = mat.clone();
        nightStyle.copyDayColor(mat, ground.material);
        nightStyle.apply(ground, preset === 'night');
        contextStyle.apply(ground.material);
        const uv = ground.geometry.getAttribute('uv');
        for (let i = 0; i < uv.count; i++)
          uv.setXY(i, uv.getX(i) * 7500, uv.getY(i) * 7500);
        uv.needsUpdate = true;
      }
      initialReady = true;
      syncEffects();
      readyMs = Math.round(performance.now());
      applyLayers();
      callbacks.onReady();
      callbacks.onStatus('');
      // Publish and paint the base before optional CPU-side colour/normal refinement.
      // No additional model or texture transfer; deferred work keeps startup latency flat.
      requestAnimationFrame(() => {
        if (disposed) return;
        const refine = async () => {
          if (disposed || !baseRoot) return;
          palette.buildings(baseRoot, 'base');
          const meshes: THREE.Mesh[] = [];
          baseRoot.traverse((o) => {
            if (o instanceof THREE.Mesh) meshes.push(o);
          });
          // Keep the original summation order and publish the GPU normal buffer
          // only once it is complete. Yield between bounded vertex batches.
          for (const mesh of meshes) {
            const steps = palette.terrainSteps(mesh);
            while (!disposed) {
              const step = steps.next();
              if (step.done) break;
              await new Promise<void>((resolve) => setTimeout(resolve, 0));
            }
            if (disposed) return;
          }
          renderer.shadowMap.needsUpdate = true;
          dirty = true;
        };
        if ('requestIdleCallback' in window)
          window.requestIdleCallback(refine, { timeout: 1500 });
        else setTimeout(refine, 0);
      });
      void loadBoundary();
      reconcileDetails();
      void loadTrees().catch(() => {
        if (!disposed) callbacks.onStatus('树木加载失败，可重试', true);
      });
    } catch {
      if (!disposed) callbacks.onStatus('校园加载失败，请检查网络后重试', true);
    } finally {
      loading.delete('base');
    }
  }
  function setQuality(q: Quality) {
    if (q !== quality) {
      adaptive.reset();
      effectsFailed = false;
    }
    quality = q;
    applyQuality();
  }
  function applyQuality() {
    profile = qualityProfile(quality, compact(), saveData(), adaptive.level);
    modeSmooth = profile.level === 2;
    renderer.setPixelRatio(
      Math.min(window.devicePixelRatio, profile.pixelRatio) *
        profile.resolutionScale,
    );
    renderer.shadowMap.enabled = profile.shadows;
    sun.castShadow = profile.shadows;
    syncEffects();
    if (!profile.shadows) {
      sun.shadow.dispose();
      sun.shadow.map = null;
      sun.shadow.mapPass = null;
    }
    if (!profile.nearTrees) {
      detailQueue.cancel('trees-near');
      if (treesRoot && highTreesReady) {
        const retired = new THREE.Group();
        for (const child of treesRoot.children.slice())
          if (child.userData.lod === 1) retired.add(child);
        disposeObject(retired, [scene]);
        highTreesReady = false;
      }
    }
    treesRoot?.traverse((o) => {
      if (o instanceof THREE.InstancedMesh)
        o.count = Math.ceil(o.userData.fullCount * profile.treeDensity);
    });
    dirty = true;
    applyLayers();
    reconcileDetails();
  }
  function setPreset(p: Preset) {
    preset = p;
    scene.fog = sky.setPreset(p);
    const light = LIGHTING[p];
    sun.color.set(light.sun);
    sun.intensity = light.power;
    ambient.color.set(light.skyLight);
    ambient.groundColor.set(light.bounce);
    ambient.intensity = light.hemisphere;
    fill.color.set(light.fill);
    fill.intensity = light.fillPower;
    scene.environmentIntensity = light.environment;
    renderer.toneMappingExposure = light.exposure;
    // shadowFrustum owns the target-relative light position, including when
    // reapplying the same preset while its cached volume is unchanged.
    effects?.setNight(p === 'night');
    syncRoadLights();
    labels.dataset.light = p;
    scene.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return;
      nightStyle.apply(o, p === 'night');
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (!(m instanceof THREE.MeshStandardMaterial)) continue;
        if (m.name === 'timeSilver' || m.name === 'timeLight') {
          m.emissive.set('#83b6e2');
          m.emissiveIntensity =
            p === 'night' ? (m.name === 'timeSilver' ? 0.16 : 1.8) : 0;
        }
      }
    });
    if (p === 'night') {
      // Pane attributes are created lazily; include them in the existing LOD budget.
      for (const [key, root] of loaded)
        geometryCosts.set(key, detailCost(root));
      reconcileDetails();
    }
    dirty = true;
  }
  function view(v: string) {
    restoredPose = null;
    setOrbit(false);
    if (v === 'overview') {
      setHovered(null);
      composeViewport();
      autoFramed = true;
      selected = null;
      callbacks.onSelect(null);
      clearGroup(highlight);
      overview();
      return;
    }
    autoFramed = false;
    if (v === 'top' || v === 'tilt' || v === 'north') composeViewport();
    const t = controls.target.clone();
    const offset = camera.position.clone().sub(t);
    if (v === 'top')
      moveTo(t, t.clone().add(new THREE.Vector3(0, offset.length(), 0.01)));
    else if (v === 'tilt')
      moveTo(
        t,
        t
          .clone()
          .add(
            new THREE.Vector3(-0.45, 0.66, 0.8)
              .normalize()
              .multiplyScalar(offset.length()),
          ),
      );
    else if (v === 'north')
      moveTo(
        t,
        t
          .clone()
          .add(new THREE.Vector3(0, offset.y, Math.hypot(offset.x, offset.z))),
      );
    else {
      const factor = v === 'zoomIn' ? 0.75 : 1.33;
      const d = Math.max(
        controls.minDistance,
        Math.min(controls.maxDistance, offset.length() * factor),
      );
      moveTo(t, t.clone().add(offset.normalize().multiplyScalar(d)));
    }
  }
  function onKey(e: KeyboardEvent) {
    const dirs: Record<string, [number, number]> = {
      ArrowUp: [0, -1],
      ArrowDown: [0, 1],
      ArrowLeft: [-1, 0],
      ArrowRight: [1, 0],
    };
    if (dirs[e.key]) {
      e.preventDefault();
      callbacks.onInteract();
      autoFramed = false;
      setOrbit(false);
      tween = null;
      const d = camera.position.distanceTo(controls.target) * 0.035;
      const [x, z] = dirs[e.key];
      camera.position.x += x * d;
      camera.position.z += z * d;
      controls.target.x += x * d;
      controls.target.z += z * d;
      dirty = true;
    } else if (['+', '=', '-', 'Home'].includes(e.key)) {
      e.preventDefault();
      callbacks.onInteract();
      view(
        e.key === 'Home' ? 'overview' : e.key === '-' ? 'zoomOut' : 'zoomIn',
      );
    }
  }
  canvas.addEventListener('keydown', onKey);
  controls.addEventListener('start', () => {
    tween = null;
    autoFramed = false;
    setOrbit(false);
    callbacks.onInteract();
    dirty = true;
  });
  controls.addEventListener('change', () => {
    cameraChanged = true;
    dirty = true;
    pendingRequest = performance.now();
  });
  function resize() {
    const rect = host.getBoundingClientRect();
    labelViewport.width = rect.width;
    labelViewport.height = rect.height;
    measureLabels();
    const w = host.clientWidth,
      h = host.clientHeight;
    renderer.setSize(w, h);
    // Preserve the current optical centre until the measured viewport arrives.
    // ResizeObserver may also fire without an actual canvas size change.
    const previousView = camera.view;
    camera.setViewOffset(
      w,
      h,
      previousView ? (previousView.offsetX * w) / previousView.fullWidth : 0,
      previousView ? (previousView.offsetY * h) / previousView.fullHeight : 0,
      w,
      h,
    );
    setQuality(quality);
    dirty = true;
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  resize();
  function shadowFrustum() {
    const size = Math.min(
      1700,
      Math.max(100, camera.position.distanceTo(controls.target) * 0.8),
    );
    const t = controls.target;
    if (!shadowVolume.changed(t.x, t.y, t.z, size, preset)) return;
    renderer.shadowMap.needsUpdate = true;
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
  }
  function metrics(): Metrics {
    const mem = (
      performance as Performance & { memory?: { usedJSHeapSize: number } }
    ).memory;
    return {
      readyMs,
      postprocessing: effects
        ? 'ready'
        : effectsFailed
          ? 'failed'
          : effectsLoading
            ? 'loading'
            : 'off',
      ...(benchmarkOrbit
        ? {
            benchmark: {
              orbiting,
              elapsedMs: benchmarkRun?.elapsedMs ?? 0,
              sampleIndex: benchmarkRun?.sampleIndex ?? 0,
              camera: getSnapshot(),
              viewport: [host.clientWidth, host.clientHeight],
              frame: { ...cameraFrame },
            },
          }
        : {}),
      heapMiB: mem ? Math.round(mem.usedJSHeapSize / 1048576) : null,
      shadowUpdates,
      fps: Math.round(fps),
      triangles: renderer.info.render.triangles,
      drawCalls: renderer.info.render.calls,
      geometries: renderer.info.memory.geometries,
      textures: renderer.info.memory.textures,
      pixelRatio: renderer.getPixelRatio(),
      quality: ['精细', '均衡', '流畅'][profile.level],
      automaticQualityLevel: adaptive.level,
      shadows: profile.shadows,
      nearTrees: profile.nearTrees,
      detailBudgetMiB: profile.detailBudgetMiB,
      loadedBytes,
      loadedDetails: [...loaded.keys()],
      queuedDetails: detailQueue.tasks.size,
      residentDetailBytes: [...loaded.keys()].reduce(
        (n, key) =>
          n +
          (manifest?.landmarks.find((a) => 'landmark-' + a.id === key)?.bytes ??
            manifest?.zones.find((a) => a.id === key)?.bytes ??
            manifest?.infrastructure?.find((a) => a.id === key)?.bytes ??
            manifest?.sports?.find((a) => a.id === key)?.bytes ??
            0),
        0,
      ),
      detailGeometryMiB:
        Math.round(
          ([...loaded.keys()].reduce(
            (n, key) => n + (geometryCosts.get(key) ?? 0),
            0,
          ) /
            1048576) *
            10,
        ) / 10,
    };
  }
  function animate(time: number) {
    if (disposed) return;
    loop = requestAnimationFrame(animate);
    if (!framePacer.shouldUpdate(time, modeSmooth)) return;
    const moving = controls.update();
    if (orbiting && !tween) {
      if (reduced.matches) setOrbit(false);
      else {
        const offset = benchmarkRun
          ? benchmarkRun.position(time)
          : orbitOffset
              .subVectors(camera.position, controls.target)
              .applyAxisAngle(
                orbitAxis,
                Math.min(0.05, (time - lastFrame) / 1000) * 0.13,
              );
        camera.position.copy(controls.target).add(offset);
        camera.lookAt(controls.target);
        dirty = true;
      }
    }
    if (tween) {
      const f = Math.min(1, (time - tween.start) / 1300);
      const e = 1 - (1 - f) ** 3;
      camera.position.lerpVectors(tween.from, tween.to, e);
      controls.target.lerpVectors(tween.fromTarget, tween.toTarget, e);
      if (f === 1) tween = null;
      dirty = true;
    }
    if (dirty || moving || tween) {
      cameraChanged = true;
      // A 1 m near plane wastes depth precision at campus-wide altitude,
      // causing thin road/terrain surfaces to flicker in the overview.
      const near = Math.max(1, Math.min(100, (camera.position.y - 50) * 0.01));
      if (camera.near !== near) {
        camera.near = near;
        camera.updateProjectionMatrix();
      }
      shadowFrustum();
      applyTreeLOD();
      convexCulling?.update(camera, modeSmooth && !renderer.shadowMap.enabled);
      renderScene();
      // Paint the complete geometry first. Only the shadow-free smooth tier
      // needs this CPU-side optimisation; switching away cancels its need.
      if (
        baseRoot &&
        modeSmooth &&
        !renderer.shadowMap.enabled &&
        !convexCulling &&
        convexPreparation === undefined
      ) {
        convexPreparation = setTimeout(() => {
          convexPreparation = undefined;
          if (
            disposed ||
            !baseRoot ||
            !modeSmooth ||
            renderer.shadowMap.enabled
          )
            return;
          convexCulling = createConvexCulling(baseRoot);
          dirty = true;
        }, 0);
      }
      dirty = false;
      lastFrame = time;
      if (
        lastRendered &&
        (time - lastRendered < 1000 || orbiting || moving || tween)
      ) {
        activeFrameMs += time - lastRendered;
        activeFrames++;
      }
      lastRendered = time;
      if (orderedHover !== hovered || orderedSelection !== selected) {
        orderedHover = hovered;
        orderedSelection = selected;
        // Reset tie order to the catalogue order, matching the previous sort.
        for (let i = 0; i < labelNodes.length; i++)
          labelOrder[i] = labelNodes[i];
        labelOrder.sort(
          (a, b) =>
            Number(b.l.id === hovered) * 2 +
            Number(b.l.id === selected) -
            (Number(a.l.id === hovered) * 2 + Number(a.l.id === selected)),
        );
      }
      const occupied = occupiedLabels;
      occupied.length = 0;
      for (const { l, el, point, width, height, bounds } of labelOrder) {
        const p = labelProjection.copy(point).project(camera);
        const dist = camera.position.distanceTo(point);
        const x = ((p.x + 1) * labelViewport.width) / 2,
          y = ((-p.y + 1) * labelViewport.height) / 2;
        bounds[0] = x - width / 2;
        bounds[1] = y - height;
        bounds[2] = x + width / 2;
        bounds[3] = y;
        const overlap = occupied.some(
          (r) =>
            bounds[0] < r[2] + 6 &&
            bounds[2] > r[0] - 6 &&
            bounds[1] < r[3] + 6 &&
            bounds[3] > r[1] - 6,
        );
        const obscured =
          bounds[0] < frame.left ||
          bounds[2] > frame.left + frame.width ||
          bounds[1] < frame.top ||
          bounds[3] > frame.top + frame.height;
        const hidden =
          (l.placeKind === 'sports'
            ? !layers.sports
            : !layers[detailLayer('landmark-' + l.id)]) ||
          p.z < 0 ||
          p.z > 1 ||
          Math.abs(p.x) > 1 ||
          Math.abs(p.y) > 1 ||
          (selected && dist > 650) ||
          overlap ||
          obscured;
        el.style.display = hidden ? 'none' : '';
        if (!hidden) occupied.push(bounds);
        el.style.transform = `translate(${x}px,${y}px) translate(-50%,-100%)`;
        el.classList.toggle('active', selected === l.id);
      }
    }

    if (cameraChanged && time - cameraSampleAt > 200) {
      callbacks.onCamera(getSnapshot());
      cameraSampleAt = time;
      cameraChanged = false;
    }
    if (benchmarkRun ? benchmarkRun.sampleDue() : time - sampleStart > 1500) {
      if (activeFrames > 0 && activeFrameMs > 0)
        fps = (1000 * activeFrames) / activeFrameMs;
      callbacks.onMetrics?.(metrics());
      if (quality === 'auto' && !compact() && !saveData() && !document.hidden) {
        if (
          adaptive.sample(
            fps,
            activeFrames,
            orbiting || Boolean(tween) || Boolean(moving),
          )
        )
          applyQuality();
      }
      activeFrameMs = 0;
      activeFrames = 0;
      sampleStart = time;
    }
    if (
      manifest &&
      initialReady &&
      pendingRequest &&
      time - pendingRequest > 450
    ) {
      pendingRequest = 0;
      reconcileDetails();
    }
  }
  loop = requestAnimationFrame(animate);
  void initialize();
  const onLost = (event: Event) => {
    event.preventDefault();
    callbacks.onStatus('图形显示中断，恢复后将自动重绘，也可刷新页面', true);
  };
  const onRestored = () => {
    callbacks.onStatus('');
    renderer.shadowMap.autoUpdate = false;
    renderer.shadowMap.needsUpdate = true;
    dirty = true;
  };
  canvas.addEventListener('webglcontextlost', onLost);
  canvas.addEventListener('webglcontextrestored', onRestored);
  return {
    focus,
    setHovered,
    landmarkView,
    setOrbit,
    setViewport,
    setLayer: (key, on) => {
      if (!on) setHovered(null);
      layers[key] = on;
      applyLayers();
      if (key === 'buildings' || key === 'roads' || key === 'sports')
        reconcileDetails();
      if (key === 'boundary' && on) void loadBoundary();
      updateLoadStatus();
    },
    setPreset,
    setQuality,
    view,
    exportImage: async () => {
      convexCulling?.update(camera, modeSmooth && !renderer.shadowMap.enabled);
      renderScene();
      const out = document.createElement('canvas');
      out.width = canvas.width;
      out.height = canvas.height;
      const ctx = out.getContext('2d');
      if (!ctx) throw new Error('Canvas unavailable');
      ctx.drawImage(canvas, 0, 0);
      const size = Math.max(15, Math.round(out.width / 110));
      ctx.font = `${size}px sans-serif`;
      const segments = [t('广西大学 校园地图'), '© OpenStreetMap contributors'];
      if (layers.boundary && boundaryReady)
        segments.push(t('白色细线：校园大致边界'));
      const label = segments.join('  |  ');
      const available = out.width - size * 2;
      const lines =
        ctx.measureText(label).width <= available ? [label] : segments;
      const lineHeight = size * 1.5;
      const footerHeight = lineHeight * lines.length + size;
      ctx.fillStyle = '#1d3b31dd'; // Radix jade-12
      ctx.fillRect(0, out.height - footerHeight, out.width, footerHeight);
      ctx.fillStyle = 'white';
      for (let i = 0; i < lines.length; i++) {
        ctx.font = `${size}px sans-serif`;
        const fittedSize = Math.min(
          size,
          (size * available) / ctx.measureText(lines[i]).width,
        );
        ctx.font = `${fittedSize}px sans-serif`;
        ctx.fillText(
          lines[i],
          size,
          out.height - footerHeight + size + lineHeight * i,
        );
      }
      const blob = await new Promise<Blob | null>((resolve) =>
        out.toBlob(resolve, 'image/png'),
      );
      if (!blob) throw new Error('Export failed');
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = t('广西大学-校园视图.png');
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    retry: () => {
      // A rejected decoderPending is permanent for that loader instance.
      // All subsequent parses must share a fresh decoder after a failed preload.
      if (decoderFailed) {
        draco.dispose();
        decoderFailed = false;
        draco = createDecoder();
        loader.setDRACOLoader(draco);
      }
      if (!initialReady) void initialize();
      else {
        void loadBoundary();
        failed.clear();
        highTreesFailed = false;
        treesFailed = false;
        reconcileDetails();
        if (!treesRoot)
          void loadTrees().catch(() =>
            callbacks.onStatus('树木加载失败，请稍后重试', true),
          );
      }
    },
    setLocale,
    getSnapshot,
    restoreSnapshot,
    dispose: () => {
      disposed = true;
      lifecycle.abort();
      detailQueue.dispose();
      cancelAnimationFrame(loop);
      clearTimeout(convexPreparation);
      observer.disconnect();
      wheelHost.removeEventListener('wheel', onOverlayWheel);
      controls.dispose();
      draco.dispose();
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointercancel', onCancel);
      canvas.removeEventListener('pointerleave', onLeave);
      cancelAnimationFrame(hoverFrame);
      canvas.removeEventListener('keydown', onKey);
      canvas.removeEventListener('webglcontextlost', onLost);
      canvas.removeEventListener('webglcontextrestored', onRestored);
      convexCulling = null;
      disposeObject(scene);
      for (const p of proxies) {
        p.geometry.dispose();
        (p.material as THREE.Material).dispose();
      }
      contextStyle.dispose();
      effects?.dispose();
      sky.dispose();
      renderer.dispose();
      canvas.remove();
      labels.remove();
    },
  };
}
function clearGroup(group: THREE.Group) {
  for (const c of group.children.slice()) {
    group.remove(c);
    disposeObject(c);
  }
}
