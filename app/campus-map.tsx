import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react';
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsDown,
  ChevronsUp,
  CircleAlert,
  Layers3,
  MapPin,
  Sun,
} from 'lucide-react';
import { CampusHeader } from '@/components/campus-header';
import { CampusLayerSettings } from '@/components/campus-layer-settings';
import { CampusLightingSettings } from '@/components/campus-lighting-settings';
import { CampusLoadStatus } from '@/components/campus-load-status';
import {
  CampusLocaleProvider,
  useCampusLocale,
} from '@/components/campus-locale';
import {
  CampusHelp,
  CampusMapTools,
  CampusMoreTools,
  type MapView,
} from '@/components/campus-map-tools';
import { CampusMinimap } from '@/components/campus-minimap';
import { CampusPlaceDetail } from '@/components/campus-place-detail';
import { CampusPlaces } from '@/components/campus-places';
import { CampusShare } from '@/components/campus-share';
import { CampusTour } from '@/components/campus-tour';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSceneFrame, useVisualViewport } from '@/hooks/use-campus-layout';
import { useCampusTour } from '@/hooks/use-campus-tour';
import { asset, prefetchBase } from '@/lib/campus/boot';
import { createCameraStore } from '@/lib/campus/camera-store';
import { createLoadStatusStore } from '@/lib/campus/load-status-store';
import { searchableBuildings } from '@/lib/campus/navigation';
import { decodeShare } from '@/lib/campus/share';
import { fetchJson } from '@/lib/campus/streaming';
import type {
  Building,
  Landmark,
  LandmarkView,
  LayerKey,
  Metrics,
  Overview,
  Preset,
  Quality,
  SceneController,
} from '@/lib/campus/types';
import { DEFAULT_LAYERS } from '@/lib/campus/types';
export default function CampusApp() {
  return (
    <CampusLocaleProvider>
      <CampusMap />
    </CampusLocaleProvider>
  );
}
function CampusMap() {
  const { locale, t, name } = useCampusLocale();
  const localeRef = useRef(locale);
  const dock = useRef<HTMLElement>(null);
  const panelToggle = useRef<HTMLButtonElement>(null);
  const detailBack = useRef<HTMLButtonElement>(null);
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
    [collapsed, setCollapsed] = useState(false),
    [toast, setToast] = useState<{ message: string; failed: boolean } | null>(
      null,
    ),
    [retrySeed, setRetrySeed] = useState(0),
    [metrics, setMetrics] = useState<Metrics | null>(null);
  const visitTourStop = useCallback(
    (id: string) => controller.current?.focus(id, 'tour'),
    [],
  );
  const tour = useCampusTour(landmarks, visitTourStop);
  const { setPlaying: setTour, setIndex: setTourIndex } = tour;
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
  const [panelExpanded, setPanelExpanded] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [debug, setDebug] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [cameraStore] = useState(createCameraStore);
  const [panelMode, setPanelMode] = useState<'menu' | 'detail'>('menu');
  const [landmarkView, setLandmarkView] = useState<LandmarkView | null>(
    'oblique',
  );
  const [orbit, setOrbit] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  // A fresh object restarts the timer when the same message repeats.
  const notify = useCallback(
    (message: string, failed = false) => setToast({ message, failed }),
    [],
  );
  const pauseMotion = useCallback(() => {
    setTour(false);
    controller.current?.setOrbit(false);
  }, [setTour]);
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
    const t = setTimeout(() => setToast(null), 3500);
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
            import.meta.env.DEV &&
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
  }, [retrySeed, cameraStore, loadStatusStore, setTour, setTourIndex]);
  useEffect(() => {
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReducedMotion(preference.matches);
    update();
    preference.addEventListener('change', update);
    return () => preference.removeEventListener('change', update);
  }, []);
  const keyboardOpen = useVisualViewport(host);
  useSceneFrame({ ready, collapsed, framingRequest, host, dock, controller });
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
  const choose = useCallback(
    (id: string) => {
      setTour(false);
      controller.current?.focus(id);
    },
    [setTour],
  );
  const currentLandmark = landmarks.find((l) => l.id === selected);
  const currentBuilding = selected
    ? buildings.find((b) => b.id === selected || b.landmark === selected)
    : undefined;
  const current = currentLandmark ?? currentBuilding;
  function hoverPlace(id: string | null) {
    controller.current?.setHovered(id);
  }
  function openShare() {
    pauseMotion();
    setShareOpen(true);
  }
  function openHelp() {
    pauseMotion();
    setHelpOpen(true);
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
  function view(v: MapView) {
    setTour(false);
    setLandmarkView(null);
    controller.current?.view(v);
    if (v === 'overview') {
      setSelected(null);
      setCollapsed(false);
    }
  }
  function retry() {
    if (controller.current) controller.current.retry();
    else {
      loadStatusStore.set('正在重新加载…');
      setRetrySeed((s) => s + 1);
    }
  }
  function toggleFullscreen() {
    if (!document.fullscreenEnabled) {
      notify('当前浏览器不支持全屏', true);
      return;
    }
    const action = document.fullscreenElement
      ? document.exitFullscreen()
      : document.documentElement.requestFullscreen();
    void action.catch(() => notify('当前浏览器不支持全屏', true));
  }
  return (
    <main className={`campus-app ${keyboardOpen ? 'keyboard-open' : ''}`}>
      <div className="scene-host" ref={host} />
      <CampusHeader onHome={() => view('overview')} />
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
            <CampusPlaceDetail
              landmark={currentLandmark}
              building={currentBuilding}
              landmarks={landmarks}
              view={landmarkView}
              orbit={orbit}
              reducedMotion={reducedMotion}
              onViewChange={changeLandmarkView}
              onOrbitChange={() => {
                setTour(false);
                controller.current?.setOrbit(!orbit);
              }}
              onShare={openShare}
            />
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
                  <CampusPlaces
                    landmarks={landmarks}
                    buildings={buildings}
                    query={query}
                    selected={selected}
                    hovered={hovered}
                    ready={ready}
                    failed={error}
                    onQueryChange={setQuery}
                    onSearchFocus={() => {
                      pauseMotion();
                      setPanelExpanded(true);
                    }}
                    onHover={hoverPlace}
                    onChoose={choose}
                    onRetry={retry}
                  />
                </TabsContent>
                <TabsContent value="layers" className="settings-content">
                  <CampusLayerSettings layers={layers} onToggle={toggleLayer} />
                </TabsContent>
                <TabsContent value="environment" className="settings-content">
                  <CampusLightingSettings
                    preset={preset}
                    quality={quality}
                    onPresetChange={changePreset}
                    onQualityChange={changeQuality}
                  />
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
                  <ChevronRight size={16} aria-hidden="true" />
                </button>
              )}
            </div>
          )}
          <CampusMinimap
            buildings={buildings}
            current={current}
            camera={cameraStore}
            showBoundary={layers.boundary}
          />
        </div>
        <CampusTour
          tour={tour}
          landmarks={landmarks}
          ready={ready}
          collapsed={collapsed}
        />
      </aside>
      <CampusMapTools
        camera={cameraStore}
        ready={ready}
        onView={view}
        onFullscreen={toggleFullscreen}
        onShare={openShare}
        onMore={() => {
          pauseMotion();
          setToolsOpen(true);
        }}
      />
      <footer className="map-footer">
        <button className="gesture-help" onClick={openHelp}>
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
        <output className={`toast ${toast.failed ? 'failed' : ''}`}>
          {toast.failed ? (
            <CircleAlert size={15} aria-hidden="true" />
          ) : (
            <Check size={15} aria-hidden="true" />
          )}
          {t(toast.message)}
        </output>
      )}
      {debug && metrics && (
        <pre className="debug-metrics">{JSON.stringify(metrics, null, 2)}</pre>
      )}
      <CampusMoreTools
        open={toolsOpen}
        onOpenChange={setToolsOpen}
        ready={ready}
        onView={view}
        onFullscreen={toggleFullscreen}
        onShare={openShare}
        onHelp={openHelp}
      />
      <CampusHelp open={helpOpen} onOpenChange={setHelpOpen} />
      <CampusShare
        open={shareOpen}
        onOpenChange={setShareOpen}
        ready={ready}
        controller={controller}
        pauseMotion={pauseMotion}
        notify={notify}
      />
    </main>
  );
}
