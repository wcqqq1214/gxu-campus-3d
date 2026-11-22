import * as THREE from 'three';
import { placeName, translate, type Locale } from './i18n';
import { landmarkLabelAnchor } from './labels';
import type { Landmark, Preset, ViewportFrame } from './types';

/**
 * Numbered landmark labels in a DOM layer over the canvas. Each frame they are
 * projected, prioritized by hover and selection, and hidden where they would
 * overlap, leave the visible frame or belong to a hidden layer.
 */
export function createSceneLabels({
  host,
  landmarks,
  invalidate,
  onHover,
  onChoose,
}: {
  host: HTMLElement;
  landmarks: Landmark[];
  /** Requests a redraw after label sizes or anchors change. */
  invalidate: () => void;
  onHover: (id: string | null) => void;
  onChoose: (id: string) => void;
}) {
  let locale: Locale = 'zh';
  const t = (source: string, values?: Record<string, string | number>) =>
    translate(locale, source, values);
  const layer = document.createElement('div');
  layer.className = 'scene-labels';
  host.appendChild(layer);
  const nodes = landmarks.map((l, i) => {
    const el = document.createElement('button');
    el.className = 'map-label';
    el.dataset.placeId = l.id;
    el.onpointerenter = () => onHover(l.id);
    el.onpointerleave = () => onHover(null);
    el.onfocus = () => onHover(l.id);
    el.onblur = () => onHover(null);
    const number = document.createElement('span');
    number.textContent = String(i + 1).padStart(2, '0');
    el.appendChild(number);
    const caption = document.createElement('span');
    caption.className = 'map-label-name';
    caption.textContent = placeName(l.name, locale);
    el.appendChild(caption);
    el.title = t('查看{name}', { name: placeName(l.name, locale) });
    el.onclick = () => onChoose(l.id);
    layer.appendChild(el);
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
  const order = [...nodes];
  let orderedHover: string | null | undefined;
  let orderedSelection: string | null | undefined;
  const projection = new THREE.Vector3();
  const occupied: number[][] = [];
  const viewport = { width: 0, height: 0 };
  function measure() {
    const layerDisplay = layer.style.display;
    layer.style.display = '';
    const displays = nodes.map(({ el }) => el.style.display);
    for (const { el } of nodes) el.style.display = '';
    for (const node of nodes) {
      node.width = node.el.offsetWidth;
      node.height = node.el.offsetHeight;
    }
    nodes.forEach(({ el }, i) => {
      el.style.display = displays[i];
    });
    layer.style.display = layerDisplay;
    invalidate();
  }
  return {
    setLocale(value: Locale) {
      locale = value;
      layer.lang = value === 'zh' ? 'zh-CN' : 'en';
      for (const { l, el, caption } of nodes) {
        const name = placeName(l.name, locale);
        caption.textContent = name;
        el.title = t('查看{name}', { name });
        el.setAttribute('aria-label', el.title);
      }
      measure();
    },
    resize(width: number, height: number) {
      viewport.width = width;
      viewport.height = height;
      measure();
    },
    /** Moves anchors onto loaded models; `model` returns the landmark's current model, if any. */
    updateAnchors(
      model: (key: string) => THREE.Object3D | undefined,
      id?: string,
    ) {
      for (const node of nodes) {
        if (id && node.l.id !== id) continue;
        node.point.copy(
          landmarkLabelAnchor(node.l, model('landmark-' + node.l.id)),
        );
        node.el.dataset.anchor = node.point
          .toArray()
          .map((v) => v.toFixed(2))
          .join(',');
      }
      invalidate();
    },
    anchor(id: string) {
      return nodes.find((node) => node.l.id === id)!.point;
    },
    setHovered(id: string | null) {
      for (const { l, el } of nodes)
        el.classList.toggle('linked-hover', l.id === id);
    },
    setVisible(visible: boolean) {
      layer.style.display = visible ? '' : 'none';
    },
    setLight(preset: Preset) {
      layer.dataset.light = preset;
    },
    layout(
      camera: THREE.Camera,
      {
        hovered,
        selected,
        frame,
        hidden: layerHidden,
      }: {
        hovered: string | null;
        selected: string | null;
        frame: ViewportFrame;
        hidden: (landmark: Landmark) => boolean;
      },
    ) {
      if (orderedHover !== hovered || orderedSelection !== selected) {
        orderedHover = hovered;
        orderedSelection = selected;
        // Reset tie order to the catalogue order, matching the previous sort.
        for (let i = 0; i < nodes.length; i++) order[i] = nodes[i];
        order.sort(
          (a, b) =>
            Number(b.l.id === hovered) * 2 +
            Number(b.l.id === selected) -
            (Number(a.l.id === hovered) * 2 + Number(a.l.id === selected)),
        );
      }
      occupied.length = 0;
      for (const { l, el, point, width, height, bounds } of order) {
        const p = projection.copy(point).project(camera);
        const dist = camera.position.distanceTo(point);
        const x = ((p.x + 1) * viewport.width) / 2,
          y = ((-p.y + 1) * viewport.height) / 2;
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
          layerHidden(l) ||
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
    },
    dispose() {
      layer.remove();
    },
  };
}
