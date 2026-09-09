import { navigableBuildings } from './navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { isTap } from './math';
import { DEFAULT_LAYERS } from './types';
import type {
  Building,
  Landmark,
  Quality,
  Preset,
  SceneController,
  Metrics,
  LayerKey,
} from './types';
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';
export const asset = (path: string) => `${BASE}/${path}`;
interface Asset {
  id?: string;
  url: string;
  bytes: number;
  sha256?: string;
  featureIds?: string[];
}
interface Manifest {
  base: Asset;
  trees: Asset;
  zones: Asset[];
  landmarks: Asset[];
}
interface Callbacks {
  onStatus: (message: string, error?: boolean) => void;
  onReady: () => void;
  onSelect: (id: string | null) => void;
  onInteract: () => void;
  onMetrics: (m: Metrics) => void;
}
export function createScene(
  host: HTMLElement,
  buildings: Building[],
  landmarks: Landmark[],
  callbacks: Callbacks,
): SceneController {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#d8e5e5');
  scene.fog = new THREE.Fog('#d8e5e5', 4800, 10500);
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: false,
  });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  const canvas = renderer.domElement;
  canvas.setAttribute(
    'aria-label',
    '广西大学三维校园，方向键平移，加减键缩放，Home返回全景',
  );
  canvas.tabIndex = 0;
  host.appendChild(canvas);
  const camera = new THREE.PerspectiveCamera(41, 1, 1, 12000);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.09;
  controls.minDistance = 45;
  controls.maxDistance = 6500;
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
  sun.shadow.bias = -0.00035;
  sun.shadow.normalBias = 0.9;
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
  const compact = () => window.innerWidth < 760;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const loaded = new Map<string, THREE.Group>();
  const loading = new Set<string>();
  const failed = new Map<string, Asset>();
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
  for (const b of navigableBuildings(buildings, landmarks)) {
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
    const b = buildings.find((b) => b.id === id || b.landmark === id);
    if (!l) return;
    selected = id;
    const c = (l ?? b)!;
    const dist =
      (l?.distance ??
        Math.max(
          100,
          Math.hypot(c.bounds[2] - c.bounds[0], c.bounds[3] - c.bounds[1]) *
            1.9,
        )) * (compact() ? 1.45 : 1);
    const target = new THREE.Vector3(
      c.center[0],
      c.elevation + c.height * 0.35,
      -c.center[1],
    );
    moveTo(
      target,
      target
        .clone()
        .add(
          new THREE.Vector3(
            ...(l?.cameraOffset ??
              ([-0.5, 0.66, 1] as [number, number, number])),
          ).multiplyScalar(dist),
        ),
    );
    clearGroup(highlight);
    const mark = new THREE.Mesh(
      new THREE.RingGeometry(dist * 0.2, dist * 0.205, 64),
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
    if (l && manifest) {
      const a = manifest.landmarks.find((a) => a.id === l.id);
      if (a) void loadDetail(a, 'landmark-' + l.id);
    }
    if (b && manifest && !modeSmooth) {
      const a = manifest.zones.find((a) => a.id === b.zone);
      if (a) void loadDetail(a, b.zone);
    }
  }
  function overview(animate = true) {
    const t = new THREE.Vector3(-310, 0, 15);
    const p = new THREE.Vector3(1350, 2050, 2350);
    if (compact()) {
      t.x = 0;
      p.set(1600, 2900, 3100);
    }
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
          if (m.name === 'glass') {
            m.emissive.set('#eec47b');
            m.emissiveIntensity = preset === 'night' ? 0.38 : 0;
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
      const isZone = manifest?.zones.some((z) => z.id === key);
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
  async function loadGLB(a: Asset) {
    const gltf = await loader.loadAsync(
      asset(a.url) + (a.sha256 ? `?v=${a.sha256}` : ''),
    );
    if (disposed) {
      disposeObject(gltf.scene);
      throw new Error('disposed');
    }
    loadedBytes += a.bytes;
    styleMeshes(gltf.scene);
    return gltf;
  }
  async function loadDetail(a: Asset, key: string) {
    if (loaded.has(key) || loading.has(key) || disposed) return;
    loading.add(key);
    try {
      const g = await loadGLB(a);
      dynamic.add(g.scene);
      loaded.set(key, g.scene);
      failed.delete(key);
      applyLayers();
      if (failed.size === 0 && initialReady) callbacks.onStatus('');
    } catch {
      if (!disposed) {
        failed.set(key, a);
        callbacks.onStatus('部分近景暂未加载，已保留校园基础画面。', true);
      }
    } finally {
      loading.delete(key);
    }
  }
  async function loadTrees() {
    if (!manifest || treesRoot) return;
    const [g, data, terrain] = await Promise.all([
      loadGLB(manifest.trees),
      fetch(asset('data/vegetation.json')).then((r) => r.json()) as Promise<
        number[][]
      >,
      fetch(asset('data/terrain.json')).then((r) => r.json()) as Promise<{
        bounds: number[];
        cols: number;
        rows: number;
        heights: number[];
      }>,
    ]);
    if (disposed) {
      disposeObject(g.scene);
      return;
    }
    treesRoot = new THREE.Group();
    treesRoot.name = 'vegetation';
    treesRoot.userData.layer = 'vegetation';
    scene.add(treesRoot);
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
          if (p.userData.template === typ || p.name === `Tree-template-${typ}`)
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
        });
        inst.instanceMatrix.needsUpdate = true;
        inst.computeBoundingSphere();
        inst.castShadow = true;
        inst.receiveShadow = true;
        inst.userData.fullCount = rows.length;
        treesRoot.add(inst);
      }
    }
    disposeObject(g.scene);
    // Materials and geometry are shared with the instanced meshes and disposed once during teardown.
    setQuality(quality);
    applyLayers();
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
    scene.fog = new THREE.Fog(sky, 4800, 10500);
    sun.color.set(color);
    sun.intensity = power;
    ambient.intensity = amb;
    sun.position.set(pos[0], pos[1], pos[2]);
    scene.traverse((o) => {
      if (o instanceof THREE.Mesh) {
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          if (m instanceof THREE.MeshStandardMaterial && m.name === 'glass') {
            m.emissive.set('#edbd71');
            m.emissiveIntensity = p === 'night' ? 0.48 : 0;
          }
      }
    });
    dirty = true;
  }
  function view(v: string) {
    if (v === 'overview') {
      selected = null;
      callbacks.onSelect(null);
      clearGroup(highlight);
      overview();
      return;
    }
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
    callbacks.onInteract();
    dirty = true;
  });
  controls.addEventListener('change', () => {
    dirty = true;
    pendingRequest = performance.now();
  });
  function resize() {
    const w = host.clientWidth,
      h = host.clientHeight;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
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
    };
  }
  function animate(time: number) {
    if (disposed) return;
    loop = requestAnimationFrame(animate);
    if (modeSmooth && time - lastFrame < 32) return;
    const moving = controls.update();
    if (tween) {
      const f = Math.min(1, (time - tween.start) / 1300);
      const e = 1 - (1 - f) ** 3;
      camera.position.lerpVectors(tween.from, tween.to, e);
      controls.target.lerpVectors(tween.fromTarget, tween.toTarget, e);
      if (f === 1) tween = null;
      dirty = true;
    }
    if (dirty || moving || tween) {
      shadowFrustum();
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
          (!compact() && x < 350) || y < 105 || y > rect.height - 95;
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
      !modeSmooth &&
      pendingRequest &&
      time - pendingRequest > 450
    ) {
      pendingRequest = 0;
      const distance = camera.position.distanceTo(controls.target);
      if (distance < 1050) {
        const zone =
          controls.target.z < -200
            ? 'north'
            : controls.target.x < 0
              ? 'west'
              : 'east';
        const a = manifest.zones.find((z) => z.id === zone);
        if (a) void loadDetail(a, zone);
      }
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
    clearSelection: () => {
      selected = null;
      clearGroup(highlight);
      dirty = true;
    },
    setLayer: (key, on) => {
      layers[key] = on;
      applyLayers();
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
        for (const [key, a] of failed) void loadDetail(a, key);
        if (!treesRoot)
          void loadTrees().catch(() =>
            callbacks.onStatus('植被加载失败，请稍后重试。', true),
          );
      }
    },
    getMetrics: metrics,
    dispose: () => {
      disposed = true;
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
