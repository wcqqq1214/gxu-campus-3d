import { loadCampusBoundary } from './boundary-data';
import { translate, type Locale, type Message } from './i18n';
import { createNightStyle, createRoadLights } from './night';
import { createPalette } from './palette';
import { createSky, fogRange } from './sky';
import { LIGHTING } from './lighting';
import { searchableBuildings } from './navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { batchSportsSurfaces } from './sports-batching';
import { batchStaticRoadSurfaces } from './road-batching';
import { pruneGroundTriangles } from './ground-triangles';
import { createConvexCulling } from './convex-culling';
import type { CameraSnapshot } from './share';
import { fetchModel, fetchJson } from './streaming';
import type { StreamAsset as Asset } from './streaming';
import {
  asset,
  modelUrl,
  type BasePrefetch,
  type ModelManifest as Manifest,
} from './boot';
import {
  benchmarkOrbitEnabled,
  buildingPose,
  campusOverviewPoints,
  landmarkPose,
  orbitPose,
  overviewPose,
  viewPose,
  type MapView,
} from './camera';
import { DEFAULT_LAYERS } from './types';
import { QualityControl } from './quality';
import { FramePacer, FrameStats } from './frame-pacing';
import { BenchmarkOrbit } from './benchmark-orbit';
import { ShadowFrustum } from './shadow-frustum';
import { disposeObject } from './resources';
import { createBoundary } from './boundary';
import { createContextStyle } from './context-style';
import { createModelLoader, matchGround, refineBase } from './scene-base';
import { createDetailStreaming } from './scene-details';
import { createSceneEffects } from './scene-effects';
import { createSceneTrees } from './scene-trees';
import { downloadCanvas } from './scene-export';
import { createSceneLabels } from './scene-labels';
import {
  createScenePicking,
  footprintMesh,
  forwardOverlayWheel,
} from './scene-pointer';
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
  const releaseWheel = forwardOverlayWheel(host.parentElement ?? host, canvas);
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
  const loader = createModelLoader();
  let manifest: Manifest | null = null;
  let pendingPrefetch = prefetch;
  let baseRoot: THREE.Group | null = null;
  let disposed = false;
  let preset: Preset = 'day';
  let selected: string | null = null;
  let hovered: string | null = null;
  let initialReady = false;
  let readyMs = 0;
  let loadedBytes = 0;
  let loop = 0;
  let modeSmooth = false;
  const qualityControl = new QualityControl();
  let profile = qualityControl.profile();
  const effects = createSceneEffects({
    renderer,
    scene,
    camera,
    night: () => preset === 'night',
    onReady: () => {
      dirty = true;
    },
  });
  const syncEffects = () => effects.sync(profile.postprocessing, initialReady);
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
    if (!effects.render()) renderer.render(scene, camera);
  }
  let lastFrame = 0;
  let benchmarkRun: BenchmarkOrbit | null = null;
  const framePacer = new FramePacer();
  const stats = new FrameStats(performance.now());
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
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const loading = new Set<string>();
  const lifecycle = new AbortController();
  const progresses = new Map<
    string,
    { label: string; name?: string; fraction: number }
  >();
  let tween: {
    from: THREE.Vector3;
    to: THREE.Vector3;
    fromTarget: THREE.Vector3;
    toTarget: THREE.Vector3;
    start: number;
  } | null = null;
  const trees = createSceneTrees({
    scene,
    lifetime: lifecycle.signal,
    nightStyle,
    night: () => preset === 'night',
    load: (a, key, signal) => loadGLB(a, key, signal),
    onLoaded: () => {
      setQuality(qualityControl.quality);
      applyLayers();
    },
    onSettled: () => {
      pendingRequest = performance.now();
    },
  });
  const details = createDetailStreaming({
    scene,
    root: dynamic,
    layers,
    detailLayer,
    view: () => ({
      manifest,
      ready: initialReady,
      selected,
      smooth: modeSmooth,
      budgetMiB: profile.detailBudgetMiB,
      // A flight selects details around its destination, not the passing campus area.
      target: tween?.toTarget ?? controls.target,
      camera: tween?.to ?? camera.position,
    }),
    load: (a, key, signal) => loadGLB(a, key, signal),
    nearTrees: (distance) =>
      profile.nearTrees && distance < 1000
        ? trees.nearLoader(manifest)
        : undefined,
    onNearTreesFailed: () =>
      callbacks.onStatus('近处树木加载失败，可重试', true),
    onAttached: (key) => {
      if (key.startsWith('landmark-'))
        updateLabelAnchors(key.slice('landmark-'.length));
      if (key === 'landmark-' + selected && autoFramed && !orbiting)
        frameLandmark();
    },
    onReleased: (key) => {
      if (key.startsWith('landmark-'))
        updateLabelAnchors(key.slice('landmark-'.length));
    },
    onSettled: () => {
      pendingRequest = performance.now();
    },
    onFailed: updateLoadStatus,
    onReconciled: () => {
      applyLayers();
      updateLoadStatus();
    },
  });
  const reconcileDetails = (focusing = false) => details.reconcile(focusing);
  const labels = createSceneLabels({
    host,
    landmarks,
    invalidate: () => {
      dirty = true;
    },
    onHover: setHovered,
    onChoose: (id) => {
      callbacks.onInteract();
      focus(id);
    },
  });
  const labelHidden = (l: Landmark) =>
    l.placeKind === 'sports'
      ? !layers.sports
      : !layers[detailLayer('landmark-' + l.id)];
  const orbitOffset = new THREE.Vector3();
  const orbitAxis = new THREE.Vector3(0, 1, 0);
  function setLocale(value: Locale) {
    locale = value;
    canvas.setAttribute(
      'aria-label',
      t('广西大学三维校园，方向键平移，加减键缩放，Home返回全景'),
    );
    labels.setLocale(value);
  }
  function updateLabelAnchors(id?: string) {
    labels.updateAnchors(
      (key) => details.loaded.get(key) ?? baseRoot?.getObjectByName(key),
      id,
    );
  }
  function setHovered(id: string | null) {
    if (hovered === id) return;
    hovered = id;
    labels.setHovered(id);
    callbacks.onHover(id);
    dirty = true;
  }
  const namedBuildings = new Map(
    searchableBuildings(buildings, landmarks).map((b) => [b.id, b]),
  );
  const picking = createScenePicking({
    canvas,
    camera,
    buildings,
    landmarks,
    layers,
    moving: () => Boolean(tween),
    onHover: setHovered,
    onPick: (id) => focus(id),
  });
  const highlight = new THREE.Group();
  scene.add(highlight);
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
  function jumpTo(pose: { target: THREE.Vector3; position: THREE.Vector3 }) {
    tween = null;
    controls.target.copy(pose.target);
    camera.position.copy(pose.position);
    controls.update();
    dirty = true;
  }
  function selectionRing(radius: number, center: number[], elevation: number) {
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
    ring.position.set(center[0], elevation + 0.6, -center[1]);
    return ring;
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
    composeViewport();
    frameLandmark();
    clearGroup(highlight);
    // Sports grounds and bridges are already distinct; a ring would cut across them.
    if (l.placeKind !== 'sports' && l.placeKind !== 'bridge') {
      const [x0, y0, x1, y1] = l.bounds;
      const radius = Math.max(12, Math.hypot(x1 - x0, y1 - y0) * 0.54);
      highlight.add(selectionRing(radius, l.center, l.elevation));
    }
    callbacks.onSelect(id, origin);
    reconcileDetails(true);
  }
  function focusBuilding(
    id: string,
    origin: import('./types').SelectionOrigin = 'manual',
  ) {
    const b = namedBuildings.get(id)!;
    picking.clearHover();
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
    highlight.add(selectionRing(radius, b.center, b.elevation));
    callbacks.onSelect(id, origin);
    reconcileDetails(true);
  }
  function frameLandmark(animate = true) {
    const place = landmarks.find((p) => p.id === selected);
    const building = place ? undefined : namedBuildings.get(selected ?? '');
    const viewport = { width: host.clientWidth, height: host.clientHeight };
    const architecture = buildings.find(
      (b) => b.landmark === selected,
    )?.architecture;
    const pose = building
      ? buildingPose(building, selectedView, cameraFrame, viewport, camera.fov)
      : place
        ? landmarkPose(
            place,
            selectedView,
            {
              model: details.loaded.get('landmark-' + place.id),
              anchor: labels.anchor(place.id),
              architecture,
            },
            cameraFrame,
            viewport,
            camera.fov,
          )
        : null;
    if (!pose) return;
    if (animate) moveTo(pose.target, pose.position);
    else jumpTo(pose);
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
        lastFrame = startedAt;
        stats.restart(startedAt);
        return;
      }
      const place = landmarks.find((p) => p.id === selected)!;
      const fit = orbitPose(
        place,
        details.loaded.get('landmark-' + place.id),
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
    const pose = overviewPose(overviewPoints, cameraFrame, {
      width: host.clientWidth,
      height: host.clientHeight,
    });
    if (animate) moveTo(pose.target, pose.position);
    else jumpTo(pose);
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
        }
      }
    });
    applyModelLighting(root);
  }
  function applyModelLighting(root: THREE.Object3D) {
    root.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return;
      nightStyle.apply(o, preset === 'night');
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (!(m instanceof THREE.MeshStandardMaterial)) continue;
        if (m.name === 'timeSilver' || m.name === 'timeLight') {
          m.emissive.set('#83b6e2');
          m.emissiveIntensity =
            preset === 'night' ? (m.name === 'timeSilver' ? 0.16 : 1.8) : 0;
        }
      }
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
    for (const [key, root] of details.loaded) {
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
          !details.loaded.get(child.name)?.visible;
    syncRoadLights();
    boundaryRoot.visible = layers.boundary;
    trees.setVisible(layers.vegetation);
    labels.setVisible(layers.labels);
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
    else if (trees.failed(!modeSmooth))
      callbacks.onStatus('部分树木加载失败，可重试', true);
    else if (details.hasFailures())
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
        const styledPreset = preset;
        styleMeshes(gltf.scene, key !== 'base');
        await yieldLoading();
        batchSportsSurfaces(gltf.scene);
        await yieldLoading();
        batchStaticRoadSurfaces(gltf.scene);
        await yieldLoading();
        if (key === 'base') pruneGroundTriangles(gltf.scene);
        // Preset changes during a yield cannot reach this unattached root.
        // Synchronize after the last yield, before the caller publishes it.
        if (preset !== styledPreset) applyModelLighting(gltf.scene);
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
  async function loadBoundary() {
    if (boundaryLoading || boundaryReady || disposed) return;
    boundaryLoading = true;
    try {
      const data = await loadCampusBoundary(lifecycle.signal);
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
      matchGround(ground, baseRoot, {
        nightStyle,
        contextStyle,
        night: preset === 'night',
      });
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
          if (!(await refineBase(baseRoot, palette, () => disposed))) return;
          renderer.shadowMap.needsUpdate = true;
          dirty = true;
        };
        if ('requestIdleCallback' in window)
          window.requestIdleCallback(refine, { timeout: 1500 });
        else setTimeout(refine, 0);
      });
      void loadBoundary();
      reconcileDetails();
      void trees.load(manifest).catch(() => {
        if (!disposed) callbacks.onStatus('树木加载失败，可重试', true);
      });
    } catch {
      if (!disposed) callbacks.onStatus('校园加载失败，请检查网络后重试', true);
    } finally {
      loading.delete('base');
    }
  }
  function setQuality(q: Quality) {
    if (qualityControl.select(q)) effects.resetFailure();
    applyQuality();
  }
  function applyQuality() {
    profile = qualityControl.profile();
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
      details.cancel('trees-near');
    }
    trees.configure(profile.treeDensity, profile.nearTrees);
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
    effects.setNight(p === 'night');
    syncRoadLights();
    labels.setLight(p);
    applyModelLighting(scene);
    if (p === 'night') {
      // Pane attributes are created lazily; include them in the existing LOD budget.
      details.remeasure();
      reconcileDetails();
    }
    dirty = true;
  }
  function view(v: 'overview' | MapView) {
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
    const pose = viewPose(v, controls.target, camera.position, {
      min: controls.minDistance,
      max: controls.maxDistance,
    });
    moveTo(pose.target, pose.position);
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
    labels.resize(rect.width, rect.height);
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
    setQuality(qualityControl.quality);
    dirty = true;
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  resize();
  function shadowFrustum() {
    const distance = camera.position.distanceTo(controls.target);
    if (shadowVolume.fit(sun, controls.target, distance, preset))
      renderer.shadowMap.needsUpdate = true;
  }
  function metrics(): Metrics {
    const mem = (
      performance as Performance & { memory?: { usedJSHeapSize: number } }
    ).memory;
    return {
      readyMs,
      postprocessing: effects.status,
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
      fps: Math.round(stats.fps),
      triangles: renderer.info.render.triangles,
      drawCalls: renderer.info.render.calls,
      geometries: renderer.info.memory.geometries,
      textures: renderer.info.memory.textures,
      pixelRatio: renderer.getPixelRatio(),
      quality: ['精细', '均衡', '流畅'][profile.level],
      automaticQualityLevel: qualityControl.automaticLevel,
      shadows: profile.shadows,
      nearTrees: profile.nearTrees,
      detailBudgetMiB: profile.detailBudgetMiB,
      loadedBytes,
      loadedDetails: [...details.loaded.keys()],
      queuedDetails: details.queued,
      residentDetailBytes: manifest ? details.residentBytes(manifest) : 0,
      detailGeometryMiB:
        Math.round((details.geometryBytes() / 1048576) * 10) / 10,
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
      if (trees.updateLOD(camera.position, profile.nearTrees))
        renderer.shadowMap.needsUpdate = true;
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
      stats.rendered(time, Boolean(orbiting || moving || tween));
      labels.layout(camera, { hovered, selected, frame, hidden: labelHidden });
    }

    if (cameraChanged && time - cameraSampleAt > 200) {
      callbacks.onCamera(getSnapshot());
      cameraSampleAt = time;
      cameraChanged = false;
    }
    if (benchmarkRun ? benchmarkRun.sampleDue() : stats.due(time)) {
      const activeFrames = stats.sample(time);
      callbacks.onMetrics?.(metrics());
      if (
        qualityControl.sample(
          stats.fps,
          activeFrames,
          orbiting || Boolean(tween) || Boolean(moving),
        )
      )
        applyQuality();
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
      const segments = [t('广西大学 校园地图'), '© OpenStreetMap contributors'];
      if (layers.boundary && boundaryReady)
        segments.push(t('白色细线：校园大致边界'));
      await downloadCanvas(canvas, segments, t('广西大学-校园视图.png'));
    },
    retry: () => {
      // A rejected decoderPending is permanent for that loader instance.
      // All subsequent parses must share a fresh decoder after a failed preload.
      loader.recover();
      if (!initialReady) void initialize();
      else {
        void loadBoundary();
        details.retry();
        trees.resetFailures();
        reconcileDetails();
        if (!trees.loaded)
          void trees
            .load(manifest!)
            .catch(() => callbacks.onStatus('树木加载失败，请稍后重试', true));
      }
    },
    setLocale,
    getSnapshot,
    restoreSnapshot,
    dispose: () => {
      disposed = true;
      lifecycle.abort();
      details.dispose();
      cancelAnimationFrame(loop);
      clearTimeout(convexPreparation);
      observer.disconnect();
      releaseWheel();
      controls.dispose();
      loader.dispose();
      picking.dispose();
      canvas.removeEventListener('keydown', onKey);
      canvas.removeEventListener('webglcontextlost', onLost);
      canvas.removeEventListener('webglcontextrestored', onRestored);
      convexCulling = null;
      disposeObject(scene);
      contextStyle.dispose();
      effects.dispose();
      sky.dispose();
      renderer.dispose();
      canvas.remove();
      labels.dispose();
    },
  };
}
function clearGroup(group: THREE.Group) {
  for (const c of group.children.slice()) {
    group.remove(c);
    disposeObject(c);
  }
}
