'use client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowUpRight,
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
import { CampusMinimap } from '@/components/campus-minimap';
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? '';
const LAYER_ITEMS: [LayerKey, string, string, typeof Building2][] = [
  ['buildings', '校园建筑', '教学楼、宿舍与校园地标', Building2],
  ['vegetation', '林木植被', '乔木、棕榈与林荫景观', Trees],
  ['roads', '道路与桥梁', '公共农院路、校道、桥梁与步行空间', Navigation],
  ['water', '湖塘水面', '镜湖、碧云湖及其他水体', Waves],
  ['sports', '运动场地', '球场、跑道与游泳池', GraduationCap],
  ['boundary', '校园边界', '灰绿色细线表示大致范围，农院路为公共道路', MapPin],
  ['context', '紧邻校界建筑', '仅保留贴近校界的周边建筑', Layers3],
  ['labels', '地点名称', '可点击的校园地标标注', MapPin],
];
const PRESETS: [Preset, string, typeof Sun][] = [
  ['morning', '晨光', Sunrise],
  ['day', '日间', Sun],
  ['evening', '黄昏', Sunset],
  ['night', '夜景', Moon],
];
const refs: Record<string, { name: string; url: string; year: string }> = {
  teachingSixEntrances2025: {
    name: '六教 · 校方南北门与两侧入口示意图',
    url: 'https://yjsc.gxu.edu.cn/info/1021/4254.htm',
    year: '发布于 2025-12-17；附件 3 入口位置关系',
  },
  teachingSixDesign: {
    name: '六教 · 华蓝设计项目说明与外观',
    url: 'https://www.gxhl.com/work/jianzhugongcheng/337.html',
    year: '2013 年设计、2016 年竣工；照片日期未知',
  },
  teachingTenGallery: {
    name: '第十教学楼 · 校方多媒体教学楼外观',
    url: 'https://www.gxu.edu.cn/info/1021/18800.htm',
    year: '发表及拍摄日期未知；外观参考',
  },
  teachingTen2024: {
    name: '第十教学楼 · 智慧教室调研记录',
    url: 'https://jwc.gxu.edu.cn/info/1222/3455.htm',
    year: '发布于 2024-10-08；用途与名称核对',
  },
  teachingTen2026: {
    name: '第十教学楼 · 2026 年校方面试公告',
    url: 'https://www.gxu.edu.cn/info/1364/40889.htm',
    year: '发布于 2026-06-09；用途与名称核对',
  },
  teachingTenClassrooms2022: {
    name: '第十教学楼 · A/B 座智慧教室建设公告',
    url: 'https://www.gxu.edu.cn/info/1006/29463.htm',
    year: '发布于 2022-06-24；用途与名称核对',
  },
  timeGate2025: {
    name: '时光之门 · 校方研学活动近景',
    url: 'https://cjxy.gxu.edu.cn/info/1041/1477.htm',
    year: '发布于 2025-03-21；拍摄日期未单独注明',
  },
  timeGateOverall2023: {
    name: '时光之门 · 2023 年地标导览转载全貌',
    url: 'https://www.sohu.com/a/718274615_121123989',
    year: '发布于 2023-09-06；拍摄日期未单独注明',
  },
  timeGateRoute2022: {
    name: '时光之门 · 外国语学院云游路线',
    url: 'https://fls.gxu.edu.cn/info/1205/4151.htm',
    year: '发布于 2022-07-14；拍摄日期未单独注明',
  },
  timeGateUse2026: {
    name: '时光之门 · 2026 年校友返校记录',
    url: 'https://gxulif.gxu.edu.cn/info/1527/12265.htm',
    year: '发布于 2026-07-27；拍摄日期未单独注明',
  },
  chongzuo2023: {
    name: '校方崇左桥下穿坡道与护栏照片',
    url: 'https://ghjjc.gxu.edu.cn/info/1046/2619.htm',
    year: '发布于 2023-06-27；单张拍摄日期未知。可见坡道、排水盖板和圆形护栏，未展示完整桥体',
  },
  bridgeFlowers2023: {
    name: '校方崇左桥、博萃桥附近围栏与三角梅',
    url: 'https://ghjjc.gxu.edu.cn/info/1057/2393.htm',
    year: '发布于 2023-03-30；拍摄日期未知。仅作为围栏和植物外观参考',
  },
  huixian2025: {
    name: '校方荟贤桥路段维护照片',
    url: 'https://ghjjc.gxu.edu.cn/info/1046/3774.htm',
    year: '发布于 2025-10-31；拍摄日期未知。可见道路铺装、盲道和路灯，桥洞形制未被完整覆盖',
  },
  bridgeMaintenance2024: {
    name: '校方农院路围墙周边绿化养护记录',
    url: 'https://ghjjc.gxu.edu.cn/info/1046/3085.htm',
    year: '发布于 2024-04-17；用于核对围墙存在，不提供精确边界',
  },
  chongzuoHistoric2013: {
    name: '崇左桥历史结构照片 · 2013',
    url: 'http://www.archina.com/index.php?a=show&g=ela&id=1336&m=index',
    year: '发布于 2013-04-16。只辅助桥洞及题名建模，不用于声称现状细部一致',
  },
  chongzuoReport2013: {
    name: '广西新闻网崇左桥现场报道',
    url: 'https://news.gxnews.com.cn/staticpages/20130416/newgx516c8136-7372321.shtml',
    year: '发布于 2013-04-16；正文明确农院路在上、校园通道在下，仅辅助核对空间关系',
  },
  chongzuoRoute2025: {
    name: '校方研学线路中的崇左桥',
    url: 'https://cjxy.gxu.edu.cn/info/1082/1384.htm',
    year: '发布于 2025-01-17；核对桥名与近期使用，不证明完整桥体外观',
  },
  bocuiNotice2023: {
    name: '校方博萃桥道路示意图',
    url: 'https://www.gxu.edu.cn/info/1365/32406.htm',
    year: '发布于 2023-01-18；核对图书馆南侧与农院路交叉位置。历史封闭通知不代表当前通行状态',
  },
  bridgeNamingGuide: {
    name: '校方捐赠指南中的荟贤桥位置',
    url: 'https://jjh.gxu.edu.cn/__local/A/1C/2D/C94DA67648AB9698A6BE04E1718_D3801DBD_2512297.pdf',
    year: '历史冠名资料，具体发布日期未知；荟贤桥位于新体育馆北侧的相对关系仅作位置辅助',
  },
  eastGatePhoto: {
    name: '东门落成实拍 · 中国教育在线（校方供图）',
    url: 'https://www.eol.cn/guangxi/xiaoyuandongtai/201812/t20181202_1635608.shtml',
    year: '发布于 2018-12-02，辅以无日期街景；2025 校方说明核对位置。未取得近年完整立面照片',
  },
  westGatePhoto: {
    name: '鲁班路西门入口街景',
    url: 'https://m.sgpabj.com/bendi/10373143.html',
    year: '照片拍摄日期未知；页面信息更新于 2026-01-16，2026 校方重开通知辅助核对位置',
  },
  newEast2026: {
    name: '校方新东门位置说明 · 秀灵西一里',
    url: 'https://www.gxu.edu.cn/info/1364/39930.htm',
    year: '发布于 2026-01-22；结合 2026 雅思入校导览定位。门体照片待补，外观为推定细化',
  },
  apartmentOfficial: {
    name: '校方留学生中心 · 公寓与裙楼外观',
    url: 'https://gjxy.gxu.edu.cn/lbt/xxss.htm',
    year: '当前首页链接的历史照片，拍摄日期未知；结合 2022 校方位置资料与 2024 住宿报道核对，未取得近期完整外立面照片',
  },
  westTrack2025: {
    name: '校方 2025 新生开学典礼 · 西田径场',
    url: 'https://news.gxu.edu.cn/info/1002/42983.htm',
    year: '发布于 2025-09-15 · 活动日 2025-09-15，单张照片拍摄时间未注明；另核对 2025 校运会照片',
  },
  eastTrack2026: {
    name: '校方 2026 阳光缤纷跑 · 东田径场',
    url: 'https://news.gxu.edu.cn/info/1002/43641.htm',
    year: '发布于 2026-04-26 · 单张照片拍摄时间未注明；跑道面层与白色分道线参考',
  },
  gate2026: {
    name: '2026 活动报道中的现南大门',
    url: 'https://www.5iidea.com/contents/47982',
    year: '发布于 2026-04-27 · 单张照片拍摄日期未注明；另以 2022 校方照片及 2024 日期水印照片交叉核对',
  },
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
  const r = await fetch(`${BASE}/data/${path}`, { cache: 'no-cache' });
  if (!r.ok) throw new Error(path);
  return r.json();
}
export default function Home() {
  const dock = useRef<HTMLElement>(null);
  const host = useRef<HTMLDivElement>(null),
    controller = useRef<SceneController | null>(null);
  const [buildings, setBuildings] = useState<Building[]>([]),
    [landmarks, setLandmarks] = useState<Landmark[]>([]),
    [overview, setOverview] = useState<Overview | null>(null);
  const [ready, setReady] = useState(false),
    [status, setStatus] = useState('正在铺开校园…'),
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
    [about, setAbout] = useState(false),
    [more, setMore] = useState(false),
    [toast, setToast] = useState(''),
    [retrySeed, setRetrySeed] = useState(0),
    [metrics, setMetrics] = useState<Metrics | null>(null);
  const [debug, setDebug] = useState(false);
  const [category, setCategory] = useState<Category | 'all'>('all');
  const [cameraState, setCameraState] = useState<CameraSnapshot | null>(null);
  const [shareLink, setShareLink] = useState('');
  const [panelMode, setPanelMode] = useState<'menu' | 'detail'>('menu');
  const [landmarkView, setLandmarkView] = useState<LandmarkView | null>(
    'oblique',
  );
  const [orbit, setOrbit] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
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
            onSelect: (id) => {
              if (active) {
                setSelected(id);
                setMore(false);
                setPanelMode(id ? 'detail' : 'menu');
                setLandmarkView('oblique');
                setCollapsed(false);
              }
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
          controller.current = c;
          const shared = decodeShare(
            location.hash,
            ls.map((l) => l.id),
          );
          if (shared) {
            c.restoreSnapshot(shared);
            if (shared.preset) setPreset(shared.preset);
            setLandmarkView(shared.view ?? null);
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
        if (key !== previous) {
          previous = key;
          controller.current?.setViewport(frame);
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
  }, [ready, collapsed]);
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
  const places = useMemo(
    () => searchLandmarks(landmarks, query, category),
    [landmarks, query, category],
  );
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
    setLandmarkView(null);
    controller.current?.view(v);
    if (v === 'overview') {
      setSelected(null);
      setCollapsed(false);
    }
  }
  async function shareView() {
    const snapshot = controller.current?.getSnapshot();
    if (!snapshot) return;
    const url = new URL(location.pathname, location.origin);
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
        ref={dock}
        className={`panel-dock ${collapsed ? 'collapsed' : ''}`}
        aria-label="校园探索菜单"
      >
        <div className="dock-heading">
          {panelMode === 'detail' && current && (
            <button
              className="dock-back"
              title="返回精选地标"
              onClick={() => setPanelMode('menu')}
            >
              <ChevronLeft size={18} />
            </button>
          )}
          <button
            className="dock-toggle"
            aria-expanded={!collapsed}
            aria-controls="campus-panel-body"
            onClick={() => setCollapsed((v) => !v)}
          >
            <span>
              {panelMode === 'detail' && current ? current.name : '校园探索'}
            </span>
            <small>{collapsed ? '展开' : '收起'}</small>
            <ChevronDown size={16} />
          </button>
        </div>
        <div id="campus-panel-body" className="dock-body" hidden={collapsed}>
          {panelMode === 'detail' && current ? (
            <section
              className={`place-detail ${more ? 'expanded' : ''}`}
              aria-label="建筑详情"
            >
              <div className="detail-heading">
                <div>
                  <div className="eyebrow">
                    {currentLandmark?.placeKind === 'sports'
                      ? 'CAMPUS ATHLETICS'
                      : currentLandmark
                        ? 'CAMPUS LANDMARK'
                        : 'CAMPUS BUILDING'}
                  </div>
                  <h2>{current.name}</h2>
                </div>
                <button
                  className="icon-button"
                  title="关闭建筑详情"
                  onClick={() => {
                    setSelected(null);
                    setMore(false);
                    setPanelMode('menu');
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
              {currentLandmark && (
                <fieldset className="landmark-views" aria-label="地标观察视角">
                  {(
                    [
                      ['oblique', '全貌'],
                      [
                        'front',
                        ['library', 'teaching-six'].includes(currentLandmark.id)
                          ? '南侧'
                          : '正面',
                      ],
                      [
                        'back',
                        ['library', 'teaching-six'].includes(currentLandmark.id)
                          ? '北侧'
                          : '背面',
                      ],
                      ['top', '俯视'],
                      [
                        'entrance',
                        ['library', 'teaching-six'].includes(currentLandmark.id)
                          ? '南门近景'
                          : currentLandmark?.placeKind === 'bridge'
                            ? '桥下近景'
                            : currentLandmark?.placeKind === 'sculpture'
                              ? '雕塑近景'
                              : '入口近景',
                      ],
                      ...(['library', 'teaching-six'].includes(
                        currentLandmark.id,
                      )
                        ? [['rear-entrance', '北门近景']]
                        : []),
                    ] as [LandmarkView, string][]
                  ).map(([value, label]) => (
                    <button
                      key={value}
                      aria-pressed={!orbit && landmarkView === value}
                      onClick={() => changeLandmarkView(value)}
                    >
                      {label}
                    </button>
                  ))}
                  <button
                    aria-pressed={orbit}
                    disabled={reducedMotion}
                    title={
                      reducedMotion
                        ? '系统已启用减少动态效果'
                        : '环绕当前地标，拖动画面可暂停'
                    }
                    onClick={() => {
                      setTour(false);
                      controller.current?.setOrbit(!orbit);
                    }}
                  >
                    {orbit ? <Pause size={14} /> : <RotateCcw size={14} />}{' '}
                    {orbit ? '暂停环绕' : '环绕观察'}
                  </button>
                </fieldset>
              )}
              <div className="detail-actions">
                <button onClick={() => setMore((v) => !v)} aria-expanded={more}>
                  复原依据 <ChevronDown size={14} />
                </button>
                <button onClick={() => void shareView()}>
                  <Share2 size={14} />
                  分享视角
                </button>
              </div>
              {more && (
                <div className="detail-evidence">
                  <p>
                    {currentLandmark?.detail ??
                      currentBuilding?.facadeBasis ??
                      '保留公开地图轮廓，窗格、屋顶和入口按建筑类型推定。'}
                  </p>
                  {currentBuilding?.constructionStatus && (
                    <p>{currentBuilding.constructionStatus}</p>
                  )}
                  <dl>
                    <div>
                      <dt>高度依据</dt>
                      <dd>
                        {currentLandmark?.placeKind === 'bridge'
                          ? '净高与坡度为视觉估算，非工程测量'
                          : currentLandmark?.placeKind === 'sports'
                            ? '历史 DEM 局部平整，非测量高程'
                            : currentLandmark?.id === 'new-east-gate'
                              ? '缺少门体照片，暂按门卫设施尺度估算'
                              : (currentBuilding?.heightBasis ??
                                '参考照片估算')}
                      </dd>
                    </div>
                    <div>
                      <dt>地图编辑时间</dt>
                      <dd>
                        {current.osmEditedAt?.slice(0, 10) ?? '详见位置来源'}
                      </dd>
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
                      {currentLandmark.additionalReferences
                        ?.filter((id) => refs[id])
                        .map((id) => (
                          <div key={id}>
                            <a
                              href={refs[id].url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {refs[id].name} <ArrowUpRight size={13} />
                            </a>
                            <small>{refs[id].year}</small>
                          </div>
                        ))}
                    </>
                  )}
                </div>
              )}
            </section>
          ) : (
            <div className="explorer">
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
                      placeholder="搜索地标，如图书馆、六教"
                      aria-label="搜索精选地标"
                    />
                    {query && (
                      <button title="清除搜索" onClick={() => setQuery('')}>
                        <X size={14} />
                      </button>
                    )}
                  </div>
                  <fieldset
                    className="category-filters"
                    aria-label="精选地标分类"
                  >
                    {(
                      [
                        ['all', '全部'],
                        ['academic', '教学'],
                        ['living', '生活'],
                        ['culture', '文体'],
                        ['landmark', '校门'],
                        ['infrastructure', '路桥'],
                      ] as [Category | 'all', string][]
                    ).map(([value, label]) => (
                      <button
                        key={value}
                        className={category === value ? 'active' : ''}
                        aria-pressed={category === value}
                        onClick={() => setCategory(value)}
                      >
                        {label}
                      </button>
                    ))}
                  </fieldset>
                  <div className="result-heading">
                    <span>{query ? '精选地标搜索结果' : '精选地标'}</span>
                    <span>{places.length} 处</span>
                  </div>
                  <div className="places">
                    {places.length ? (
                      places.map((p) => (
                        <button
                          key={p.id}
                          className={`place-row ${selected === p.id ? 'selected' : ''}`}
                          onClick={() => choose(p.id)}
                          disabled={!ready}
                        >
                          <span className="place-index">
                            {String(
                              landmarks.findIndex((l) => l.id === p.id) + 1,
                            ).padStart(2, '0')}
                          </span>
                          <span className="place-copy">
                            <strong>{p.name}</strong>
                            <small>
                              {CATEGORY_NAMES[p.category]}
                              {p.id === 'new-east-gate'
                                ? ' · 外观推定'
                                : ' · 重点复原'}
                            </small>
                          </span>
                          <ArrowUpRight size={16} />
                        </button>
                      ))
                    ) : (
                      <div className="empty-state">
                        没有找到对应精选地标。
                        <br />
                        试试“图书馆”“六教”，或切换到全部分类。
                      </div>
                    )}
                  </div>
                </TabsContent>
                <TabsContent value="layers" className="settings-content">
                  <p className="section-hint">选择你想看见的校园层次。</p>
                  {LAYER_ITEMS.map(([key, label, desc, Icon]) => (
                    <label
                      className="layer-row"
                      key={key}
                      htmlFor={`layer-${key}`}
                    >
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
              {current && (
                <button
                  className="return-landmark"
                  onClick={() => setPanelMode('detail')}
                >
                  返回 {current.name} <ArrowUpRight size={14} />
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
        <div className="tour-bar">
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
                ? `${String(tourIndex + 1).padStart(2, '0')} / ${landmarks.length} · ${landmarks[tourIndex]?.name}`
                : `${landmarks.length || '—'} 处精选地标 · 自动导览`}
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
      </aside>
      <div className="map-tools" aria-label="视角控制">
        <button
          className="north-button"
          onClick={() => view('north')}
          title="正北朝向"
        >
          <Navigation
            size={20}
            style={{
              transform: `rotate(${cameraBearing(cameraState) - 45}deg)`,
            }}
          />
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
            title="分享当前视角"
            disabled={!ready}
            onClick={() => void shareView()}
          >
            <Share2 size={18} />
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
      <footer className="map-footer">
        <span className="gesture-help">拖动旋转 · 右键平移 · 滚轮缩放</span>
        {layers.boundary && (
          <span className="boundary-legend">
            <i />
            校园大致边界
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
          <span>{status}</span>
          {loadProgress !== undefined && (
            <progress aria-label="模型加载进度" max={1} value={loadProgress} />
          )}
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
      <Dialog
        open={Boolean(shareLink)}
        onOpenChange={(open) => {
          if (!open) setShareLink('');
        }}
      >
        <DialogContent className="share-dialog">
          <DialogTitle>分享这个校园视角</DialogTitle>
          <DialogDescription>
            链接保留当前地标、镜头和光照，换一块屏幕也能继续浏览。
          </DialogDescription>
          <Input
            aria-label="校园视角链接"
            value={shareLink}
            readOnly
            onFocus={(event) => event.currentTarget.select()}
          />
          <p>复制上方链接即可分享。</p>
        </DialogContent>
      </Dialog>
      <Dialog open={about} onOpenChange={setAbout}>
        <DialogContent className="about-dialog">
          <DialogTitle>关于「西大 · 云游校园」</DialogTitle>
          <DialogDescription>
            广西大学主校区的三维建筑与地理环境复现。
          </DialogDescription>
          <div className="about-scroll">
            <p>
              以大学东路主校区为中心，涵盖东、西、北校园。校外建筑仅保留紧邻校界的部分，周边道路用于交代位置。
            </p>
            <div className="about-stats">
              <span>
                <b>{overview?.campusBuildings ?? '—'}</b>校内建筑
              </span>
              <span>
                <b>{landmarks.length || '—'}</b>精选地标
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
              农院路为贯穿校园区域的公共道路，两侧校园通过立交通道连接。道路与桥梁快照：
              {overview?.infrastructureSnapshotAt?.slice(0, 10)}；走廊约{' '}
              {((overview?.publicRoadMeters ?? 0) / 1000).toFixed(2)}{' '}
              千米。围墙、路幅及桥梁净高含估算，展示范围不代表权属或实际通行权限。
            </p>
            <p>
              建筑轮廓来自公开地图，{overview?.estimatedHeights ?? '部分'}{' '}
              处建筑高度按类型估算。重点地标依据照片独立建模；未被照片覆盖的立面、树位和植物种类包含推定。地形使用
              Mapzen / SRTM 历史高程，SRTM 采集于 2000 年，非近期校园测绘。
            </p>
            <div className="source-links">
              {Object.entries(refs)
                .filter(([k]) =>
                  [
                    'gate2026',
                    'campus2026',
                    'campus2024',
                    'campusGallery',
                    'apartmentOfficial',
                    'chongzuo2023',
                    'huixian2025',
                  ].includes(k),
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
              返回全景。手动操作会暂停巡游和环绕。地标详情可切换全貌、正面、背面、俯视与入口近景，图书馆和六教分别提供南北门，桥梁提供桥下近景。面板可收起，镜头会避开展开的面板。搜索支持“六教”“新东园门”“农院路”等别名，可按教学、生活、文体、校门和路桥筛选；地图标注和点击定位仅开放精选地标。灰绿色细线表示校园大致边界，可在图层中关闭，农院路公共走廊从校园范围中扣除。位置小图显示镜头方向，分享按钮可复制带光照与视角的链接。
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
