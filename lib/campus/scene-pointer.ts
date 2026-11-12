import * as THREE from 'three';
import { isTap } from './math';
import { navigationFootprints } from './navigation';
import type { Building, Landmark, LayerKey } from './types';

/** Extruded footprint, used both as an invisible pick target and as a highlight outline. */
export function footprintMesh(b: {
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

/**
 * Mouse hover and tap selection on the canvas. Only curated places participate;
 * hidden layers are not pickable.
 */
export function createScenePicking({
  canvas,
  camera,
  buildings,
  landmarks,
  layers,
  moving,
  onHover,
  onPick,
}: {
  canvas: HTMLCanvasElement;
  camera: THREE.Camera;
  buildings: Building[];
  landmarks: Landmark[];
  layers: Record<LayerKey, boolean>;
  /** Hover picking pauses during camera flights. */
  moving: () => boolean;
  onHover: (id: string | null) => void;
  onPick: (id: string) => void;
}) {
  const proxies: THREE.Mesh[] = [];
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
  function pickTargets() {
    ensurePickProxies();
    return proxies.filter((p) => layers[p.userData.layer as LayerKey]);
  }
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
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
  function clearHover() {
    canvas.style.cursor = '';
    onHover(null);
  }
  function updatePointerHover() {
    hoverFrame = 0;
    if (!hoverPoint || moving() || downPointers > 0) return;
    const hit = pick(hoverPoint.x, hoverPoint.y);
    onHover(hit?.id ?? null);
    canvas.style.cursor = hit ? 'pointer' : '';
  }
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
      clearHover();
      return;
    }
    hoverPoint = { x: e.clientX, y: e.clientY };
    if (!hoverFrame) hoverFrame = requestAnimationFrame(updatePointerHover);
  }
  function onLeave() {
    hoverPoint = null;
    clearHover();
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
    clearHover();
    if (hit) onPick(hit.id);
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
  return {
    clearHover,
    dispose() {
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointercancel', onCancel);
      canvas.removeEventListener('pointerleave', onLeave);
      cancelAnimationFrame(hoverFrame);
      for (const p of proxies) {
        p.geometry.dispose();
        (p.material as THREE.Material).dispose();
      }
    },
  };
}

/**
 * Wheel gestures over map overlays zoom the map, except inside scrollable
 * menus and dialogs. Returns the listener's cleanup.
 */
export function forwardOverlayWheel(
  overlay: HTMLElement,
  canvas: HTMLCanvasElement,
) {
  function onWheel(event: WheelEvent) {
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
      if (el === overlay) break;
    }
    // Retain wheel units, cursor position and pinch modifiers for OrbitControls.
    if (!canvas.dispatchEvent(new WheelEvent('wheel', event)))
      event.preventDefault();
  }
  overlay.addEventListener('wheel', onWheel, { passive: false });
  return () => overlay.removeEventListener('wheel', onWheel);
}
