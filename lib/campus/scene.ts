import { navigationFootprints } from './navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { isTap } from './math';
import type { CameraSnapshot } from './share';
import { fetchModel, nearbyChunks, ResourceQueue } from './streaming';
import type { StreamAsset as Asset } from './streaming';
import { entranceBox, fitBox, landmarkBox, landmarkDirection } from './camera';
import { DEFAULT_LAYERS } from './types';
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
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';
export const asset = (path: string) => `${BASE}/${path}`;
interface Manifest {
  base: Asset;
  trees: Asset;
  treesNear?: Asset;
  zones: Asset[];
  landmarks: Asset[];
}
interface Callbacks {
  onStatus: (message: string, error?: boolean, progress?: number) => void;
  onReady: () => void;
  onSelect: (id: string | null) => void;
  onInteract: () => void;
  onMetrics: (m: Metrics) => void;
  onOrbit: (on: boolean) => void;
  onCamera: (snapshot: CameraSnapshot) => void;
}
export function createScene(
  host: HTMLElement,
  buildings: Building[],
  landmarks: Landmark[],
  callbacks: Callbacks,
): SceneController {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#d8e5e5');
  scene.fog = new THREE.Fog('#d8e5e5', 8500, 22000);
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: false,
  });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
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
  const ambient = new THREE.HemisphereLight('#d9edff', '#60704e', 1.35);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight('#fff3da', 2.6);
  sun.position.set(-700, 1400, 600);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.bias = -0.00008;
  sun.shadow.normalBias = 0.18;
  scene.add(sun);
  scene.add(sun.target);
  const fill = new THREE.DirectionalLight('#b4d9ea', 0.35);
  fill.position.set(1000, 600, -700);
  scene.add(fill);
  const layers = { ...DEFAULT_LAYERS };
  const dynamic = new THREE.Group();
  scene.add(dynamic);
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(30000, 30000),
    new THREE.MeshStandardMaterial({ color: '#b8c9a9', roughness: 1 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -22;
  scene.add(ground);
  const skyCanvas = document.createElement('canvas');
  skyCanvas.width = 256;
  skyCanvas.height = 128;
  const skyContext = skyCanvas.getContext('2d')!;
  const gradient = skyContext.createLinearGradient(0, 0, 0, 128);
  gradient.addColorStop(0, '#719cc4');
  gradient.addColorStop(0.5, '#e2ebdf');
  gradient.addColorStop(0.52, '#9ca989');
  gradient.addColorStop(1, '#52684e');
  skyContext.fillStyle = gradient;
  skyContext.fillRect(0, 0, 256, 128);
  skyContext.fillStyle = '#fff5d8';
  skyContext.beginPath();
  skyContext.arc(55, 30, 5, 0, Math.PI * 2);
  skyContext.fill();
  const skyTexture = new THREE.CanvasTexture(skyCanvas);
  skyTexture.mapping = THREE.EquirectangularReflectionMapping;
  skyTexture.colorSpace = THREE.SRGBColorSpace;
  scene.environment = skyTexture;
  scene.environmentIntensity = 0.45;
  const loader = new GLTFLoader();
  const draco = new DRACOLoader();
  draco.setDecoderPath(asset('draco/'));
  draco.setWorkerLimit(2);
  loader.setDRACOLoader(draco);
  let manifest: Manifest | null = null;
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
  let initialReady = false;
  let readyMs = 0;
  let loadedBytes = 0;
  let loop = 0;
  let modeSmooth = false;
  let lastFrame = 0;
  let frameCount = 0;
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
  const progresses = new Map<string, { label: string; fraction: number }>();
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
    const number = document.createElement('span');
    number.textContent = String(i + 1).padStart(2, '0');
    el.appendChild(number);
    el.appendChild(document.createTextNode(l.name));
    el.title = `查看${l.name}`;
    el.onclick = () => {
      callbacks.onInteract();
      focus(l.id);
    };
    labels.appendChild(el);
    return {
      l,
      el,
      point: new THREE.Vector3(
        l.center[0],
        l.elevation + l.height + 8,
        -l.center[1],
      ),
    };
  });
  const proxies: THREE.Mesh[] = [];
  for (const b of navigationFootprints(buildings, landmarks)) {
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
    mesh.userData = { id: b.landmark ?? b.id, inside: b.insideCampus };
    proxies.push(mesh);
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
    const rect = canvas.getBoundingClientRect();
    pointer.set(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      (-(e.clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(
      proxies.filter((p) =>
        p.userData.inside ? layers.buildings : layers.context,
      ),
      false,
    )[0];
    if (hit) focus(hit.object.userData.id);
  }
  function onCancel() {
    downPointers = 0;
    maxTravel = 999;
  }
  canvas.addEventListener('pointerdown', onDown);
  canvas.addEventListener('pointermove', onMove);
  canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointercancel', onCancel);
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
  function focus(id: string) {
    const l = landmarks.find((l) => l.id === id);
    if (!l) return;
    selected = id;
    restoredPose = null;
    selectedView = 'oblique';
    autoFramed = true;
    setOrbit(false);
    const c = l;
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
    if (l?.placeKind === 'sports') {
      mark.geometry.dispose();
      mark.material.dispose();
    } else highlight.add(mark);
    callbacks.onSelect(id);
    reconcileDetails(true);
  }
  function frameLandmark(animate = true) {
    const place = landmarks.find((p) => p.id === selected);
    if (!place) return;
    const detail = loaded.get('landmark-' + place.id);
    let box = detail
      ? new THREE.Box3().setFromObject(detail)
      : landmarkBox(place);
    if (selectedView === 'entrance' || selectedView === 'rear-entrance')
      box = entranceBox(
        place,
        box,
        selectedView === 'rear-entrance',
        buildings.find((b) => b.landmark === selected)?.architecture,
      );
    const fitted = fitBox(
      box,
      landmarkDirection(
        place,
        selectedView,
        buildings.find((b) => b.landmark === selected)?.architecture,
      ),
      frame,
      { width: host.clientWidth, height: host.clientHeight },
      camera.fov,
    );
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
    autoFramed = true;
    frameLandmark();
  }
  function setOrbit(on: boolean) {
    restoredPose = null;
    orbiting = on && Boolean(selected) && !reduced.matches;
    callbacks.onOrbit(orbiting);
    if (orbiting) {
      selectedView = 'oblique';
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
        frame,
        { width: host.clientWidth, height: host.clientHeight },
      );
      moveTo(fit.target, fit.position);
    }
  }
  function setViewport(value: ViewportFrame) {
    frame = value;
    frameReady = true;
    camera.setViewOffset(
      host.clientWidth,
      host.clientHeight,
      host.clientWidth / 2 - (frame.left + frame.width / 2),
      host.clientHeight / 2 - (frame.top + frame.height / 2),
      host.clientWidth,
      host.clientHeight,
    );
    if (restoredPose?.position) applyRestoredPose();
    else if (orbiting) setOrbit(true);
    else if (selected && autoFramed) frameLandmark();
    else if (!selected && autoFramed) overview();
    dirty = true;
  }
  function visibleTangent() {
    return (
      (Math.tan((camera.fov * Math.PI) / 360) *
        Math.min(frame.width, frame.height)) /
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
      focus(snapshot.selected);
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
    const { target: t, position: p } = fitBox(
      box,
      new THREE.Vector3(0.55, 1.1, 1),
      frame,
      { width: host.clientWidth, height: host.clientHeight },
    );
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
  function styleMeshes(root: THREE.Object3D) {
    root.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return;
      o.castShadow = true;
      o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (m instanceof THREE.MeshStandardMaterial) {
          if (m.name === 'sportWhite') {
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
          if (/glass$/i.test(m.name)) {
            m.emissive.set('#edbd71');
            m.emissiveIntensity = preset === 'night' ? 0.42 : 0;
          }
        }
      }
    });
  }
  function applyLayers() {
    if (baseRoot)
      for (const child of baseRoot.children) {
        const key = child.name;
        const layer = classify(child);
        child.visible =
          layer === 'buildings'
            ? layers.buildings && !loaded.get(key)?.visible
            : (layers[layer as LayerKey] ?? true);
        if (loaded.has(key) && !modeSmooth) child.visible = false;
      }
    for (const [key, root] of loaded) {
      const isZone = key.startsWith('chunk-');
      root.visible = layers.buildings && (!isZone || !modeSmooth);
      if (baseRoot) {
        const base = baseRoot.children.find((c) => c.name === key);
        if (base) base.visible = layers.buildings && !root.visible;
      }
    }
    if (treesRoot) treesRoot.visible = layers.vegetation;
    labels.style.display = layers.labels ? '' : 'none';
    highlight.visible = layers.buildings;
    dirty = true;
  }
  function updateLoadStatus() {
    if (disposed) return;
    const foreground =
      progresses.get('landmark-' + selected) ??
      progresses.get('base') ??
      progresses.values().next().value;
    if (foreground)
      callbacks.onStatus(
        `${foreground.label} · ${Math.round(foreground.fraction * 100)}%`,
        false,
        foreground.fraction,
      );
    else if (treesFailed || (highTreesFailed && !modeSmooth))
      callbacks.onStatus('部分植被暂未加载，已保留现有场景，可重试。', true);
    else if ([...failed.keys()].some((key) => wanted.has(key)))
      callbacks.onStatus('部分近景暂未加载，已保留基础校园；可重试。', true);
    else if (initialReady) callbacks.onStatus('');
  }
  async function loadGLB(a: Asset, key = 'base', signal = lifecycle.signal) {
    const label =
      key === 'base'
        ? '正在铺开校园'
        : key.startsWith('trees')
          ? '正在添上林荫'
          : key.startsWith('landmark-')
            ? `正在细化${landmarks.find((l) => 'landmark-' + l.id === key)?.name ?? '地标'}`
            : '正在补充周边细节';
    try {
      const buffer = await fetchModel(
        asset(a.url) + (a.sha256 ? `?v=${a.sha256}` : ''),
        a.bytes,
        signal,
        (fraction) => {
          progresses.set(key, { label, fraction });
          updateLoadStatus();
        },
      );
      signal.throwIfAborted();
      const gltf = await loader.parseAsync(buffer, asset('models/'));
      if (disposed || signal.aborted) {
        disposeObject(gltf.scene);
        throw new DOMException('Request cancelled', 'AbortError');
      }
      loadedBytes += a.bytes;
      styleMeshes(gltf.scene);
      return gltf;
    } finally {
      progresses.delete(key);
      updateLoadStatus();
    }
  }
  function releaseDetail(key: string) {
    const root = loaded.get(key);
    if (!root) return;
    dynamic.remove(root);
    disposeObject(root);
    loaded.delete(key);
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
    const cap = (compact() ? 32 : 64) * 1048576;
    const currentKey = 'landmark-' + selected;
    const foreground = manifest.landmarks.find((a) => a.id === selected);
    const wantedAssets: [string, Asset][] = [];
    let allocation = 0;
    if (layers.buildings && foreground) {
      wantedAssets.push([currentKey, foreground]);
      allocation += geometryCosts.get(currentKey) ?? foreground.bytes * 24;
    }
    // A fast response during a flight must use its destination, not the passing campus area.
    const destination = tween?.toTarget ?? controls.target;
    const destinationCamera = tween?.to ?? camera.position;
    const x = destination.x;
    const y = -destination.z;
    if (
      layers.buildings &&
      !modeSmooth &&
      (focusing || destinationCamera.distanceTo(destination) < 1050)
    ) {
      const candidates = nearbyChunks(manifest.zones, x, y);
      // Reserve in-flight nearby chunks before spending freed budget on another one.
      candidates.sort(
        (a, b) =>
          Number(Boolean(detailQueue.tasks.get(b.asset.id!)?.started)) -
          Number(Boolean(detailQueue.tasks.get(a.asset.id!)?.started)),
      );
      for (const { asset: a } of candidates) {
        const cost = geometryCosts.get(a.id!) ?? a.bytes * 32;
        if (
          wantedAssets.length >=
            (foreground ? (loaded.has(currentKey) ? 4 : 2) : 3) ||
          allocation + cost > cap
        )
          continue;
        allocation += cost;
        wantedAssets.push([a.id!, a]);
      }
    }
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
        layers.buildings &&
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
      !modeSmooth &&
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
        .catch(() => {
          if (!disposed)
            callbacks.onStatus(
              '近景植被暂未加载，已保留远景林荫，可重试。',
              true,
            );
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
      const elevation = (x: number, y: number) => {
        const [x0, y0, x1, y1] = terrain.bounds;
        const u = Math.max(
          0,
          Math.min(
            terrain.cols - 2,
            Math.floor(((x - x0) / (x1 - x0)) * (terrain.cols - 1)),
          ),
        );
        const v = Math.max(
          0,
          Math.min(
            terrain.rows - 2,
            Math.floor(((y - y0) / (y1 - y0)) * (terrain.rows - 1)),
          ),
        );
        return terrain.heights[v * terrain.cols + u];
      };
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
        for (const rows of sectors.values()) {
          const inst = new THREE.InstancedMesh(geometry, material, rows.length);
          const transform = new THREE.Object3D();
          rows.forEach(([x, y, h], i) => {
            transform.position.set(x, elevation(x, y), -y);
            transform.rotation.set(0, i * 2.399, 0);
            transform.scale.setScalar(h / 9);
            transform.updateMatrix();
            inst.setMatrixAt(i, transform.matrix);
            const tint =
              0.92 +
              (((Math.sin(x * 12.9898 + y * 78.233) * 43758.5453) % 1) + 1) *
                0.07;
            inst.setColorAt(i, new THREE.Color(tint * 0.98, tint, tint * 0.96));
          });
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
      if (!disposed) {
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
        !modeSmooth &&
        camera.position.distanceTo(o.userData.center) < 500;
      o.visible = o.userData.lod === 1 ? near : !near;
    }
  }
  async function initialize() {
    if (loading.has('base') || initialReady) return;
    loading.add('base');
    callbacks.onStatus('正在铺开校园…');
    try {
      const response = await fetch(asset('data/models.json'), {
        cache: 'no-cache',
      });
      if (!response.ok) throw new Error('manifest');
      manifest = await response.json();
      if (disposed) return;
      const gltf = await loadGLB(manifest!.base);
      baseRoot = gltf.scene;
      scene.add(baseRoot);
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
        const uv = ground.geometry.getAttribute('uv');
        for (let i = 0; i < uv.count; i++)
          uv.setXY(i, uv.getX(i) * 7500, uv.getY(i) * 7500);
        uv.needsUpdate = true;
      }
      initialReady = true;
      readyMs = Math.round(performance.now());
      applyLayers();
      callbacks.onReady();
      callbacks.onStatus('');
      reconcileDetails();
      void loadTrees().catch(() => {
        if (!disposed) callbacks.onStatus('植被暂未加载，可重试。', true);
      });
    } catch {
      if (!disposed)
        callbacks.onStatus('校园加载失败，请检查网络后重试。', true);
    } finally {
      loading.delete('base');
    }
  }
  function setQuality(q: Quality) {
    quality = q;
    modeSmooth =
      q === 'smooth' ||
      (q === 'auto' &&
        (compact() ||
          Boolean(
            (navigator as Navigator & { connection?: { saveData?: boolean } })
              .connection?.saveData,
          )));
    renderer.setPixelRatio(
      Math.min(window.devicePixelRatio, modeSmooth ? 1.25 : 1.75),
    );
    renderer.shadowMap.enabled = !modeSmooth;
    sun.castShadow = !modeSmooth;
    if (treesRoot)
      treesRoot.traverse((o) => {
        if (o instanceof THREE.InstancedMesh)
          o.count = modeSmooth
            ? Math.ceil(o.userData.fullCount * 0.55)
            : o.userData.fullCount;
      });
    applyLayers();
    reconcileDetails();
  }
  function setPreset(p: Preset) {
    preset = p;
    const settings = {
      morning: ['#d8e5e1', '#fff0cc', 2.6, 1.2, [-1300, 500, 700]],
      day: ['#d8e5e5', '#fff4df', 2.6, 1.35, [-700, 1400, 600]],
      evening: ['#e8d7cb', '#ffc386', 2.8, 0.9, [1300, 380, 700]],
      night: ['#182b3a', '#b3cdf4', 0.55, 0.26, [-700, 1000, -600]],
    } as const;
    const [sky, color, power, amb, pos] = settings[p];
    scene.background = new THREE.Color(sky);
    scene.fog = new THREE.Fog(sky, 8500, 22000);
    sun.color.set(color);
    sun.intensity = power;
    ambient.intensity = amb;
    sun.position.set(pos[0], pos[1], pos[2]);
    scene.traverse((o) => {
      if (o instanceof THREE.Mesh) {
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          if (
            m instanceof THREE.MeshStandardMaterial &&
            /glass$/i.test(m.name)
          ) {
            m.emissive.set('#edbd71');
            m.emissiveIntensity = p === 'night' ? 0.42 : 0;
          }
      }
    });
    dirty = true;
  }
  function view(v: string) {
    restoredPose = null;
    setOrbit(false);
    if (v === 'overview') {
      autoFramed = true;
      selected = null;
      callbacks.onSelect(null);
      clearGroup(highlight);
      overview();
      return;
    }
    autoFramed = false;
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
    const w = host.clientWidth,
      h = host.clientHeight;
    renderer.setSize(w, h);
    camera.setViewOffset(
      w,
      h,
      w / 2 - (frame.left + frame.width / 2),
      h / 2 - (frame.top + frame.height / 2),
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
    sun.shadow.normalBias = size < 350 ? 0.18 : 0.6;
    sun.target.position.copy(t);
    const directions = {
      morning: [-1300, 500, 700],
      day: [-700, 1400, 600],
      evening: [1300, 380, 700],
      night: [-700, 1000, -600],
    };
    const dir = directions[preset];
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
      heapMiB: mem ? Math.round(mem.usedJSHeapSize / 1048576) : null,
      fps: Math.round(fps),
      triangles: renderer.info.render.triangles,
      drawCalls: renderer.info.render.calls,
      geometries: renderer.info.memory.geometries,
      textures: renderer.info.memory.textures,
      pixelRatio: renderer.getPixelRatio(),
      quality: modeSmooth ? '流畅' : '精细',
      loadedBytes,
      loadedDetails: [...loaded.keys()],
      queuedDetails: detailQueue.tasks.size,
      residentDetailBytes: [...loaded.keys()].reduce(
        (n, key) =>
          n +
          (manifest?.landmarks.find((a) => 'landmark-' + a.id === key)?.bytes ??
            manifest?.zones.find((a) => a.id === key)?.bytes ??
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
    if (modeSmooth && time - lastFrame < 32) return;
    const moving = controls.update();
    if (orbiting && !tween) {
      if (reduced.matches) setOrbit(false);
      else {
        const offset = camera.position.clone().sub(controls.target);
        offset.applyAxisAngle(
          new THREE.Vector3(0, 1, 0),
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
      shadowFrustum();
      applyTreeLOD();
      renderer.render(scene, camera);
      dirty = false;
      lastFrame = time;
      frameCount++;
      if (lastRendered && time - lastRendered < 200) {
        activeFrameMs += time - lastRendered;
        activeFrames++;
      }
      lastRendered = time;
      const rect = host.getBoundingClientRect();
      const occupied: number[][] = [];
      for (const { l, el, point } of [...labelNodes].sort(
        (a, b) => Number(b.l.id === selected) - Number(a.l.id === selected),
      )) {
        const p = point.clone().project(camera);
        const dist = camera.position.distanceTo(point);
        const x = ((p.x + 1) * rect.width) / 2,
          y = ((-p.y + 1) * rect.height) / 2;
        const width = l.name.length * 12 + 38;
        const bounds = [x - width / 2, y - 28, x + width / 2, y];
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
          (l.placeKind === 'sports' ? !layers.sports : !layers.buildings) ||
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
    if (time - sampleStart > 1500) {
      if (activeFrames > 3) fps = (1000 * activeFrames) / activeFrameMs;
      callbacks.onMetrics(metrics());
      if (quality === 'auto' && frameCount > 10 && fps < 23) {
        renderer.setPixelRatio(Math.max(0.8, renderer.getPixelRatio() * 0.85));
        dirty = true;
      }
      frameCount = 0;
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
    callbacks.onStatus(
      '图形设备暂时中断。恢复后将重新绘制；也可刷新页面。',
      true,
    );
  };
  const onRestored = () => {
    callbacks.onStatus('');
    dirty = true;
  };
  canvas.addEventListener('webglcontextlost', onLost);
  canvas.addEventListener('webglcontextrestored', onRestored);
  return {
    focus,
    landmarkView,
    setOrbit,
    setViewport,
    clearSelection: () => {
      selected = null;
      autoFramed = false;
      setOrbit(false);
      clearGroup(highlight);
      dirty = true;
    },
    setLayer: (key, on) => {
      layers[key] = on;
      applyLayers();
      if (key === 'buildings') reconcileDetails();
    },
    setPreset,
    setQuality,
    view,
    exportImage: async () => {
      renderer.render(scene, camera);
      const out = document.createElement('canvas');
      out.width = canvas.width;
      out.height = canvas.height;
      const ctx = out.getContext('2d');
      if (!ctx) throw new Error('Canvas unavailable');
      ctx.drawImage(canvas, 0, 0);
      const size = Math.max(15, Math.round(out.width / 110));
      ctx.font = `${size}px sans-serif`;
      const label =
        '广西大学 · 云游校园  |  © OpenStreetMap contributors · ODbL';
      ctx.fillStyle = '#15382ddd';
      ctx.fillRect(0, out.height - size * 3, out.width, size * 3);
      ctx.fillStyle = 'white';
      ctx.fillText(label, size, out.height - size);
      const blob = await new Promise<Blob | null>((resolve) =>
        out.toBlob(resolve, 'image/png'),
      );
      if (!blob) throw new Error('Export failed');
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = '广西大学-校园视图.png';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    retry: () => {
      if (!initialReady) void initialize();
      else {
        failed.clear();
        highTreesFailed = false;
        treesFailed = false;
        reconcileDetails();
        if (!treesRoot)
          void loadTrees().catch(() =>
            callbacks.onStatus('植被加载失败，请稍后重试。', true),
          );
      }
    },
    getMetrics: metrics,
    getSnapshot,
    restoreSnapshot,
    dispose: () => {
      disposed = true;
      lifecycle.abort();
      detailQueue.dispose();
      skyTexture.dispose();
      cancelAnimationFrame(loop);
      observer.disconnect();
      controls.dispose();
      draco.dispose();
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointercancel', onCancel);
      canvas.removeEventListener('keydown', onKey);
      canvas.removeEventListener('webglcontextlost', onLost);
      canvas.removeEventListener('webglcontextrestored', onRestored);
      disposeObject(scene);
      for (const p of proxies) {
        p.geometry.dispose();
        (p.material as THREE.Material).dispose();
      }
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
function disposeObject(root: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>(),
    materials = new Set<THREE.Material>(),
    textures = new Set<THREE.Texture>();
  root.traverse((o) => {
    if (o instanceof THREE.Mesh) {
      geometries.add(o.geometry);
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        materials.add(m);
        for (const v of Object.values(m))
          if (v instanceof THREE.Texture) textures.add(v);
      }
    }
  });
  for (const g of geometries) g.dispose();
  for (const m of materials) m.dispose();
  for (const t of textures) t.dispose();
}
