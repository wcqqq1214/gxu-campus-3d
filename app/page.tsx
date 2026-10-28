'use client';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ComponentProps,
} from 'react';
import {
  CampusLocaleProvider,
  useCampusLocale,
} from '@/components/campus-locale';
import { createLoadStatusStore } from '@/lib/campus/load-status-store';
import { CampusLoadStatus } from '@/components/campus-load-status';
import { landmarkDescription } from '@/lib/campus/i18n/descriptions';
import { Menu } from '@base-ui/react/menu';
import { Tooltip } from '@base-ui/react/tooltip';
import Image from 'next/image';
import {
  ArrowUpRight,
  Building2,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsUp,
  ChevronsDown,
  Download,
  Expand,
  Grid2X2,
  Globe,
  House,
  Scan,
  Dumbbell,
  RectangleEllipsis,
  ScanEye,
  Ellipsis,
  CircleHelp,
  Layers3,
  MapPin,
  Minus,
  Moon,
  Navigation,
  Pause,
  Play,
  Plus,
  Search,
  Share2,
  Sun,
  Sunrise,
  Sunset,
  Trees,
  Waves,
  X,
} from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import type {
  Building,
  Landmark,
  Overview,
  SceneController,
  Quality,
  Preset,
  LayerKey,
  Metrics,
  LandmarkView,
  Category,
} from '@/lib/campus/types';
import { DEFAULT_LAYERS, CATEGORY_NAMES } from '@/lib/campus/types';
import { nextTourIndex } from '@/lib/campus/math';
import {
  buildingLocationLabel,
  searchBuildings,
  searchableBuildings,
  searchLandmarks,
} from '@/lib/campus/navigation';
import { decodeShare, encodeShare, cameraBearing } from '@/lib/campus/share';
import { fetchJson } from '@/lib/campus/streaming';
import { asset, prefetchBase } from '@/lib/campus/boot';
import { createCameraStore, type CameraStore } from '@/lib/campus/camera-store';
import { CampusMinimap } from '@/components/campus-minimap';
import { CampusViewControls } from '@/components/campus-view-controls';
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';
const TOUR_STOP_MS = 8500;
const LAYER_ITEMS: [LayerKey, string, typeof Building2][] = [
  ['labels', '地点名称', RectangleEllipsis],
  ['boundary', '校园边界', Scan],
  ['buildings', '校园建筑', Building2],
  ['vegetation', '树木', Trees],
  ['roads', '道路与桥梁', Navigation],
  ['water', '水面', Waves],
  ['sports', '运动场地', Dumbbell],
  ['context', '周边建筑', Layers3],
];
const PRESETS: [Preset, string, typeof Sun][] = [
  ['morning', '清晨', Sunrise],
  ['day', '白天', Sun],
  ['evening', '黄昏', Sunset],
  ['night', '夜晚', Moon],
];
const BUILDING_RESULT_LIMIT = 40;
const QUALITY_OPTIONS: [Quality, string][] = [
  ['auto', '自动'],
  ['fine', '精细'],
  ['smooth', '流畅'],
];
export default function Home() {
  return (
    <CampusLocaleProvider>
      <CampusMap />
    </CampusLocaleProvider>
  );
}
function CampusMap() {
  const { locale, setLocale, t, name } = useCampusLocale();
  const localeRef = useRef(locale);
  const dock = useRef<HTMLElement>(null);
  const panelToggle = useRef<HTMLButtonElement>(null);
  const detailBack = useRef<HTMLButtonElement>(null);
  const tourEntry = useRef<HTMLButtonElement>(null);
  const tourProgress = useRef<HTMLSpanElement>(null);
  const menuScroll = useRef(0);
  const returnPlace = useRef<string | null>(null);
  const pendingFocus = useRef<'detail' | 'menu' | null>(null);
  const host = useRef<HTMLDivElement>(null),
    controller = useRef<SceneController | null>(null);
  const [buildings, setBuildings] = useState<Building[]>([]),
    [landmarks, setLandmarks] = useState<Landmark[]>([]),
    [overview, setOverview] = useState<Overview | null>(null);
  const [loadStatusStore] = useState(createLoadStatusStore);
  const error = useSyncExternalStore(
    loadStatusStore.subscribe,
    loadStatusStore.getError,
    () => false,
  );
  const [ready, setReady] = useState(false),
    [selected, setSelected] = useState<string | null>(null),
    [query, setQuery] = useState(''),
    [tab, setTab] = useState('explore');
  const [layers, setLayers] = useState(DEFAULT_LAYERS),
    [preset, setPreset] = useState<Preset>('day'),
    [quality, setQuality] = useState<Quality>('auto'),
    [tour, setTour] = useState(false),
    [tourStarted, setTourStarted] = useState(false),
    [tourIndex, setTourIndex] = useState(0),
    [collapsed, setCollapsed] = useState(false),
    [toast, setToast] = useState(''),
    [retrySeed, setRetrySeed] = useState(0),
    [metrics, setMetrics] = useState<Metrics | null>(null);
  const settings = useRef({
    layers: DEFAULT_LAYERS,
    preset: 'day' as Preset,
    quality: 'auto' as Quality,
  });
  const presetEdited = useRef(false);
  useEffect(() => {
    // Portals (dialogs, menus, tooltips) render outside the app, so the theme sits on <html>.
    const night = preset === 'night';
    document.documentElement.dataset.theme = night ? 'night' : 'day';
    // Radix UI Colors switch to their dark scales under .dark-theme.
    document.documentElement.classList.toggle('dark-theme', night);
  }, [preset]);
  useEffect(() => {
    localeRef.current = locale;
    controller.current?.setLocale(locale);
  }, [locale]);
  const [framingRequest, setFramingRequest] = useState(0);
  const framedRequest = useRef(0);
  const [panelExpanded, setPanelExpanded] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const [debug, setDebug] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [cameraStore] = useState(createCameraStore);
  const [shareLink, setShareLink] = useState('');
  const [panelMode, setPanelMode] = useState<'menu' | 'detail'>('menu');
  const [landmarkView, setLandmarkView] = useState<LandmarkView | null>(
    'oblique',
  );
  const [orbit, setOrbit] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const notify = useCallback((message: string) => setToast(message), []);
  const pauseMotion = useCallback(() => {
    setTour(false);
    controller.current?.setOrbit(false);
  }, []);
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.hidden) pauseMotion();
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () =>
      document.removeEventListener('visibilitychange', onVisibilityChange);
  }, [pauseMotion]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(''), 3500);
    return () => clearTimeout(t);
  }, [toast]);
  useEffect(() => {
    const lifetime = new AbortController();
    void fetchJson<Overview>(asset('data/overview.json'), lifetime.signal)
      .then((data) => {
        if (!lifetime.signal.aborted) setOverview(data);
      })
      // The data date is supplementary; the map works without it.
      .catch(() => {});
    return () => lifetime.abort();
  }, []);
  useEffect(() => {
    let active = true;
    const lifetime = new AbortController();
    const debugMetrics = new URLSearchParams(location.search).has('debug');
    queueMicrotask(() => {
      if (active) setDebug(debugMetrics);
    });
    let cleanup: (() => void) | undefined;
    // The base model is the longest download; start it beside the scene code
    // and building data instead of after them.
    const boot = prefetchBase(lifetime.signal);
    void Promise.all([
      fetchJson<Building[]>(asset('data/buildings.json'), lifetime.signal),
      fetchJson<Landmark[]>(asset('data/landmarks.json'), lifetime.signal),
      import('@/lib/campus/scene'),
    ])
      .then(([bs, ls, { createScene }]) => {
        if (!active || !host.current) return;
        setBuildings(bs);
        setLandmarks(ls);
        try {
          if (
            process.env.NODE_ENV === 'development' &&
            new URLSearchParams(location.search).has('test-webgl-unavailable')
          )
            throw new Error('WebGL test');
          const c = createScene(
            host.current,
            bs,
            ls,
            {
              onStatus: (message, failed = false, progress) => {
                if (active) {
                  loadStatusStore.set(message, failed, progress);
                }
              },
              onReady: () => {
                if (active) setReady(true);
              },
              onSelect: (id, origin = 'manual') => {
                if (active) {
                  setSelected(id);
                  setFramingRequest((value) => value + 1);
                  setLandmarkView('oblique');
                  const stop = ls.findIndex((place) => place.id === id);
                  // Ordinary buildings are not tour stops; the tour keeps its place.
                  if (stop >= 0) setTourIndex(stop);
                  if (origin !== 'tour') {
                    setPanelMode(id ? 'detail' : 'menu');
                    setCollapsed(false);
                    setPanelExpanded(false);
                    dock.current
                      ?.querySelector<HTMLInputElement>('input[type="search"]')
                      ?.blur();
                    if (origin === 'manual') {
                      setTour(false);
                      pendingFocus.current = id ? 'detail' : 'menu';
                    }
                  }
                }
              },
              onHover: (id) => {
                if (active) setHovered(id);
              },
              onInteract: () => {
                if (active) {
                  setTour(false);
                  setLandmarkView(null);
                }
              },
              onCamera: (snapshot) => {
                if (active) cameraStore.set(snapshot);
              },
              onOrbit: (on) => {
                if (active) {
                  setOrbit(on);
                  if (on) setLandmarkView('oblique');
                }
              },
              // Metrics are only displayed in debug mode; elsewhere each
              // report would re-render the whole page every 1.5 s.
              onMetrics: debugMetrics
                ? (m) => {
                    if (active) setMetrics(m);
                  }
                : undefined,
            },
            boot,
          );
          c.setLocale(localeRef.current);
          controller.current = c;
          cleanup = () => c.dispose();
          c.setQuality(settings.current.quality);
          c.setPreset(settings.current.preset);
          for (const key of Object.keys(settings.current.layers) as LayerKey[])
            c.setLayer(key, settings.current.layers[key]);
          const shared = decodeShare(location.hash, [
            ...ls.map((l) => l.id),
            ...searchableBuildings(bs, ls).map((b) => b.id),
          ]);
          if (shared) {
            if (presetEdited.current) shared.preset = settings.current.preset;
            c.restoreSnapshot(shared);
            if (shared.preset) {
              settings.current.preset = shared.preset;
              setPreset(shared.preset);
            }
            setLandmarkView(
              shared.view ?? (shared.position ? null : 'oblique'),
            );
          }
          cleanup = () => c.dispose();
        } catch {
          // Without WebGL nothing will consume the prefetched model.
          lifetime.abort();
          loadStatusStore.set(
            '无法显示三维画面，请开启硬件加速或使用支持 WebGL 2 的浏览器',
            true,
          );
        }
      })
      .catch(() => {
        if (active) {
          loadStatusStore.set('校园数据加载失败，请检查网络后重试', true);
        }
      });
    return () => {
      active = false;
      lifetime.abort();
      cleanup?.();
      controller.current = null;
    };
    // The store is created once; listing it only satisfies the hook rule.
  }, [retrySeed, cameraStore, loadStatusStore]);
  useEffect(() => {
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReducedMotion(preference.matches);
    update();
    preference.addEventListener('change', update);
    return () => preference.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    const viewport = window.visualViewport;
    const update = () => {
      const root = host.current?.parentElement;
      const height = viewport?.height ?? window.innerHeight;
      root?.style.setProperty('--app-height', `${height}px`);
      root?.style.setProperty(
        '--viewport-top',
        `${viewport?.offsetTop ?? 0}px`,
      );
      setKeyboardOpen(
        window.innerWidth < 760 && height < window.innerHeight * 0.75,
      );
    };
    update();
    viewport?.addEventListener('resize', update);
    viewport?.addEventListener('scroll', update);
    window.addEventListener('resize', update);
    return () => {
      viewport?.removeEventListener('resize', update);
      viewport?.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, []);
  useEffect(() => {
    if (!ready || !host.current || !dock.current) return;
    const root = host.current.parentElement!;
    const header = root.querySelector<HTMLElement>('.masthead')!;
    const tools = root.querySelector<HTMLElement>('.map-tools')!;
    let pending = 0;
    let previous = '';
    const measure = () => {
      cancelAnimationFrame(pending);
      pending = requestAnimationFrame(() => {
        const panel = dock.current!.getBoundingClientRect();
        const menu = tools.getBoundingClientRect();
        const top = header.getBoundingClientRect().bottom + 18;
        const mobile = window.innerWidth < 760;
        const left = mobile || collapsed ? 18 : panel.right + 24;
        const right = menu.left - 18;
        const bottom = mobile ? panel.top - 34 : window.innerHeight - 42;
        const frame = {
          left,
          top,
          width: Math.max(120, right - left),
          height: Math.max(100, bottom - top),
        };
        root.style.setProperty('--dock-height', `${panel.height}px`);
        root.style.setProperty('--scene-left', `${left}px`);
        const key = JSON.stringify(frame);
        const reframe = framedRequest.current !== framingRequest;
        if (key !== previous || reframe) {
          previous = key;
          framedRequest.current = framingRequest;
          controller.current?.setViewport(frame, reframe);
        }
      });
    };
    const observer = new ResizeObserver(measure);
    [dock.current, header, tools, host.current].forEach((el) =>
      observer.observe(el),
    );
    measure();
    return () => {
      observer.disconnect();
      cancelAnimationFrame(pending);
    };
  }, [ready, collapsed, framingRequest]);
  useEffect(() => {
    if (!pendingFocus.current || collapsed) return;
    const destination = pendingFocus.current;
    pendingFocus.current = null;
    const body = dock.current?.querySelector<HTMLElement>('.dock-body');
    if (destination === 'detail') {
      if (body) body.scrollTop = 0;
      detailBack.current?.focus({ preventScroll: true });
    } else {
      const row = Array.from(
        dock.current?.querySelectorAll<HTMLButtonElement>('[data-place-id]') ??
          [],
      ).find((item) => item.dataset.placeId === returnPlace.current);
      (
        row ??
        dock.current?.querySelector<HTMLInputElement>('input[type="search"]')
      )?.focus({ preventScroll: true });
      if (body) body.scrollTop = menuScroll.current;
    }
  }, [selected, panelMode, collapsed, panelExpanded]);
  function togglePanel() {
    setCollapsed((value) => !value);
    requestAnimationFrame(() =>
      panelToggle.current?.focus({ preventScroll: true }),
    );
  }
  function returnToMenu() {
    pauseMotion();
    returnPlace.current = selected;
    pendingFocus.current = 'menu';
    setTab('explore');
    setPanelMode('menu');
    setPanelExpanded(true);
    setCollapsed(false);
  }
  function changeLandmarkView(value: LandmarkView) {
    setTour(false);
    setLandmarkView(value);
    controller.current?.landmarkView(value);
  }
  const choose = useCallback((id: string) => {
    setTour(false);
    controller.current?.focus(id);
  }, []);
  useEffect(() => {
    if (!tour || !landmarks.length) return;
    controller.current?.focus(landmarks[tourIndex].id, 'tour');
    // Both the station change and its indicator use this deadline. Updating the
    // DOM directly keeps progress running while the panel is display:none,
    // without re-rendering the entire map on every animation frame.
    const deadline = performance.now() + TOUR_STOP_MS;
    let frame = 0;
    const updateProgress = () => {
      const progress = Math.min(
        1,
        Math.max(0, 1 - (deadline - performance.now()) / TOUR_STOP_MS),
      );
      if (tourProgress.current)
        tourProgress.current.style.transform = `scaleX(${progress})`;
      if (progress < 1) frame = requestAnimationFrame(updateProgress);
    };
    updateProgress();
    const timer = setTimeout(
      () => setTourIndex((i) => nextTourIndex(i, landmarks.length)),
      Math.max(0, deadline - performance.now()),
    );
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(frame);
    };
  }, [tour, tourIndex, landmarks]);
  const currentLandmark = landmarks.find((l) => l.id === selected);
  const currentBuilding = selected
    ? buildings.find((b) => b.id === selected || b.landmark === selected)
    : undefined;
  const current = currentLandmark ?? currentBuilding;
  const places = useMemo(
    () => searchLandmarks(landmarks, query),
    [landmarks, query],
  );
  const buildingMatches = useMemo(
    () => searchBuildings(buildings, landmarks, query, locale),
    [buildings, landmarks, query, locale],
  );
  const resultCount = places.length + buildingMatches.length;
  const groups = query.trim()
    ? places.length
      ? [{ key: 'search', name: t('精选地点'), places }]
      : []
    : (
        [
          'academic',
          'culture',
          'landmark',
          'infrastructure',
          'living',
          'service',
        ] as Category[]
      )
        .map((key) => ({
          key,
          name: t(CATEGORY_NAMES[key]),
          places: places.filter((p) => p.category === key),
        }))
        .filter((group) => group.places.length);
  function hoverPlace(id: string | null) {
    controller.current?.setHovered(id);
  }
  function resetSearch() {
    setQuery('');
    dock.current
      ?.querySelector<HTMLInputElement>('input[type="search"]')
      ?.focus();
  }
  function openShare() {
    pauseMotion();
    setShareOpen(true);
  }
  function toggleLayer(k: LayerKey, on: boolean) {
    settings.current.layers = { ...settings.current.layers, [k]: on };
    setLayers(settings.current.layers);
    controller.current?.setLayer(k, on);
  }
  function changePreset(p: Preset) {
    presetEdited.current = true;
    settings.current.preset = p;
    setPreset(p);
    controller.current?.setPreset(p);
  }
  function changeQuality(q: Quality) {
    settings.current.quality = q;
    setQuality(q);
    controller.current?.setQuality(q);
  }
  function view(
    v: 'overview' | 'top' | 'tilt' | 'north' | 'zoomIn' | 'zoomOut',
  ) {
    setTour(false);
    setLandmarkView(null);
    controller.current?.view(v);
    if (v === 'overview') {
      setSelected(null);
      setCollapsed(false);
    }
  }
  async function shareView() {
    pauseMotion();
    const snapshot = controller.current?.getSnapshot();
    if (!snapshot) return;
    const url = new URL(location.pathname, location.origin);
    url.searchParams.set('lang', locale);
    url.hash = encodeShare(snapshot);
    try {
      await navigator.clipboard.writeText(url.href);
      notify('链接已复制');
    } catch {
      setShareLink(url.href);
    }
  }
  function retry() {
    if (controller.current) controller.current.retry();
    else {
      loadStatusStore.set('正在重新加载…');
      setRetrySeed((s) => s + 1);
    }
  }
  function jump(delta: number) {
    setTourStarted(true);
    setTourIndex((i) => (i + delta + landmarks.length) % landmarks.length);
    if (!tour && landmarks.length)
      controller.current?.focus(
        landmarks[(tourIndex + delta + landmarks.length) % landmarks.length].id,
        'tour',
      );
  }
  function toggleFullscreen() {
    if (!document.fullscreenEnabled) {
      notify('当前浏览器不支持全屏');
      return;
    }
    const action = document.fullscreenElement
      ? document.exitFullscreen()
      : document.documentElement.requestFullscreen();
    void action.catch(() => notify('当前浏览器不支持全屏'));
  }
  async function exportView() {
    try {
      await controller.current?.exportImage();
      notify('图片已下载');
    } catch {
      notify('下载失败，请重试');
    }
  }
  return (
    <main className={`campus-app ${keyboardOpen ? 'keyboard-open' : ''}`}>
      <div className="scene-host" ref={host} />
      <header className="masthead">
        <div className="masthead-brand">
          <button
            className="brand-mark"
            onClick={() => view('overview')}
            title={t('回到全景')}
            aria-label={t('回到全景')}
          >
            <Image
              src={`${BASE}/favicon.svg`}
              alt=""
              width={44}
              height={44}
              unoptimized
            />
          </button>
          <h1>
            {t('广西大学')}
            <span>{t('校园地图')}</span>
          </h1>
        </div>
        <div className="masthead-actions">
          <Menu.Root>
            <Menu.Trigger
              className="header-action"
              aria-label="语言 / Language"
            >
              <Globe size={18} aria-hidden="true" />
            </Menu.Trigger>
            <Menu.Portal>
              <Menu.Positioner
                className="language-menu-positioner"
                side="bottom"
                align="end"
                sideOffset={8}
              >
                <Menu.Popup
                  className="language-menu"
                  aria-label="语言 / Language"
                >
                  <Menu.RadioGroup value={locale} onValueChange={setLocale}>
                    <Menu.RadioItem
                      className="language-menu-item"
                      value="zh"
                      closeOnClick
                    >
                      <span lang="zh-CN">中文</span>
                      <Menu.RadioItemIndicator>
                        <Check size={16} aria-hidden="true" />
                      </Menu.RadioItemIndicator>
                    </Menu.RadioItem>
                    <Menu.RadioItem
                      className="language-menu-item"
                      value="en"
                      closeOnClick
                    >
                      <span lang="en">English</span>
                      <Menu.RadioItemIndicator>
                        <Check size={16} aria-hidden="true" />
                      </Menu.RadioItemIndicator>
                    </Menu.RadioItem>
                  </Menu.RadioGroup>
                </Menu.Popup>
              </Menu.Positioner>
            </Menu.Portal>
          </Menu.Root>
          <a
            className="header-action"
            href="https://github.com/wcqqq1214/gxu-campus-3d"
            target="_blank"
            rel="noreferrer"
            aria-label={t('查看 GitHub 仓库')}
          >
            <svg
              width={18}
              height={18}
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M12 .297C5.37.297 0 5.67 0 12.297c0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.043-1.61-4.043-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.09-.745.083-.729.083-.729 1.205.084 1.838 1.237 1.838 1.237 1.07 1.835 2.809 1.305 3.495.998.108-.776.418-1.305.762-1.605-2.665-.3-5.466-1.334-5.466-5.93 0-1.31.467-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23a11.5 11.5 0 0 1 3-.404c1.02.005 2.045.138 3 .404 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
          </a>
        </div>
      </header>
      <aside
        ref={dock}
        className={`panel-dock ${collapsed ? 'collapsed' : ''} ${panelExpanded ? 'expanded' : ''} ${panelMode === 'detail' ? 'detail-mode' : ''}`}
        aria-label={t('校园浏览面板')}
      >
        {(collapsed || panelMode === 'detail') && (
          <div className="dock-heading">
            {panelMode === 'detail' && current && (
              <button
                ref={detailBack}
                className="dock-back"
                title={t('返回地点列表')}
                aria-label={t('返回地点列表')}
                onClick={returnToMenu}
              >
                <ChevronLeft size={16} />
                <span>{t('返回列表')}</span>
              </button>
            )}
            <button
              ref={panelToggle}
              className="dock-toggle"
              aria-expanded={!collapsed}
              aria-controls="campus-panel-body"
              aria-label={collapsed ? t('展开面板') : t('收起面板')}
              onClick={togglePanel}
            >
              <span>
                {panelMode === 'detail' && current
                  ? collapsed
                    ? name(current.name)
                    : ''
                  : t('校园浏览')}
              </span>
              <ChevronDown size={16} />
            </button>
          </div>
        )}
        <div
          id="campus-panel-body"
          className="dock-body"
          hidden={collapsed}
          onScroll={(event) => {
            if (panelMode === 'menu' && tab === 'explore')
              menuScroll.current = event.currentTarget.scrollTop;
          }}
        >
          {panelMode === 'detail' && current ? (
            <section className="place-detail" aria-label={t('地点详情')}>
              <div className="detail-heading">
                <div className="eyebrow">
                  {t(CATEGORY_NAMES[current.category])}
                </div>
                <h2>{name(current.name)}</h2>
              </div>
              {currentLandmark ? (
                <p>{landmarkDescription(currentLandmark, locale)}</p>
              ) : (
                <>
                  <p className="building-location">
                    {buildingLocationLabel(currentBuilding!, landmarks, locale)}
                  </p>
                  <p className="building-facts">
                    {currentBuilding!.levels >= 1
                      ? t('约 {levels} 层，高约 {height} 米', {
                          levels: Math.round(currentBuilding!.levels),
                          height: Math.round(currentBuilding!.height),
                        })
                      : t('高约 {height} 米', {
                          height: Math.round(currentBuilding!.height),
                        })}
                  </p>
                </>
              )}
              <CampusViewControls
                landmark={currentLandmark}
                view={landmarkView}
                orbit={orbit}
                reducedMotion={reducedMotion}
                onViewChange={changeLandmarkView}
                onOrbitChange={() => {
                  setTour(false);
                  controller.current?.setOrbit(!orbit);
                }}
              />
              <div className="detail-actions">
                <button onClick={openShare}>
                  <Share2 size={14} />
                  {t('分享视角')}
                </button>
              </div>
            </section>
          ) : (
            <div className="explorer">
              <Tabs
                value={tab}
                onValueChange={(v) => {
                  setTab(String(v));
                  if (dock.current) {
                    const body = dock.current.querySelector('.dock-body');
                    if (body) body.scrollTop = 0;
                  }
                }}
                className="main-tabs"
              >
                <div className="explorer-toolbar">
                  <TabsList className="panel-tabs">
                    <TabsTrigger value="explore">
                      <MapPin size={17} />
                      {t('地点')}
                    </TabsTrigger>
                    <TabsTrigger value="layers">
                      <Layers3 size={17} />
                      {t('图层')}
                    </TabsTrigger>
                    <TabsTrigger value="environment">
                      <Sun size={17} />
                      {t('光影')}
                    </TabsTrigger>
                  </TabsList>
                  <button
                    className="dock-expand"
                    aria-expanded={panelExpanded}
                    aria-controls="campus-panel-body"
                    aria-label={panelExpanded ? t('收起列表') : t('展开列表')}
                    title={panelExpanded ? t('收起列表') : t('展开列表')}
                    onClick={() => setPanelExpanded((value) => !value)}
                  >
                    {panelExpanded ? (
                      <ChevronsDown size={16} />
                    ) : (
                      <ChevronsUp size={16} />
                    )}
                  </button>
                  <button
                    ref={collapsed ? undefined : panelToggle}
                    className="menu-collapse"
                    aria-expanded={!collapsed}
                    aria-controls="campus-panel-body"
                    aria-label={t('收起面板')}
                    title={t('收起面板')}
                    onClick={togglePanel}
                  >
                    <ChevronDown size={16} />
                  </button>
                </div>
                <TabsContent value="explore" className="explore-content">
                  <div className="search-wrap">
                    <Search size={16} />
                    <Input
                      type="search"
                      onFocus={() => {
                        pauseMotion();
                        setPanelExpanded(true);
                      }}
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder={t('搜索地点或建筑')}
                      aria-label={t('搜索校园地点')}
                    />
                    {query && (
                      <button
                        title={t('清除搜索')}
                        onClick={() => {
                          setQuery('');
                          dock.current
                            ?.querySelector<HTMLInputElement>(
                              'input[type="search"]',
                            )
                            ?.focus();
                        }}
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>
                  <output
                    className="result-heading"
                    data-searching={Boolean(query.trim())}
                    aria-atomic="true"
                  >
                    {query.trim()
                      ? t('{count} 个结果', { count: resultCount })
                      : t('{count} 个地点', { count: resultCount })}
                  </output>
                  <div className="places">
                    {!landmarks.length ? (
                      error ? (
                        <div className="empty-state">
                          <p>{t('地点数据加载失败')}</p>
                          <button className="search-reset" onClick={retry}>
                            {t('重新加载')}
                          </button>
                        </div>
                      ) : (
                        <output className="empty-state">
                          {t('正在加载地点…')}
                        </output>
                      )
                    ) : resultCount ? (
                      <>
                        <PlaceGroups
                          groups={groups}
                          landmarks={landmarks}
                          selected={selected}
                          hovered={hovered}
                          ready={ready}
                          searching={
                            Boolean(query.trim()) && !buildingMatches.length
                          }
                          onHover={hoverPlace}
                          onChoose={choose}
                        />
                        <BuildingResults
                          buildings={buildingMatches}
                          landmarks={landmarks}
                          selected={selected}
                          ready={ready}
                          titled={places.length > 0}
                          onChoose={choose}
                        />
                      </>
                    ) : (
                      <div className="empty-state">
                        <p>{t('没有找到相关地点或建筑')}</p>
                        <button className="search-reset" onClick={resetSearch}>
                          {t('清空搜索')}
                        </button>
                      </div>
                    )}
                  </div>
                </TabsContent>
                <TabsContent value="layers" className="settings-content">
                  {LAYER_ITEMS.map(([key, label, Icon]) => (
                    <label
                      className="layer-row"
                      key={key}
                      htmlFor={`layer-${key}`}
                    >
                      <Icon size={19} />
                      <span id={`layer-title-${key}`}>{t(label)}</span>
                      <Switch
                        id={`layer-${key}`}
                        checked={layers[key]}
                        onCheckedChange={(on) => toggleLayer(key, on)}
                        aria-labelledby={`layer-title-${key}`}
                      />
                    </label>
                  ))}
                </TabsContent>
                <TabsContent value="environment" className="settings-content">
                  <div className="preset-grid">
                    {PRESETS.map(([p, label, Icon]) => (
                      <button
                        key={p}
                        className={preset === p ? 'active' : ''}
                        onClick={() => changePreset(p)}
                        aria-pressed={preset === p}
                        aria-label={t(label)}
                      >
                        <Image
                          src={`${BASE}/images/presets/${p}.jpg`}
                          alt=""
                          width={640}
                          height={360}
                          loading="lazy"
                          unoptimized
                        />
                        <span className="preset-caption">
                          <Icon size={16} />
                          {t(label)}
                          {preset === p && <Check size={14} />}
                        </span>
                      </button>
                    ))}
                  </div>
                  <div className="setting-row">
                    <span id="quality-title">{t('画质')}</span>
                    <fieldset
                      className="segmented"
                      aria-labelledby="quality-title"
                    >
                      {QUALITY_OPTIONS.map(([q, label]) => (
                        <button
                          key={q}
                          aria-pressed={quality === q}
                          onClick={() => changeQuality(q)}
                        >
                          {t(label)}
                        </button>
                      ))}
                    </fieldset>
                  </div>
                </TabsContent>
              </Tabs>
              {overview && (
                <div className="panel-foot">
                  {t('地图数据更新于 {date}', {
                    date: overview.snapshotAt.slice(0, 10).replaceAll('-', '.'),
                  })}
                </div>
              )}
              {current && (
                <button
                  className="return-landmark"
                  onClick={() => {
                    pendingFocus.current = 'detail';
                    setPanelMode('detail');
                    setPanelExpanded(false);
                  }}
                >
                  {t('返回 {name}', { name: name(current.name) })}
                  <ArrowUpRight size={14} />
                </button>
              )}
            </div>
          )}
          <CampusMinimap
            buildings={buildings}
            current={currentLandmark ?? currentBuilding}
            camera={cameraStore}
            showBoundary={layers.boundary}
          />
        </div>
        {collapsed && tourStarted && (
          <button
            className="tour-compact"
            onClick={() => setTour((value) => !value)}
          >
            {tour ? <Pause size={15} /> : <Play size={15} />}
            {tour ? t('暂停游览') : t('继续游览')}
            <span>
              {tourIndex + 1}/{landmarks.length}
            </span>
          </button>
        )}
        <div
          className={`tour-bar ${tourStarted ? 'tour-active' : 'tour-idle'}`}
        >
          {tour && (
            <div className="tour-timer" key={tourIndex} aria-hidden="true">
              <span ref={tourProgress} />
            </div>
          )}
          {tourStarted && (
            <div className="tour-heading">
              <div className="tour-copy">
                <small>
                  <span className="tour-position">
                    {tourIndex + 1}/{landmarks.length}
                  </span>
                  <span>
                    {landmarks[tourIndex]
                      ? name(landmarks[tourIndex].name)
                      : ''}
                  </span>
                </small>
              </div>
              <button
                className="tour-end"
                title={t('结束游览')}
                aria-label={t('结束游览')}
                onClick={() => {
                  setTour(false);
                  setTourStarted(false);
                  requestAnimationFrame(() => {
                    const target =
                      tourEntry.current ??
                      dock.current?.querySelector<HTMLButtonElement>(
                        '[role="tab"][aria-selected="true"]',
                      );
                    target?.focus({ preventScroll: true });
                  });
                }}
              >
                <X size={16} />
              </button>
            </div>
          )}
          <button
            ref={tourEntry}
            className="tour-start"
            disabled={!ready}
            onClick={() => {
              setTourStarted(true);
              setTour((v) => !v);
            }}
          >
            {tour ? <Pause size={15} /> : <Play size={15} />}
            <span>
              {tour
                ? t('暂停游览')
                : tourStarted
                  ? t('继续游览')
                  : t('开始游览')}
            </span>
            {!tourStarted && (
              <small className="tour-count">
                {t('{count} 个地点', { count: landmarks.length })}
              </small>
            )}
          </button>
          {tourStarted && (
            <>
              <button
                className="tour-skip"
                title={t('上一站')}
                disabled={!ready}
                onClick={() => jump(-1)}
              >
                <ChevronLeft size={17} />
              </button>
              <button
                className="tour-skip"
                title={t('下一站')}
                disabled={!ready}
                onClick={() => jump(1)}
              >
                <ChevronRight size={17} />
              </button>
            </>
          )}
        </div>
      </aside>
      <Tooltip.Provider delay={200}>
        <div className="map-tools" aria-label={t('视角控制')}>
          <MapToolButton
            className="north-button"
            onClick={() => view('north')}
            aria-label={t('朝向正北')}
            tooltip={t('朝向正北')}
          >
            <NorthArrow camera={cameraStore} />
            <span>N</span>
          </MapToolButton>
          <div className="tool-stack zoom-tools">
            <MapToolButton
              onClick={() => view('zoomIn')}
              aria-label={t('放大')}
              tooltip={t('放大')}
              shortcut="+"
            >
              <Plus size={19} />
            </MapToolButton>
            <MapToolButton
              onClick={() => view('zoomOut')}
              aria-label={t('缩小')}
              tooltip={t('缩小')}
              shortcut="−"
            >
              <Minus size={19} />
            </MapToolButton>
          </div>
          <div className="tool-stack secondary-tools">
            <MapToolButton
              onClick={() => view('top')}
              aria-label={t('俯视')}
              tooltip={t('俯视')}
            >
              <Grid2X2 size={18} />
            </MapToolButton>
            <MapToolButton
              onClick={() => view('tilt')}
              aria-label={t('鸟瞰')}
              tooltip={t('鸟瞰')}
            >
              <ScanEye size={18} />
            </MapToolButton>
            <MapToolButton
              onClick={() => view('overview')}
              aria-label={t('回到全景')}
              tooltip={t('回到全景')}
              shortcut="Home"
            >
              <House size={18} />
            </MapToolButton>
            <MapToolButton
              aria-label={t('全屏')}
              tooltip={t('全屏')}
              onClick={toggleFullscreen}
            >
              <Expand size={18} />
            </MapToolButton>
            <MapToolButton
              aria-label={t('分享')}
              tooltip={t('分享')}
              disabled={!ready}
              onClick={openShare}
            >
              <Share2 size={18} />
            </MapToolButton>
          </div>
          <div className="tool-stack mobile-tools">
            <MapToolButton
              className="mobile-reset"
              onClick={() => view('overview')}
              aria-label={t('回到全景')}
              tooltip={t('回到全景')}
              shortcut="Home"
            >
              <House size={18} />
            </MapToolButton>
            <MapToolButton
              className="more-tools-button"
              onClick={() => {
                pauseMotion();
                setToolsOpen(true);
              }}
              aria-haspopup="dialog"
              aria-label={t('更多工具')}
              tooltip={t('更多工具')}
            >
              <Ellipsis size={20} />
              <span>{t('更多')}</span>
            </MapToolButton>
          </div>
        </div>
      </Tooltip.Provider>
      <footer className="map-footer">
        <button
          className="gesture-help"
          onClick={() => {
            pauseMotion();
            setHelpOpen(true);
          }}
        >
          {t('操作说明')}
        </button>
        {layers.boundary && (
          <span className="boundary-legend">
            <i />
            {t('校园大致边界')}
          </span>
        )}
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer"
        >
          © OpenStreetMap contributors
        </a>
      </footer>
      <CampusLoadStatus store={loadStatusStore} ready={ready} retry={retry} />
      {toast && (
        <output className="toast">
          <Check size={15} />
          {t(toast)}
        </output>
      )}
      {debug && metrics && (
        <pre className="debug-metrics">{JSON.stringify(metrics, null, 2)}</pre>
      )}
      <Dialog open={toolsOpen} onOpenChange={setToolsOpen}>
        <DialogContent className="tools-dialog">
          <DialogTitle>{t('更多工具')}</DialogTitle>
          <div className="tools-grid">
            <button
              onClick={() => {
                setToolsOpen(false);
                view('overview');
              }}
            >
              <House size={20} />
              {t('回到全景')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                view('north');
              }}
            >
              <Navigation size={20} />
              {t('朝向正北')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                view('top');
              }}
            >
              <Grid2X2 size={20} />
              {t('俯视')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                view('tilt');
              }}
            >
              <ScanEye size={20} />
              {t('鸟瞰')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                toggleFullscreen();
              }}
            >
              <Expand size={20} />
              {t('全屏')}
            </button>
            <button
              disabled={!ready}
              onClick={() => {
                setToolsOpen(false);
                openShare();
              }}
            >
              <Share2 size={20} />
              {t('分享')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                pauseMotion();
                setHelpOpen(true);
              }}
            >
              <CircleHelp size={20} />
              {t('操作说明')}
            </button>
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
        <DialogContent className="tools-dialog">
          <DialogTitle>{t('操作说明')}</DialogTitle>
          <dl className="gesture-instructions">
            <dt>{t('触屏')}</dt>
            <dd>{t('单指拖动旋转，双指拖动平移，双指捏合缩放')}</dd>
            <dt>{t('鼠标与触控板')}</dt>
            <dd>{t('拖动旋转，右键拖动平移，滚轮缩放')}</dd>
            <dt>{t('键盘')}</dt>
            <dd>
              {t(
                'Tab 切换控件，Enter 确认；选中地图后，方向键平移，+ 和 − 缩放，Home 回到全景',
              )}
            </dd>
            <dt>{t('搜索')}</dt>
            <dd>{t('支持名称和简称，如“六教”')}</dd>
            <dt>{t('游览')}</dt>
            <dd>{t('拖动地图即可暂停')}</dd>
          </dl>
        </DialogContent>
      </Dialog>
      <Dialog open={shareOpen} onOpenChange={setShareOpen}>
        <DialogContent className="share-dialog">
          <DialogTitle>{t('分享')}</DialogTitle>
          <div className="tools-grid">
            <button
              disabled={!ready}
              onClick={() => {
                setShareOpen(false);
                void shareView();
              }}
            >
              <Share2 size={20} />
              {t('复制链接')}
            </button>
            <button
              disabled={!ready}
              onClick={() => {
                setShareOpen(false);
                void exportView();
              }}
            >
              <Download size={20} />
              {t('下载图片')}
            </button>
          </div>
        </DialogContent>
      </Dialog>
      <Dialog
        open={Boolean(shareLink)}
        onOpenChange={(open) => {
          if (!open) setShareLink('');
        }}
      >
        <DialogContent className="share-dialog">
          <DialogTitle>{t('复制链接')}</DialogTitle>
          <Input
            aria-label={t('视角链接')}
            value={shareLink}
            readOnly
            onFocus={(event) => event.currentTarget.select()}
          />
        </DialogContent>
      </Dialog>
    </main>
  );
}

function PlaceGroups({
  groups,
  landmarks,
  selected,
  hovered,
  ready,
  searching,
  onHover,
  onChoose,
}: {
  groups: { key: string; name: string; places: Landmark[] }[];
  landmarks: Landmark[];
  selected: string | null;
  hovered: string | null;
  ready: boolean;
  searching: boolean;
  onHover: (id: string | null) => void;
  onChoose: (id: string) => void;
}) {
  const { name } = useCampusLocale();
  return (
    <>
      {groups.map((group) => (
        <section
          className="place-group"
          key={group.key}
          aria-label={group.name}
        >
          {!searching && <h3>{group.name}</h3>}
          {group.places.map((p) => (
            <button
              key={p.id}
              data-place-id={p.id}
              className={`place-row ${selected === p.id ? 'selected' : ''} ${hovered === p.id ? 'linked-hover' : ''}`}
              onPointerEnter={() => onHover(p.id)}
              onPointerLeave={() => onHover(null)}
              onFocus={() => onHover(p.id)}
              onBlur={() => onHover(null)}
              onClick={() => onChoose(p.id)}
              disabled={!ready}
            >
              <span className="place-index">
                {String(landmarks.findIndex((l) => l.id === p.id) + 1).padStart(
                  2,
                  '0',
                )}
              </span>
              <span className="place-copy">
                <strong>{name(p.name)}</strong>
              </span>
              <ChevronRight size={16} aria-hidden="true" />
            </button>
          ))}
        </section>
      ))}
    </>
  );
}

function BuildingResults({
  buildings,
  landmarks,
  selected,
  ready,
  titled,
  onChoose,
}: {
  buildings: Building[];
  landmarks: Landmark[];
  selected: string | null;
  ready: boolean;
  titled: boolean;
  onChoose: (id: string) => void;
}) {
  const { t, name, locale } = useCampusLocale();
  if (!buildings.length) return null;
  const shown = buildings.slice(0, BUILDING_RESULT_LIMIT);
  return (
    <section
      className="place-group building-results"
      aria-label={t('其他建筑')}
    >
      {titled && <h3>{t('其他建筑')}</h3>}
      {shown.map((b) => (
        <button
          key={b.id}
          data-place-id={b.id}
          className={`place-row building-row ${selected === b.id ? 'selected' : ''}`}
          onClick={() => onChoose(b.id)}
          disabled={!ready}
        >
          <Building2 size={15} className="place-kind" aria-hidden="true" />
          <span className="place-copy">
            <strong>{name(b.name)}</strong>
            <small>
              <span>{t(CATEGORY_NAMES[b.category])}</span>
              <span>{buildingLocationLabel(b, landmarks, locale)}</span>
            </small>
          </span>
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      ))}
      {buildings.length > shown.length && (
        <p className="result-more">
          {t('还有 {count} 处，请输入更完整的名称', {
            count: buildings.length - shown.length,
          })}
        </p>
      )}
    </section>
  );
}

/** Follows camera samples without re-rendering the surrounding map controls. */
function NorthArrow({ camera }: { camera: CameraStore }) {
  // A primitive selection skips renders for samples that only pan or zoom.
  const bearing = useSyncExternalStore(
    camera.subscribe,
    () => cameraBearing(camera.get()),
    () => cameraBearing(null),
  );
  return (
    <Navigation size={20} style={{ transform: `rotate(${bearing - 45}deg)` }} />
  );
}
function MapToolButton({
  tooltip,
  shortcut,
  ...props
}: ComponentProps<'button'> & { tooltip: string; shortcut?: string }) {
  return (
    <Tooltip.Root disabled={props.disabled}>
      <Tooltip.Trigger render={<button {...props} />} />
      <Tooltip.Portal>
        <Tooltip.Positioner
          className="map-tool-tooltip-positioner"
          side="left"
          sideOffset={10}
        >
          <Tooltip.Popup className="map-tool-tooltip">
            {tooltip}
            {shortcut && <kbd>{shortcut}</kbd>}
          </Tooltip.Popup>
        </Tooltip.Positioner>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
