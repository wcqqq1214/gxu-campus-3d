'use client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowUpRight,
  ArrowRight,
  Building2,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Compass,
  Download,
  Expand,
  GraduationCap,
  Info,
  Layers3,
  LoaderCircle,
  MapPin,
  Minus,
  Moon,
  Navigation,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Search,
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
} from '@/lib/campus/types';
import { DEFAULT_LAYERS, CATEGORY_NAMES } from '@/lib/campus/types';
import { nextTourIndex } from '@/lib/campus/math';
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';
const LAYER_ITEMS: [LayerKey, string, string, typeof Building2][] = [
  ['buildings', '校园建筑', '教学楼、宿舍与校园地标', Building2],
  ['vegetation', '林木植被', '乔木、棕榈与林荫景观', Trees],
  ['roads', '道路与步道', '校道、街道与步行空间', Navigation],
  ['water', '湖塘水面', '镜湖、碧云湖及其他水体', Waves],
  ['sports', '运动场地', '球场、跑道与游泳池', GraduationCap],
  ['context', '周边街区', '校界外约 300 米的建筑', Layers3],
  ['labels', '地点名称', '可点击的校园地标标注', MapPin],
];
const PRESETS: [Preset, string, typeof Sun][] = [
  ['morning', '晨光', Sunrise],
  ['day', '日间', Sun],
  ['evening', '黄昏', Sunset],
  ['night', '夜景', Moon],
];
const refs: Record<string, { name: string; url: string; year: string }> = {
  stadiumVideo: {
    name: '校方综合体育馆视频',
    url: 'https://www.gxu.edu.cn/info/1294/28211.htm',
    year: '发布于 2021-11-17 · 拍摄日期未注明；2024 场馆介绍辅助核对',
  },
  campus2026: {
    name: '校方发布的校园图文',
    url: 'https://www.gxu.edu.cn/info/1004/40412.htm',
    year: '发布于 2026-04-17 · 拍摄日期未注明',
  },
  campusGallery: {
    name: '广西大学校园风光',
    url: 'https://www.gxu.edu.cn/info/1021/18800.htm',
    year: '发布日期与拍摄日期未注明',
  },
  campusAerial: {
    name: '校方校园图文与航拍参考',
    url: 'https://www.gxu.edu.cn/info/1004/40412.htm',
    year: '发布于 2026-04-17 · 场馆屋面局部推定',
  },
  campus2024: {
    name: '校方导览与考场位置图',
    url: 'https://yjsc.gxu.edu.cn/info/1021/3604.htm',
    year: '发布于 2024-12-16 · 图底年代未注明',
  },
  computer2024: {
    name: '计算机与电子信息学院介绍',
    url: 'https://scei.gxu.edu.cn/__local/E/D9/D5/85B5C2D7E31982E036EE64854F2_3961C65F_13838F.pdf?e=.pdf',
    year: '校方 PDF 第 1 页；发布与拍摄日期未注明',
  },
};
async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}/data/${path}`);
  if (!r.ok) throw new Error(path);
  return r.json();
}
export default function Home() {
  const host = useRef<HTMLDivElement>(null),
    controller = useRef<SceneController | null>(null);
  const [buildings, setBuildings] = useState<Building[]>([]),
    [landmarks, setLandmarks] = useState<Landmark[]>([]),
    [overview, setOverview] = useState<Overview | null>(null);
  const [ready, setReady] = useState(false),
    [status, setStatus] = useState('正在铺开校园…'),
    [error, setError] = useState(false),
    [selected, setSelected] = useState<string | null>(null),
    [query, setQuery] = useState(''),
    [category, setCategory] = useState('landmark'),
    [tab, setTab] = useState('explore');
  const [layers, setLayers] = useState(DEFAULT_LAYERS),
    [preset, setPreset] = useState<Preset>('day'),
    [quality, setQuality] = useState<Quality>('auto'),
    [tour, setTour] = useState(false),
    [tourStarted, setTourStarted] = useState(false),
    [tourIndex, setTourIndex] = useState(0),
    [collapsed, setCollapsed] = useState(false),
    [about, setAbout] = useState(false),
    [more, setMore] = useState(false),
    [toast, setToast] = useState(''),
    [retrySeed, setRetrySeed] = useState(0),
    [metrics, setMetrics] = useState<Metrics | null>(null);
  const [debug, setDebug] = useState(false);
  const notify = useCallback((message: string) => setToast(message), []);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(''), 3500);
    return () => clearTimeout(t);
  }, [toast]);
  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) setDebug(new URLSearchParams(location.search).has('debug'));
    });
    let cleanup: (() => void) | undefined;
    void Promise.all([
      getJson<Building[]>('buildings.json'),
      getJson<Landmark[]>('landmarks.json'),
      getJson<Overview>('overview.json'),
      import('@/lib/campus/scene'),
    ])
      .then(([bs, ls, stats, { createScene }]) => {
        if (!active || !host.current) return;
        setBuildings(bs);
        setLandmarks(ls);
        setOverview(stats);
        try {
          if (
            process.env.NODE_ENV === 'development' &&
            new URLSearchParams(location.search).has('test-webgl-unavailable')
          )
            throw new Error('WebGL test');
          const c = createScene(host.current, bs, ls, {
            onStatus: (message, failed = false) => {
              if (active) {
                setStatus(message);
                setError(failed);
              }
            },
            onReady: () => {
              if (active) setReady(true);
            },
            onSelect: (id) => {
              if (active) {
                setSelected(id);
                setMore(false);
                if (window.innerWidth < 760) setCollapsed(Boolean(id));
              }
            },
            onInteract: () => {
              if (active) setTour(false);
            },
            onMetrics: (m) => {
              if (active) setMetrics(m);
            },
          });
          controller.current = c;
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
      cleanup?.();
      controller.current = null;
    };
  }, [retrySeed]);
  const choose = useCallback((id: string) => {
    setTour(false);
    controller.current?.focus(id);
  }, []);
  useEffect(() => {
    if (!tour || !landmarks.length) return;
    controller.current?.focus(landmarks[tourIndex].id);
    const timer = setTimeout(
      () => setTourIndex((i) => nextTourIndex(i, landmarks.length)),
      8500,
    );
    return () => clearTimeout(timer);
  }, [tour, tourIndex, landmarks]);
  const currentLandmark = landmarks.find((l) => l.id === selected);
  const currentBuilding = selected
    ? buildings.find((b) => b.id === selected || b.landmark === selected)
    : undefined;
  const current = currentLandmark ?? currentBuilding;
  const places = useMemo(() => {
    const search = query.trim().toLowerCase();
    if (!search && category === 'landmark')
      return landmarks.map((l) => ({
        id: l.id,
        name: l.name,
        category: l.category,
        landmark: true,
      }));
    const list = buildings.filter(
      (b) =>
        b.insideCampus &&
        (category === 'all' ||
          category === 'landmark' ||
          b.category === category) &&
        (!search || `${b.name} ${b.id}`.toLowerCase().includes(search)),
    );
    const result = list.map((b) => ({
      id: b.landmark ?? b.id,
      name: b.name,
      category: b.category,
      landmark: !!b.landmark,
    }));
    if (['landmark', 'all'].includes(category))
      for (const l of landmarks.filter(
        (l) => !l.osmId && (!search || l.name.toLowerCase().includes(search)),
      ))
        result.unshift({
          id: l.id,
          name: l.name,
          category: l.category,
          landmark: true,
        });
    return result;
  }, [buildings, landmarks, query, category]);
  function toggleLayer(k: LayerKey, on: boolean) {
    setLayers((v) => ({ ...v, [k]: on }));
    controller.current?.setLayer(k, on);
  }
  function changePreset(p: Preset) {
    setPreset(p);
    controller.current?.setPreset(p);
  }
  function changeQuality(q: Quality) {
    setQuality(q);
    controller.current?.setQuality(q);
  }
  function view(
    v: 'overview' | 'top' | 'tilt' | 'north' | 'zoomIn' | 'zoomOut',
  ) {
    setTour(false);
    controller.current?.view(v);
    if (v === 'overview') {
      setSelected(null);
      setCollapsed(false);
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
      );
  }
  return (
    <main className="campus-app">
      <div className="scene-host" ref={host} />
      <header className="masthead">
        <button
          className="brand-mark"
          onClick={() => view('overview')}
          title="返回全景"
        >
          西
        </button>
        <div>
          <h1>
            西大 <span>云游校园</span>
          </h1>
          <p>GUANGXI UNIVERSITY · CAMPUS EXPLORER</p>
        </div>
        <div className="header-location">
          <span className="live-dot" />
          南宁 · 大学东路主校区
        </div>
        <button
          className="icon-button about-button"
          onClick={() => setAbout(true)}
          title="项目说明"
        >
          <Info size={19} />
        </button>
        <a
          className="repo-link"
          href="https://github.com/wcqqq1214/gxu-campus-3d"
          target="_blank"
          rel="noreferrer"
        >
          GitHub <ArrowUpRight size={15} />
        </a>
      </header>
      <aside
        className={`explorer ${collapsed ? 'collapsed' : ''}`}
        aria-label="校园探索菜单"
      >
        <button
          className="mobile-handle"
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((v) => !v)}
        >
          <span />
          {collapsed ? '展开校园菜单' : '收起菜单'}
          <ChevronDown size={16} />
        </button>
        <div className="panel-heading">
          <div className="eyebrow">发现 · GUANGXI UNIVERSITY</div>
          <h2>林荫深处，是西大。</h2>
          <p className="intro">沿着校道，发现熟悉的风景。</p>
        </div>
        <Tabs
          value={tab}
          onValueChange={(v) => setTab(String(v))}
          className="main-tabs"
        >
          <TabsList className="panel-tabs">
            <TabsTrigger value="explore">
              <Compass size={17} />
              探索
            </TabsTrigger>
            <TabsTrigger value="layers">
              <Layers3 size={17} />
              图层
            </TabsTrigger>
            <TabsTrigger value="environment">
              <Sun size={17} />
              环境
            </TabsTrigger>
          </TabsList>
          <TabsContent value="explore" className="explore-content">
            <div className="search-wrap">
              <Search size={16} />
              <Input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="寻找一栋楼，一处风景"
                aria-label="搜索校园建筑"
              />
              {query && (
                <button title="清除搜索" onClick={() => setQuery('')}>
                  <X size={14} />
                </button>
              )}
            </div>
            <div className="category-filters" aria-label="建筑分类">
              {[
                ['landmark', '精选地标'],
                ['academic', '教学'],
                ['living', '生活'],
                ['culture', '文体'],
                ['all', '全部'],
              ].map(([v, label]) => (
                <button
                  key={v}
                  aria-pressed={category === v}
                  className={category === v ? 'active' : ''}
                  onClick={() => setCategory(v)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="result-heading">
              <span>
                {query
                  ? '搜索结果'
                  : category === 'landmark'
                    ? '从这里开始探索'
                    : category === 'all'
                      ? '校园建筑'
                      : '分类探索'}
              </span>
              <span>{places.length} 处</span>
            </div>
            <div className="places">
              {places.length ? (
                places.map((p, i) => (
                  <button
                    key={p.id}
                    className={`place-row ${selected === p.id ? 'selected' : ''}`}
                    onClick={() => choose(p.id)}
                    disabled={!ready}
                  >
                    <span className="place-index">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <span className="place-copy">
                      <strong>{p.name}</strong>
                      <small>
                        {CATEGORY_NAMES[p.category]}
                        {p.landmark ? ' · 重点复原' : ''}
                      </small>
                    </span>
                    <ArrowUpRight size={16} />
                  </button>
                ))
              ) : (
                <div className="empty-state">
                  没有找到对应建筑。
                  <br />
                  试试“宿舍”“教学楼”或学院名称。
                </div>
              )}
            </div>
          </TabsContent>
          <TabsContent value="layers" className="settings-content">
            <p className="section-hint">选择你想看见的校园层次。</p>
            {LAYER_ITEMS.map(([key, label, desc, Icon]) => (
              <label className="layer-row" key={key} htmlFor={`layer-${key}`}>
                <Icon size={19} />
                <span>
                  <strong>{label}</strong>
                  <small>{desc}</small>
                </span>
                <Switch
                  id={`layer-${key}`}
                  checked={layers[key]}
                  onCheckedChange={(on) => toggleLayer(key, on)}
                  aria-label={label}
                />
              </label>
            ))}
          </TabsContent>
          <TabsContent value="environment" className="settings-content">
            <p className="section-hint">同一座校园，不同的光景。</p>
            <div className="preset-grid">
              {PRESETS.map(([p, label, Icon]) => (
                <button
                  key={p}
                  className={preset === p ? 'active' : ''}
                  onClick={() => changePreset(p)}
                  aria-pressed={preset === p}
                >
                  <Icon size={24} />
                  {label}
                  {preset === p && <Check size={12} />}
                </button>
              ))}
            </div>
            <div className="settings-title">画面偏好</div>
            <RadioGroup
              value={quality}
              onValueChange={(v) => changeQuality(v as Quality)}
              className="quality-options"
            >
              {[
                ['auto', '自动', '根据屏幕与运行表现调节'],
                ['fine', '精细', '完整植被、阴影与近景细节'],
                ['smooth', '流畅', '降低植被密度与渲染分辨率'],
              ].map(([q, name, desc]) => (
                <label key={q} htmlFor={`quality-${q}`}>
                  <RadioGroupItem
                    id={`quality-${q}`}
                    value={q}
                    aria-label={name}
                  />
                  <span>
                    <strong>{name}</strong>
                    <small>{desc}</small>
                  </span>
                </label>
              ))}
            </RadioGroup>
            <p className="settings-note">
              光照为氛围模拟。复原比例保持一致，资料缺失处已注明推定。
            </p>
          </TabsContent>
        </Tabs>
        <div className="panel-foot">
          <span className="live-dot" />
          地图快照{' '}
          {overview?.snapshotAt.slice(0, 10).replaceAll('-', '.') ??
            '2026.09.09'}
          <button onClick={() => setAbout(true)} title="查看数据来源">
            <Info size={14} />
          </button>
        </div>
      </aside>
      <div className="map-tools" aria-label="视角控制">
        <button
          className="north-button"
          onClick={() => view('north')}
          title="正北朝向"
        >
          <Navigation size={20} />
          <span>N</span>
        </button>
        <div className="tool-stack">
          <button onClick={() => view('zoomIn')} title="放大">
            <Plus size={19} />
          </button>
          <button onClick={() => view('zoomOut')} title="缩小">
            <Minus size={19} />
          </button>
        </div>
        <div className="tool-stack">
          <button onClick={() => view('top')} title="俯视校园">
            <Layers3 size={18} />
          </button>
          <button onClick={() => view('tilt')} title="倾斜鸟瞰">
            <Compass size={18} />
          </button>
          <button onClick={() => view('overview')} title="全景复位">
            <RotateCcw size={18} />
          </button>
          <button
            title="全屏"
            onClick={() => {
              if (!document.fullscreenEnabled) {
                notify('当前浏览器不支持全屏，可使用横屏浏览。');
                return;
              }
              const action = document.fullscreenElement
                ? document.exitFullscreen()
                : document.documentElement.requestFullscreen();
              void action.catch(() =>
                notify('当前浏览器不支持全屏，可使用横屏浏览。'),
              );
            }}
          >
            <Expand size={18} />
          </button>
          <button
            title="导出校园画面"
            disabled={!ready}
            onClick={() =>
              void controller.current
                ?.exportImage()
                .then(() => notify('校园画面已导出'))
                .catch(() => notify('导出失败，请重试。'))
            }
          >
            <Download size={18} />
          </button>
        </div>
      </div>
      {current && (
        <section
          className={`place-detail ${more ? 'expanded' : ''}`}
          aria-label="建筑详情"
        >
          <div className="detail-heading">
            <div>
              <div className="eyebrow">
                {currentLandmark ? 'CAMPUS LANDMARK' : 'CAMPUS BUILDING'}
              </div>
              <h2>{current.name}</h2>
            </div>
            <button
              className="icon-button"
              title="关闭建筑详情"
              onClick={() => {
                setSelected(null);
                setMore(false);
                controller.current?.clearSelection();
              }}
            >
              <X size={18} />
            </button>
          </div>
          <p>
            {currentLandmark?.description ??
              `${CATEGORY_NAMES[currentBuilding!.category]}建筑，位置依据公开地图。`}
          </p>
          <div className="detail-actions">
            <button onClick={() => setMore((v) => !v)} aria-expanded={more}>
              复原依据 <ChevronDown size={14} />
            </button>
            <button onClick={() => controller.current?.focus(selected!)}>
              查看近景 <ArrowRight size={14} />
            </button>
          </div>
          {more && (
            <div className="detail-evidence">
              <p>
                {currentLandmark?.detail ??
                  '保留公开地图轮廓，窗格、屋顶和入口按建筑类型推定。'}
              </p>
              {currentBuilding?.constructionStatus && (
                <p>{currentBuilding.constructionStatus}</p>
              )}
              <dl>
                <div>
                  <dt>高度依据</dt>
                  <dd>{currentBuilding?.heightBasis ?? '参考照片估算'}</dd>
                </div>
                <div>
                  <dt>地图编辑时间</dt>
                  <dd>{current.osmEditedAt?.slice(0, 10) ?? '详见位置来源'}</dd>
                </div>
              </dl>
              <a href={current.sourceUrl} target="_blank" rel="noreferrer">
                查看位置来源 <ArrowUpRight size={13} />
              </a>
              {currentLandmark && (
                <>
                  <a
                    href={refs[currentLandmark.reference]?.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {refs[currentLandmark.reference]?.name}{' '}
                    <ArrowUpRight size={13} />
                  </a>
                  <small>{refs[currentLandmark.reference]?.year}</small>
                </>
              )}
            </div>
          )}
        </section>
      )}
      <div className="tour-bar">
        <span className="tour-symbol">
          <Compass size={21} />
        </span>
        <div className="tour-copy">
          <strong>
            {tour
              ? '正在云游西大'
              : tourStarted
                ? '巡游已暂停'
                : '把校园，慢慢看一遍'}
          </strong>
          <small>
            {tourStarted
              ? `${String(tourIndex + 1).padStart(2, '0')} / 10 · ${landmarks[tourIndex]?.name}`
              : '10 处地标 · 自动导览'}
          </small>
        </div>
        <button
          className="tour-start"
          disabled={!ready}
          onClick={() => {
            setTourStarted(true);
            setTour((v) => !v);
          }}
        >
          {tour ? <Pause size={15} /> : <Play size={15} />}
          <span>{tour ? '暂停' : tourStarted ? '继续巡游' : '开始巡游'}</span>
        </button>
        <button
          className="tour-skip"
          title="上一站"
          disabled={!ready}
          onClick={() => jump(-1)}
        >
          <ChevronLeft size={17} />
        </button>
        <button
          className="tour-skip"
          title="下一站"
          disabled={!ready}
          onClick={() => jump(1)}
        >
          <ChevronRight size={17} />
        </button>
      </div>
      <footer className="map-footer">
        <span className="gesture-help">拖动旋转 · 右键平移 · 滚轮缩放</span>
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
          <span>{status}</span>
          {error && <button onClick={retry}>重试</button>}
        </div>
      )}
      {toast && (
        <output className="toast">
          <Check size={15} />
          {toast}
        </output>
      )}
      {debug && metrics && (
        <pre className="debug-metrics">{JSON.stringify(metrics, null, 2)}</pre>
      )}
      <Dialog open={about} onOpenChange={setAbout}>
        <DialogContent className="about-dialog">
          <DialogTitle>关于「西大 · 云游校园」</DialogTitle>
          <DialogDescription>
            广西大学主校区的三维建筑与地理环境复现。
          </DialogDescription>
          <div className="about-scroll">
            <p>
              以大学东路主校区为中心，涵盖东、西、北校园，以及校界外约 300
              米的周边街区。
            </p>
            <div className="about-stats">
              <span>
                <b>{overview?.campusBuildings ?? '—'}</b>校内建筑
              </span>
              <span>
                <b>10</b>独立地标
              </span>
              <span>
                <b>{overview?.trees ?? '—'}</b>示意树木
              </span>
            </div>
            <h3>地图与复原依据</h3>
            <p>
              OSM 快照：{overview?.snapshotAt.slice(0, 10)}
              。获取日期不代表所有要素都在当年更新。近期资料以 2024—2026
              年校方发布内容为优先，照片未注明拍摄日期时保留未知状态。
            </p>
            <p>
              建筑轮廓来自公开地图，{overview?.estimatedHeights ?? '部分'}{' '}
              处建筑高度按类型估算。重点地标依据照片独立建模；未被照片覆盖的立面、树位和植物种类包含推定。地形使用
              Mapzen / SRTM 历史高程，SRTM 采集于 2000 年，非近期校园测绘。
            </p>
            <div className="source-links">
              {Object.entries(refs)
                .filter(([k]) =>
                  ['campus2026', 'campus2024', 'campusGallery'].includes(k),
                )
                .map(([k, r]) => (
                  <a href={r.url} key={k} target="_blank" rel="noreferrer">
                    {r.name}
                    <ArrowUpRight size={14} />
                  </a>
                ))}
            </div>
            <h3>如何操作</h3>
            <p>
              鼠标左键旋转，右键平移，滚轮缩放；触屏单指旋转、双指平移与缩放。聚焦画面后可用方向键平移、加减键缩放、Home
              返回全景。手动操作会暂停巡游。
            </p>
            <h3>开源与许可</h3>
            <p>
              Three.js + Blender。代码 MIT，自制模型与材质 CC BY 4.0，OSM 数据
              ODbL。公开照片用于造型参考，未作为贴图再分发。
            </p>
            <a
              className="source-link"
              href="https://github.com/wcqqq1214/gxu-campus-3d"
              target="_blank"
              rel="noreferrer"
            >
              查看源代码、模型与完整说明 <ArrowUpRight size={14} />
            </a>
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
}
