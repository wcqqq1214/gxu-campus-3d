'use client';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentProps,
} from 'react';
import {
  CampusLocaleProvider,
  useCampusLocale,
} from '@/components/campus-locale';
import { statusText, type Message } from '@/lib/campus/i18n';
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
  Download,
  Expand,
  Grid2X2,
  Globe,
  House,
  Orbit,
  Scan,
  Dumbbell,
  RectangleEllipsis,
  ScanEye,
  Ellipsis,
  CircleHelp,
  Layers3,
  LoaderCircle,
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
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
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
import { searchLandmarks } from '@/lib/campus/navigation';
import {
  decodeShare,
  encodeShare,
  cameraBearing,
  type CameraSnapshot,
} from '@/lib/campus/share';
import { fetchJson } from '@/lib/campus/streaming';
import { CampusMinimap } from '@/components/campus-minimap';
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';
const TOUR_STOP_MS = 8500;
const LAYER_ITEMS: [LayerKey, string, string, typeof Building2][] = [
  ['labels', '地点名称', '在地图上显示地点名称', RectangleEllipsis],
  ['boundary', '校园边界', '白色细线标示大致范围', Scan],
  ['buildings', '校园建筑', '教学楼、宿舍与地标', Building2],
  ['vegetation', '树木', '乔木、棕榈与林荫景观', Trees],
  ['roads', '道路与桥梁', '校道、桥梁与步行空间', Navigation],
  ['water', '湖塘水面', '镜湖、碧云湖及其他水体', Waves],
  ['sports', '运动场地', '球场、跑道与游泳池', Dumbbell],
  ['context', '周边建筑', '仅保留贴近校界的周边建筑', Layers3],
];
const PRESETS: [Preset, string, string, typeof Sun][] = [
  ['morning', '晨光', '树影初长', Sunrise],
  ['day', '日间', '校园清朗', Sun],
  ['evening', '黄昏', '余晖入窗', Sunset],
  ['night', '夜景', '灯火渐明', Moon],
];
const QUALITY_NAMES: Record<Quality, string> = {
  auto: '自动',
  fine: '精细',
  smooth: '流畅',
};
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
  const [ready, setReady] = useState(false),
    [status, setStatus] = useState<Message>('正在铺开校园…'),
    [loadProgress, setLoadProgress] = useState<number | undefined>(undefined),
    [error, setError] = useState(false),
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
    localeRef.current = locale;
    controller.current?.setLocale(locale);
  }, [locale]);
  const [framingRequest, setFramingRequest] = useState(0);
  const framedRequest = useRef(0);
  const [overviewRetry, setOverviewRetry] = useState(0);
  const [overviewError, setOverviewError] = useState(false);
  const [panelExpanded, setPanelExpanded] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const [debug, setDebug] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [cameraState, setCameraState] = useState<CameraSnapshot | null>(null);
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
    void fetchJson<Overview>(`${BASE}/data/overview.json`, lifetime.signal)
      .then((data) => {
        if (!lifetime.signal.aborted) {
          setOverview(data);
          setOverviewError(false);
        }
      })
      .catch(() => {
        if (!lifetime.signal.aborted) setOverviewError(true);
      });
    return () => lifetime.abort();
  }, [overviewRetry]);
  useEffect(() => {
    let active = true;
    const lifetime = new AbortController();
    queueMicrotask(() => {
      if (active) setDebug(new URLSearchParams(location.search).has('debug'));
    });
    let cleanup: (() => void) | undefined;
    void Promise.all([
      fetchJson<Building[]>(`${BASE}/data/buildings.json`, lifetime.signal),
      fetchJson<Landmark[]>(`${BASE}/data/landmarks.json`, lifetime.signal),
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
          const c = createScene(host.current, bs, ls, {
            onStatus: (message, failed = false, progress) => {
              if (active) {
                setStatus(message);
                setLoadProgress(progress);
                setError(failed);
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
                if (id) setTourIndex(ls.findIndex((place) => place.id === id));
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
              if (active) setCameraState(snapshot);
            },
            onOrbit: (on) => {
              if (active) {
                setOrbit(on);
                if (on) setLandmarkView('oblique');
              }
            },
            onMetrics: (m) => {
              if (active) setMetrics(m);
            },
          });
          c.setLocale(localeRef.current);
          controller.current = c;
          cleanup = () => c.dispose();
          c.setQuality(settings.current.quality);
          c.setPreset(settings.current.preset);
          for (const key of Object.keys(settings.current.layers) as LayerKey[])
            c.setLayer(key, settings.current.layers[key]);
          const shared = decodeShare(
            location.hash,
            ls.map((l) => l.id),
          );
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
          setStatus(
            '此浏览器暂时无法启用三维画面。请开启硬件加速，或使用支持 WebGL 2 的浏览器。',
          );
          setError(true);
        }
      })
      .catch(() => {
        if (active) {
          setStatus('校园资料加载失败，请检查网络后重试。');
          setError(true);
        }
      });
    return () => {
      active = false;
      lifetime.abort();
      cleanup?.();
      controller.current = null;
    };
  }, [retrySeed]);
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
  const groups = query.trim()
    ? [{ key: 'search', name: t('搜索结果'), places }]
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
      notify('视角链接已复制，可分享或稍后打开');
    } catch {
      setShareLink(url.href);
    }
  }
  function retry() {
    if (controller.current) controller.current.retry();
    else {
      setError(false);
      setStatus('正在重新加载…');
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
      notify('当前浏览器不支持全屏，可使用横屏浏览。');
      return;
    }
    const action = document.fullscreenElement
      ? document.exitFullscreen()
      : document.documentElement.requestFullscreen();
    void action.catch(() => notify('当前浏览器不支持全屏，可使用横屏浏览。'));
  }
  async function exportView() {
    try {
      await controller.current?.exportImage();
      notify('校园画面已导出');
    } catch {
      notify('导出失败，请重试。');
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
            title={t('返回全景')}
            aria-label={t('返回校园全景')}
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
              <Globe size={20} aria-hidden="true" />
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
              width={20}
              height={20}
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
            className="dock-toggle"
            aria-expanded={!collapsed}
            aria-controls="campus-panel-body"
            aria-label={collapsed ? t('展开面板') : t('收起面板')}
            onClick={() => setCollapsed((v) => !v)}
          >
            <span>
              {panelMode === 'detail' && current
                ? collapsed
                  ? name(current.name)
                  : ''
                : t('校园浏览')}
            </span>
            <small>{collapsed ? t('展开') : t('收起面板')}</small>
            <ChevronDown size={16} />
          </button>
          {!collapsed && (
            <button
              className="dock-expand"
              aria-expanded={panelExpanded}
              onClick={() => {
                setPanelExpanded((value) => !value);
              }}
            >
              {panelExpanded
                ? t('简要')
                : panelMode === 'detail'
                  ? t('详情')
                  : t('展开面板')}
            </button>
          )}
        </div>
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
                <div>
                  <div className="eyebrow">
                    {t(CATEGORY_NAMES[current.category])}
                  </div>
                  <h2>{name(current.name)}</h2>
                </div>
              </div>
              <p>
                {currentLandmark
                  ? landmarkDescription(currentLandmark, locale)
                  : t('{category}建筑。', {
                      category: t(CATEGORY_NAMES[currentBuilding!.category]),
                    })}
              </p>
              {currentLandmark && (
                <div key={current.id}>
                  <fieldset
                    className="landmark-views"
                    aria-label={t('地点观察视角')}
                  >
                    <button
                      aria-pressed={!orbit && landmarkView === 'oblique'}
                      onClick={() => changeLandmarkView('oblique')}
                    >
                      {t('全貌')}
                    </button>
                    <button
                      aria-pressed={!orbit && landmarkView === 'top'}
                      onClick={() => changeLandmarkView('top')}
                    >
                      {t('俯视')}
                    </button>
                    <button
                      aria-pressed={orbit}
                      disabled={reducedMotion}
                      title={
                        reducedMotion
                          ? t('系统已启用减少动态效果')
                          : t('环绕当前地点，拖动画面可暂停')
                      }
                      onClick={() => {
                        setTour(false);
                        controller.current?.setOrbit(!orbit);
                      }}
                    >
                      {orbit ? <Pause size={14} /> : <Orbit size={14} />}
                      {orbit ? t('暂停环绕') : t('环绕')}
                    </button>

                    {(
                      [
                        [
                          'front',
                          ['library', 'teaching-six'].includes(
                            currentLandmark.id,
                          )
                            ? t('南侧')
                            : t('正面'),
                        ],
                        [
                          'back',
                          ['library', 'teaching-six'].includes(
                            currentLandmark.id,
                          )
                            ? t('北侧')
                            : t('背面'),
                        ],
                        [
                          'entrance',
                          ['library', 'teaching-six'].includes(
                            currentLandmark.id,
                          )
                            ? t('南门近景')
                            : currentLandmark.placeKind === 'bridge'
                              ? t('桥下近景')
                              : currentLandmark.placeKind === 'sculpture'
                                ? t('雕塑近景')
                                : t('入口近景'),
                        ],
                        ...(['library', 'teaching-six'].includes(
                          currentLandmark.id,
                        )
                          ? [['rear-entrance', t('北门近景')]]
                          : []),
                      ] as [LandmarkView, string][]
                    ).map(([value, label]) => (
                      <button
                        key={value}
                        aria-pressed={!orbit && landmarkView === value}
                        onClick={() => changeLandmarkView(value)}
                      >
                        {t(label)}
                      </button>
                    ))}
                  </fieldset>
                </div>
              )}
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
                      placeholder={t('搜索地点，如图书馆、六教')}
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
                  <output className="result-heading" aria-atomic="true">
                    <span>{query.trim() ? t('搜索结果') : t('地点')}</span>
                    <span>{t('{count} 处', { count: places.length })}</span>
                  </output>
                  <div className="places">
                    {!landmarks.length ? (
                      error ? (
                        <div className="empty-state">
                          <p>{t('地点资料暂时无法加载，请检查网络后重试。')}</p>
                          <button className="search-reset" onClick={retry}>
                            {t('重新加载地点')}
                          </button>
                        </div>
                      ) : (
                        <output className="empty-state">
                          {t('正在加载地点…')}
                        </output>
                      )
                    ) : places.length ? (
                      <PlaceGroups
                        groups={groups}
                        landmarks={landmarks}
                        selected={selected}
                        hovered={hovered}
                        ready={ready}
                        searching={Boolean(query.trim())}
                        onHover={hoverPlace}
                        onChoose={choose}
                      />
                    ) : (
                      <div className="empty-state">
                        <p>{t('没有找到相关地点。试试“图书馆”或“六教”。')}</p>
                        <button className="search-reset" onClick={resetSearch}>
                          {t('清空搜索')}
                        </button>
                      </div>
                    )}
                  </div>
                </TabsContent>
                <TabsContent value="layers" className="settings-content">
                  <p className="section-hint">{t('选择地图中显示的内容')}</p>
                  {LAYER_ITEMS.map(([key, label, desc, Icon]) => (
                    <label
                      className="layer-row"
                      key={key}
                      htmlFor={`layer-${key}`}
                    >
                      <Icon size={19} />
                      <span>
                        <strong id={`layer-title-${key}`}>{t(label)}</strong>
                        <small id={`layer-description-${key}`}>{t(desc)}</small>
                      </span>
                      <Switch
                        id={`layer-${key}`}
                        checked={layers[key]}
                        onCheckedChange={(on) => toggleLayer(key, on)}
                        aria-labelledby={`layer-title-${key}`}
                        aria-describedby={`layer-description-${key}`}
                      />
                    </label>
                  ))}
                  <details className="menu-disclosure layer-note">
                    <summary>
                      {t('关于校园边界')}
                      <ChevronDown size={15} />
                    </summary>
                    <p className="settings-note">
                      {t(
                        '白色细线表示校园大致范围；农院路为公共道路，不代表封闭校区。',
                      )}
                    </p>
                  </details>
                </TabsContent>
                <TabsContent value="environment" className="settings-content">
                  <p className="section-hint">{t('同一座校园，不同的光景')}</p>
                  <div className="preset-grid">
                    {PRESETS.map(([p, label, caption, Icon]) => (
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
                          <strong>{t(label)}</strong>
                          {preset === p && <Check size={14} />}
                        </span>
                        <small>{t(caption)}</small>
                      </button>
                    ))}
                  </div>
                  <details className="menu-disclosure quality-disclosure">
                    <summary>
                      <span>
                        {t('画质')}
                        <strong>{t(QUALITY_NAMES[quality])}</strong>
                      </span>
                      <ChevronDown size={15} />
                    </summary>
                    <RadioGroup
                      value={quality}
                      onValueChange={(v) => changeQuality(v as Quality)}
                      className="quality-options"
                      aria-label={t('画质')}
                    >
                      {[
                        ['auto', t('自动'), t('根据屏幕与运行表现调节')],
                        ['fine', t('精细'), t('完整植被、阴影与近景细节')],
                        ['smooth', t('流畅'), t('降低植被密度与渲染分辨率')],
                      ].map(([q, name, desc]) => (
                        <label key={q} htmlFor={`quality-${q}`}>
                          <RadioGroupItem
                            id={`quality-${q}`}
                            value={q}
                            aria-labelledby={`quality-title-${q}`}
                          />
                          <span>
                            <strong id={`quality-title-${q}`}>{name}</strong>
                            <small>{t(desc)}</small>
                          </span>
                        </label>
                      ))}
                    </RadioGroup>
                  </details>
                  <p className="settings-note">
                    {t('预览取自图书馆同一视角，光照为氛围模拟。')}
                  </p>
                </TabsContent>
              </Tabs>
              <div className="panel-foot">
                {overviewError ? (
                  <button onClick={() => setOverviewRetry((n) => n + 1)}>
                    {t('地图数据暂不可用 · 重试')}
                  </button>
                ) : overview ? (
                  t('地图数据 · {date}', {
                    date: overview.snapshotAt.slice(0, 10).replaceAll('-', '.'),
                  })
                ) : (
                  t('地图数据加载中…')
                )}
              </div>
              {current && (
                <button
                  className="return-landmark"
                  onClick={() => {
                    pendingFocus.current = 'detail';
                    setPanelMode('detail');
                    setPanelExpanded(false);
                  }}
                >
                  {t('返回 {name}', { name: name(current.name) })}{' '}
                  <ArrowUpRight size={14} />
                </button>
              )}
            </div>
          )}
          <CampusMinimap
            buildings={buildings}
            current={currentLandmark}
            camera={cameraState}
            showBoundary={layers.boundary}
          />
        </div>
        {collapsed && tourStarted && (
          <button
            className="tour-compact"
            onClick={() => setTour((value) => !value)}
          >
            {tour ? <Pause size={15} /> : <Play size={15} />}
            {tour ? t('暂停游览') : t('继续游览')} · {tourIndex + 1}/
            {landmarks.length}
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
                <strong>{tour ? t('正在游览') : t('游览已暂停')}</strong>
                <small>
                  {String(tourIndex + 1).padStart(2, '0')} / {landmarks.length}{' '}
                  ·{' '}
                  {landmarks[tourIndex] ? name(landmarks[tourIndex].name) : ''}
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
            {tourStarted && (
              <small className="mobile-tour-progress">
                {tourIndex + 1}/{landmarks.length}
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
            aria-label={t('正北朝向')}
            tooltip={t('正北朝向')}
          >
            <Navigation
              size={20}
              style={{
                transform: `rotate(${cameraBearing(cameraState) - 45}deg)`,
              }}
            />
            <span>N</span>
          </MapToolButton>
          <div className="tool-stack zoom-tools">
            <MapToolButton
              onClick={() => view('zoomIn')}
              aria-label={t('放大')}
              tooltip={t('放大 · +（聚焦画面）')}
            >
              <Plus size={19} />
            </MapToolButton>
            <MapToolButton
              onClick={() => view('zoomOut')}
              aria-label={t('缩小')}
              tooltip={t('缩小 · −（聚焦画面）')}
            >
              <Minus size={19} />
            </MapToolButton>
          </div>
          <div className="tool-stack secondary-tools">
            <MapToolButton
              onClick={() => view('top')}
              aria-label={t('俯视校园')}
              tooltip={t('俯视校园')}
            >
              <Grid2X2 size={18} />
            </MapToolButton>
            <MapToolButton
              onClick={() => view('tilt')}
              aria-label={t('倾斜鸟瞰')}
              tooltip={t('倾斜鸟瞰')}
            >
              <ScanEye size={18} />
            </MapToolButton>
            <MapToolButton
              onClick={() => view('overview')}
              aria-label={t('全景复位')}
              tooltip={t('全景复位 · Home（聚焦画面）')}
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
              aria-label={t('全景复位')}
              tooltip={t('全景复位 · Home（聚焦画面）')}
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
          {t('操作说明 · 拖动旋转 · 滚轮缩放')}
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
          © OpenStreetMap contributors · ODbL
        </a>
      </footer>
      {status && (
        <div
          className={`scene-status ${error ? 'error' : ''}`}
          role={error ? 'alert' : 'status'}
        >
          {!error && <LoaderCircle className="spin" size={16} />}
          <span>{statusText(locale, status)}</span>
          {loadProgress !== undefined && (
            <progress
              aria-label={t('模型加载进度')}
              max={1}
              value={loadProgress}
            />
          )}
          {error && <button onClick={retry}>{t('重试')}</button>}
        </div>
      )}
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
          <DialogTitle>{t('校园工具')}</DialogTitle>
          <DialogDescription>
            {t('调整视角、分享画面，或查看操作说明。')}
          </DialogDescription>
          <div className="tools-grid">
            <button
              onClick={() => {
                setToolsOpen(false);
                view('overview');
              }}
            >
              <House size={20} />
              {t('全景复位')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                view('north');
              }}
            >
              <Navigation size={20} />
              {t('正北朝向')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                view('top');
              }}
            >
              <Grid2X2 size={20} />
              {t('俯视校园')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                view('tilt');
              }}
            >
              <ScanEye size={20} />
              {t('倾斜鸟瞰')}
            </button>
            <button
              onClick={() => {
                setToolsOpen(false);
                toggleFullscreen();
              }}
            >
              <Expand size={20} />
              {t('切换全屏')}
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
          <DialogTitle>{t('怎样游览校园')}</DialogTitle>
          <DialogDescription>
            {t('选择一个地点，或点击“开始游览”依次浏览校园。')}
          </DialogDescription>
          <dl className="gesture-instructions">
            <dt>{t('手机触控')}</dt>
            <dd>{t('单指拖动旋转；双指拖动平移；双指捏合缩放。')}</dd>
            <dt>{t('鼠标与触控板')}</dt>
            <dd>{t('拖动旋转，右键拖动平移，滚轮缩放。')}</dd>
            <dt>{t('键盘')}</dt>
            <dd>
              {t(
                'Tab 选择控件，Enter 确认。聚焦三维画面后，方向键平移，+ / − 缩放，Home 返回全景。',
              )}
            </dd>
            <dt>{t('查看地点')}</dt>
            <dd>
              {t(
                '搜索“六教”等名称或别名，在详情视角栏选择全貌、俯视、环绕、正背面及近景；可横向滑动查看更多视角。',
              )}
            </dd>
            <dt>{t('暂停游览')}</dt>
            <dd>{t('拖动画面即可暂停，也可使用“暂停游览”按钮。')}</dd>
          </dl>
        </DialogContent>
      </Dialog>
      <Dialog open={shareOpen} onOpenChange={setShareOpen}>
        <DialogContent className="share-dialog">
          <DialogTitle>{t('分享校园')}</DialogTitle>
          <DialogDescription>
            {t('保存当前视角链接，或下载带署名的校园画面。')}
          </DialogDescription>
          <div className="tools-grid">
            <button
              disabled={!ready}
              onClick={() => {
                setShareOpen(false);
                void shareView();
              }}
            >
              <Share2 size={20} />
              {t('复制视角链接')}
            </button>
            <button
              disabled={!ready}
              onClick={() => {
                setShareOpen(false);
                void exportView();
              }}
            >
              <Download size={20} />
              {t('下载画面')}
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
          <DialogTitle>{t('分享这个校园视角')}</DialogTitle>
          <DialogDescription>
            {t('链接保留当前地点、镜头和光照，换一块屏幕也能继续浏览。')}
          </DialogDescription>
          <Input
            aria-label={t('校园视角链接')}
            value={shareLink}
            readOnly
            onFocus={(event) => event.currentTarget.select()}
          />
          <p>{t('复制上方链接即可分享。')}</p>
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
      {' '}
      {groups.map((group) => (
        <section
          className="place-group"
          key={group.key}
          aria-label={group.name}
        >
          {!searching && (
            <h3>
              {group.name}
              <span>{group.places.length}</span>
            </h3>
          )}
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
      ))}{' '}
    </>
  );
}

function MapToolButton({
  tooltip,
  ...props
}: ComponentProps<'button'> & { tooltip: string }) {
  return (
    <Tooltip.Root disabled={props.disabled}>
      <Tooltip.Trigger render={<button {...props} />} />
      <Tooltip.Portal>
        <Tooltip.Positioner
          className="map-tool-tooltip-positioner"
          side="left"
          sideOffset={10}
        >
          <Tooltip.Popup className="map-tool-tooltip">{tooltip}</Tooltip.Popup>
        </Tooltip.Positioner>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
