# Blender 模型与重建

本页记录模型的目录组织、网页与资产构建命令、几何约束及回归验收流程。数据来源与估算边界见 [DATA.md](DATA.md)，前端界面与渲染规范见 [DESIGN.md](DESIGN.md)。具体尺寸和阈值以配置文件、生成器及校验脚本为准。

## 文件与版本控制

| 内容 | 位置与用途 |
| --- | --- |
| 可编辑源模型 | 本地 `blender/gxu-campus.blend`（不纳入 Git，未提供 Release 下载）。仅增量建模或核验源模型时需要，网页开发与常规测试不依赖它。 |
| 建模规则与参数 | `blender/`、`scripts/`、`data/`，随代码库管理。 |
| 网页发布资产 | `public/models/`、`public/data/`。模型与清单须成套更新；迭代候选留在 `work/`，验收确认后再一次性提交。 |
| 本地工作产物 | `work/`（不纳入 Git）。参考资料、候选模型、基准数据、截图报告和归档统一放在此处，不另建 `output/`、`outputs/` 等顶层目录。 |
| 文档与测试夹具 | `docs/` 默认忽略，仅跟踪三份正式说明与 README 配图；测试夹具存放于 `scripts/fixtures/`、`blender/fixtures/`。 |

源文件保留具名对象、材质、打包纹理及 `featureId`、`landmark`、`sourceUrl` 属性；建筑 ID 串联模型节点、目录索引与拾取，不随显示名称变化。开发、提交与推送均在 `dev` 分支进行，完整规范见 [AGENTS.md](../AGENTS.md)。

## 网页开发和检查

本地开发与 CI 统一使用 [.nvmrc](../.nvmrc) 指定的 Node.js 24（与 `package.json` 的 `engines` 一致；使用 nvm 可运行 `nvm install && nvm use`）：

```sh
npm ci
npm run dev
npm run check
npm run build:pages
```

### 前端结构与模块化约定

网页采用 Vite + React 客户端单页架构（入口为 `index.html` → `app/main.tsx`）：

- `app/campus-map.tsx`：编排场景初始化、当前选中与面板状态。
- `components/campus-*.tsx`：承载地点列表、图层、光影、游览、分享与地图工具栏。
- `hooks/`：维护游览计时器与视口尺寸测量。
- `lib/campus/scene.ts`（`createScene`）按职责拆分子模块：
  - 交互与标注：`scene-pointer.ts`（拾取）、`scene-labels.ts`（地点标注）
  - 模型与资源：`scene-details.ts`（近景流式加载）、`scene-trees.ts`（树木）、`scene-base.ts`（解码与基础地形细化）、`scene-models.ts`（下载、样式与光照同步）
  - 画面与性能：`scene-effects.ts`（按需后处理）、`quality.ts`（画质与自动降档）、`camera.ts`（相机构图）、`frame-pacing.ts`（帧率统计）

新增场景能力时优先放入上述模块或新建同类模块，避免扩大 `createScene` 闭包。

### 静态构建与 CI 流程

- **静态导出与预览**：`npm run build:pages` 输出到 `out/`（可用 `PAGES_BASE_PATH` 指定子路径），`npm run preview` 默认在 `4300` 端口预览；清理或重编前请确认没有预览进程在使用 `out/`。`out/data/buildings.json` 仅保留前端字段并将轮廓取整到厘米（`scripts/runtime-data.mjs`），建模、校验和指纹仍以 `public/data/buildings.json` 为准；增减 `Building` 字段须同步该清单（由 `test-runtime-data.mjs` 保护）。
- **检查分级**：`npm run check` 依次执行类型检查、oxlint 与 JS/TS 测试，任一失败即退出（不依赖 Python、Blender 或 `.blend`）。完整检查另含 `npm run lint:python`、`npm run test:data`、`npm run test:geometry` 与 `npm run test:browser`。
- **持续集成**：向 `dev`、`main` 推送或向 `main` 提交 PR 时，CI 在 Linux 运行全套检查，也可运行 `gh workflow run pages.yml --ref dev` 手动触发。非 `main` 分支使用 `/gxu-campus-3d` 前缀构建且跳过部署；只有直接推送 `main` 且全部检查通过才会发布。流程定义见 [pages.yml](../.github/workflows/pages.yml)（CI 安装 `libjpeg-turbo-progs` 以运行依赖 `jpegtran` 的回归）。

### 浏览器回归

Playwright 版本锁定在 `package.json` 与锁文件中。首次运行或升级后需安装 Chromium（Linux 另需系统依赖，见 [Playwright CI 文档](https://playwright.dev/docs/ci-intro)）：

```sh
npx playwright install chromium
# Linux 环境：npx playwright install --with-deps chromium
npm run test:browser
```

`npm run test:browser` 先构建 Pages，再启动服务依次运行菜单、相机与 i18n 检查：
- **检查内容**：菜单与相机连接开发服务（相机探针仅注入测试响应）；i18n 使用 `out/` 静态产物并覆盖 `/gxu-campus-3d/` 子路径。视口覆盖 `1280px`、`390px`，i18n 另含 `320px` 及语言恢复、分享导出、存储受限与 WebGL 不可用场景。
- **端口与复用**：默认占用 `4317`、`4318` 端口（已被占用直接报错；可用 `BROWSER_DEV_PORT`、`BROWSER_PREVIEW_PORT` 调整），退出、失败或中断时自动清理子进程。支持 macOS/Linux；刚构建过且 `PAGES_BASE_PATH` 一致（空字符串或 `/gxu-campus-3d`）时，可用 `-- --skip-build` 复用产物。
- **输出与超时**：每次运行写入 `work/browser-checks/run-*`（含服务日志、断言输出、视口 trace 及未完成页面截图/控制台/网络日志；CI 失败上传保留 7 天），可用 `npx playwright show-trace <trace.zip>` 回放 DOM 与网络记录。单项超时 10 分钟，CI 浏览器步骤上限 25 分钟。
- **渲染与覆盖变量**：默认使用 [Chromium 新无头模式](https://playwright.dev/docs/browsers#chromium-new-headless-mode)（`channel: chromium`），本地用可用 GPU，CI 设 `SWIFTSHADER=1` 走软件渲染（本地可用同变量复测）。此入口仅作功能回归，不比较 GPU 性能；支持 `PLAYWRIGHT_MODULE`、`CHROMIUM_PATH`、`BROWSER_PATH`、`I18N_BROWSER=webkit`（需自装浏览器）及单脚本 URL 覆盖。

## 数据和完整模型构建

数据处理使用 [.python-version](../.python-version) 指定的 Python 3.12 及约束文件（补丁版本随 3.12 系列更新）。建模需要 Blender（源文件与 CI 使用 `5.2.2`）及提供 `jpegtran` 的 `libjpeg-turbo`（Blender 使用自带 Python）；字体与自制纹理随仓库提供。

```sh
python3.12 -m venv work/venv
work/venv/bin/pip install -r scripts/requirements.txt -c scripts/constraints-geodata.txt
npm run data:restore
work/venv/bin/python scripts/prepare_geodata.py
npm run models:build
```

### Python 静态检查

开发和 CI 使用 [requirements-dev.txt](../scripts/requirements-dev.txt)（含数据处理依赖及固定版本的 Ruff）。建议激活独立的 Python 3.12 环境后再跑检查，避免调用到系统旧版 Python：

```sh
python3.12 -m venv work/python-ci-venv
source work/python-ci-venv/bin/activate
python -m pip install -r scripts/requirements-dev.txt -c scripts/constraints-geodata.txt
npm run lint:python
npm run test:data
```

[pyproject.toml](../pyproject.toml) 将 Ruff 目标设为 `py312` 并锁定版本号，检查范围涵盖 `scripts/` 与 `blender/`（排除构建与本地目录）：
- 启用 `E9`、`F` 与 `I` 规则（不执行 Blender 也不依赖 `bpy`），导入按标准库、第三方、项目模块分组（`scripts/` 与 `blender/` 互导视为项目模块；转手导出须带说明性 `# noqa: F401`），详细规则见 [Ruff 文档](https://docs.astral.sh/ruff/rules/)。
- 格式统一使用 `ruff format`（单引号，行宽 88），修改后运行 `npm run format:python`；CI 会同步跑静态检查与 `ruff format --check`。批量格式化提交已记入 [.git-blame-ignore-revs](../.git-blame-ignore-revs)。

### 完整构建说明

执行建模需确保 `blender` 在 `PATH` 中（或直接用本机绝对路径）。全新重建须先恢复快照、准备数据，再运行不带 `--base-only` 的完整构建；仅在明确刷新底图时运行 `scripts/fetch_geodata.py --refresh`，并重新核对来源日期、统计、稳定 ID 与模型。

全量构建会生成源文件及两档 GLB，但**尚未验证能否逐字节复现全部历史增量精修成果**，且工具版本变化也会影响导出；请妥善保留现有源文件与资产，不要无条件覆写。

- **准备顺序**：依次准备建筑、最终道路、入口场地、铺地、岸段与植被；待地形和场地成型后再补采树根高程并检查树冠净空。入口标高从本次地形采样（旧场地含 `buildingElevation` 时须重跑准备）；道路接台阶采本次建筑标高，锚点指纹须匹配。
- **离线公开导出**：`npm run data:export`（完整准备链也会自动调用）仅删除前端不用的说明字段并迁移依赖指纹，不抓取数据或导出几何（完整说明保留在 `data/`，需要完整字段的增量脚本仍从完整准备链运行）。轮廓、道路、朝向、标高或台阶变更后须重建下游依赖，不能靠改指纹掩盖过期几何；可用 `python3 scripts/check-public-export.py <导出前提交>` 检查差异，契约由 `test_public_data_export.py`、`test_recessed_entry_site_data.py` 与 `test_road_landing_contract.py` 保护。

## 几何与参数入口

| 对象 | 数据与生成入口 | 主要校验入口（`blender/` 下） |
| --- | --- | --- |
| 普通建筑 | [building-overrides.json](../data/building-overrides.json) → `scripts/building_overrides.py` / `building_forms.py` → `blender/generic_buildings.py` | `validate_generic.py` |
| 独立地标 | [landmarks.json](../data/landmarks.json) 及 `blender/` 专用模块（如 `library.py`、`teaching_six.py`、`south_gate.py`） | `validate_landmarks.py` 及对应地标专项 |
| 道路与桥梁 | `scripts/infrastructure_data.py`、`campus_roads_data.py` → `blender/infrastructure.py`、`road_export.py` | 道路专项及 `validate_civil_whole.py` |
| 入口与铺地 | [site-overrides.json](../data/site-overrides.json)、[paving-overrides.json](../data/paving-overrides.json) → `scripts/site_data.py`、`paving_data.py` | `validate_materials_entry.py`、`validate_courtyard_connection.py` |
| 岸段与局部基础 | [shore-overrides.json](../data/shore-overrides.json)、[foundation-overrides.json](../data/foundation-overrides.json) | `validate_shore.py`、`inspect_foundation_clearance.py`、`inspect_wall_ground_gaps.py` |
| 植被与绿篱 | `data/vegetation-zones.json`、`vegetation-avenues.json`、`low-planting.json` → 植被准备及 `blender/tree_layout.py` | `validate_tree_clearance.py`、`validate_site_tree_clearance.py`、`validate_vegetation.py` |
| 南门字形与场地 | `blender/fonts/gxu-wordmark.json`、`data/south-gate-site.json`；`scripts/prepare_gate_wordmark.py`、`prepare_south_gate_site.py` | 南门专项及入口场地检查 |

### 普通建筑与基础约束

- **体量与层高**：`parts` 覆盖原外环并保留内院，内部交界不生成默认窗；`floorHeights` 为逐层高度，不能用总高反推覆盖；`parts.baseDepth` 只封闭墙脚，不用于 `openBelow`，不改变楼底与主体顶高。
- **架空与屋顶**：`openBelow` 表示轮廓内开放底层；`entrances.attachedPortico` 为带实体支撑墙的外挑门廊（`parapetHeight: 0` 关闭栏板）；`roofVolumes` 与 `roofDome` 须落在实体屋面上并留足边界与内院净距（不计作楼层）；`openBelow.slattedRoof` 不叠加普通女儿墙。
- **立面与外廊**：`facadeRules.part` 限定体量；`segment` 按原边方向选局部墙段（须指定 `part`，不与同边同体量的整段规则混用，不切分楼体；改轮廓后重对索引）。`windowBands.firstLevel/lastLevel` 为含末层的零基索引，背后保持实体墙；`openCorridor.lastLevel` 限定外廊/凹槽范围，窗带与面板不得侵入其楼板高度。`windows: false` 不关闭显式 `panels`；`wallFinish` 直接换材质；`round-window-wall` 使用带孔墙与后退玻璃（无室内）；`exposedFacadeRules` 处理门廊或低屋顶上方外露墙，仍须检查与窗、挑檐及 `horizontalLedges` 的相交。
- **庭院与道路保护**：`courtyard-paving.stairConnection` 仅连明确的庭院边与楼梯锚点；入口外扩前先运行 `scripts/audit_entry_road_context.py`，不自动推导远处接路路径。改 `roadProtectionMargin` 后须重做准备并联验完整楼体、道路支承、范围外地形与邻楼；`preserveRoads: true` 输出空裁切掩膜并退让保护区，须保留主体与道路相交面积统计，不把退让区算作已修复。
- **修整选区与墙脚**：`repairBounds` 限单个矩形，`repairRegions` 合并多矩形后统一生成过渡，两者不同用；选区外仍采样整栋。庭院保护采用含树池的实际 `pavingPolygon` 与 `stairConnection.polygon`（不用可能侵翼的包围盒），其他场地仍保护 `gradingBounds`。墙脚检查须覆盖开放外廊下的实际楼板和退后墙，不靠填实外廊绕过检查；所有局部修整均不改原始 DEM。

### 道路与场地收边

[road-display-cleanup.json](../data/road-display-cleanup.json) 与 `scripts/road_display_cleanup.py` 同步裁切普通道路的路面、辅路与路缘，不改 OSM 轴线和场地输入；[surface-display-cleanup.json](../data/surface-display-cleanup.json) 保存运动场地裁切：

```sh
blender --background --python-exit-code 1 --python blender/update_road_display.py -- --output-dir=work/road-cleanup-candidate
blender --background --python-exit-code 1 --python blender/validate_road_display.py -- --baseline-root=/path/to/before --candidate-root=work/road-cleanup-candidate --report=work/road-cleanup-check.json
```

- **增量裁切与多边形**：基线须含改动前 `.blend` 与 `public/models/base.glb`。在已收边资产上继续裁切时，生成与校验均用可重复的 `--cut-id` 指定新增截面；`removedProbe` 与 `retainedProbes` 分别保护移除与保留部分。更新依赖 Node.js 与本地 Draco 解码器，沿用原量化范围防漂移，确认后成套更新 `.blend`、`base.glb` 与清单。不规则截面用逆时针凸多边形；带 `buildingId` 掩膜须包含于封闭楼体（不占内院与门廊）；校外截面保留校园口、地标和必要连接，路缘按三维面积裁切并插值 UV。运动场地传 `--layer=sports`（可用 `--input-root` 接续候选，只换 `sport` 网格）。
- **地形穿透修复**：[road-surface-clearance.json](../data/road-surface-clearance.json) 配合 `scripts/road_surface_clearance.py` 沿地形三角面切分路面并抬升净空不足处（保留 UV 与共享边）。完整构建自动应用，增量入口加 `--repair-clearance`；仅跑指定修复时可配 `--clearance-only --repair-id=...`（如 `yucai-plaza-north`、`office-service-network`）。同材质范围不重叠，抬升受 `maxLift` 限制；须比对旧穿透点、净空、边界标高与范围外保留，不用此法抹平有依据的台阶（`medical-plaza` 保留 `way/1501460955`、`way/1501460957`、`way/1501460959` 内及边界高程）。
- **台阶接路**：`front-connection.roadSpan: [左端, 右端]` 按入口横轴米制坐标限定接路端宽度并保留台阶全宽，两端须落在原宽度内、跨中轴并位于同一映射道路上（缺省则等宽，不适用于无台阶入口/阶梯建筑，不扩宽道路）。办公南楼西门（`way/759132930`）接服务路 `way/759628239` 时须与 `office-service-network` 联验。

### 入口与地形衔接

| 区域 | 入口配置与保留约束 |
| --- | --- |
| 资环材学院 | `recessedStairEntry` 与 `landscape.groundPatches` 管理入口和停车接路；`blender/entry_forecourt_geometry.py`、`entry_ground_bedding.py` 共用铺装与整地控制面，保留下沉庭院、挡墙与道路覆盖范围。重新定位须重采地形与前后接路标高。 |
| 土木学院 | [civil-forecourt-grade.json](../data/civil-forecourt-grade.json) → `blender/civil_forecourt_grade.py`，在道路与连接面采样前切分土体和道路共边并施加有界渐变；保留道路轮廓、附楼台阶、保护区及外边界。`contextPads` 在源文件与两档 GLB 共用落地标高，`edgePads` / `northTie` 接回邻楼和路口。 |

- **资环材验收**：须覆盖完整楼体、三段台阶与下行梯、门厅和雨棚净空、铺装接地、停车前后缘、横坡、墙脚收边与内院留空；接路采实际 `campus-roads.layers`，南北停车区联验回转车道。铺装与窄石材带共面分区并补齐共享边（不叠面遮缝）；土层与外缘过渡以准备后铺装及本次地形为准，仅此入口允许 2 毫米舍入容差。完整场地同步参与植被排除，指纹不匹配须重建依赖。校验示例：

```sh
blender --background --python-exit-code 1 --python blender/validate_materials_entry.py -- --check-root=/path/to/candidate --report=/path/to/report.json
```

- **土木整坡验收**：保护资环材停车及后缘过渡（不把高差挤向两院交界），非线性渐变前补齐 T 形共边接点，消退多余悬高时保持零权重保护区与外边界。验收须联用 `validate_civil_grade.py` 与 `validate_civil_edges.py` 核对门前、外围断面、北侧车道、建筑落地与解码高度；独立测试见 `test_civil_forecourt_grade.py`、`test_entry_ground_bedding.py` 与 `test_paving_roundoff.py`。

## 导出与增量修改

| 资源 | 内容 |
| --- | --- |
| `base.glb` | 地形、道路、水体、场地、基础建筑和地标基础体量 |
| `chunk-*.glb` | 普通建筑近景分块，加载后替换对应基础区块 |
| 地标与道路 GLB | 按目录索引与视距单独流式加载 |
| `basketball-bank-*.glb` | 完整篮筐与镂空篮网，近景替换基础球场 |
| `trees.glb` / `trees-near.glb` | 远近植物模板，网页按空间块实例化 |
| `public/data/models.json` | 资源 URL、大小、SHA256 与区块信息（哈希参与地址） |

模型统一采用 Draco 压缩并内嵌纹理，解码器置于 `public/draco/`。发布须同步源对象、基础节点、相关近景与清单，并核对无关资产未变；`--base-only` 仅用于区块键不变时的基础包重导（两档篮球场仍同步更新）。

首屏模型 `base.glb + trees.glb` 的体积预算配置在 [initial-model-budget.json](../data/initial-model-budget.json) 中：合计超过 `8,000,000` 字节警告，超过 `10,000,000` 字节阻止构建（全量、`--base-only` 与增量入口均检查；JS、JSON 与解码器另计）。

### 导出约束

- **双档与量化**：普通建筑两档共用主体、屋顶、入口和主要立面（近景加细部）；墙脚改动可能改变区块量化包围盒，须核对所在区块两档的实际解码几何。地形与普通道路共用位置量化范围（见 `blender/terrain_precision.py`、`road_export.py`、`terrain_export.py`、`build_campus.py`）；单改地形可用 `terrain_export.py --source=候选.blend --target=候选/base.glb`。
- **高精度地形分区**：[terrain-export-regions.json](../data/terrain-export-regions.json) 可指定局部高精度范围；分区直接用完整源面，接缝吸附外围解码坐标且误差须小于 `0.1` 毫米（不重叠图元仍属同一地形节点；配置为空时退回单图元）。新增分区须回归旧区域、外围与预算。
- **去重、共面与边界**：顶点去重仅合并全部属性逐字节相同的载荷，保留 UV 接缝与硬边，仅移除严格零面积面；地形与道路近共面重三角化保留外边界、材质边界与空隙，最大平面误差 `0.2` 毫米（由 `test_vertex_dedup.py`、`test_road_planar.py` 保护）。`gltf_bounds.compact_glb_float_bounds` 仅缩短可无损还原 Float32 位模式的边界 JSON（见 `test_gltf_bounds.py`）。
- **专项资源**：新东园门完整与增量构建共用 `blender/detail_export.py` 以保留薄面板纹理坐标精度，`test_new_east_export.py` 检验基础、近景与增量产物中其余节点保留；英文字形由 `scripts/build_gate_latin_font.py` 生成（OFL 随字体保存，不依赖系统字体）。篮球基础档简化篮圈、省去镂空篮网并与近景保持相同精度；`models.json` 的 `sports` 可选，加载失败或流畅档回退基础球场；`basketball_export.py --source=源文件.blend --candidate=候选目录` 仅用于旧完整球场基础包迁移。

### 增量入口

脚本位于 `blender/`，按 `blender --background --python-exit-code 1 --python <脚本> -- <参数>` 调用；具体范围以各脚本说明为准。

| 入口 | 范围与调用方式 |
| --- | --- |
| `update_roads.py`、`update_basketball.py` | 在独立候选中更新目标模型、相关地形与场地，校验后默认发布；传 `--output-root=/path/to/new-candidate` 时只生成并校验候选。 |
| `update_new_east_gate.py` | 须传 `--output-root=work/new-east-candidate`，加 `--publish` 才安装。`new_east_gate.py` 保留具名构件，`validate_new_east_gate.py` 校验源模型、两档解码、通道净空、接地与围合（相机回归另验桌面、竖屏及横屏构图）。 |
| `update_new_east_neighbours.py` | 须传新 `--output-root`，加 `--publish` 才安装。细化三栋邻楼及沿街立面（保留主体、屋顶、入口与地图数据），仅重导共享区块并用 `validate_generic.py` 联验区块全部楼体、店面碰撞与铺装接地。 |
| `update_south_gate.py` | 同步南门及相关场地，运行前先核对输入与覆盖范围。 |
| `update_tree_layout.py`、`build_vegetation.py` | 前者同步树位与朝向（`--ground` 从最终地形采样高程）；后者重导模板（模板变化须同步源模型）。 |

新东园门及邻楼的外观形制与估算范围见 [DATA.md](DATA.md#校门与邻楼)。候选目录必须尚不存在；请保留改动前基准直到比较完成。若合并来自同一基线的多份独立地标候选，不可依次整包覆盖 `base.glb`，须按目标节点合并并同步更新地基依赖；其中大学生活动中心独立水塔还须同步更新所属 `chunk-p0-p0` 近景和基础节点。

### 发布与恢复

道路、篮球、新东园门与邻楼入口共用 [incremental_update.py](../blender/incremental_update.py)：复制已发布资产与源文件 → 构建校验 → 按目标节点拼入并成套替换安装（保留无关载荷、访问器、材质、纹理与属性；任一解码、哈希或预算检查失败则只保留候选和日志）。

- **发布锁**：复制与发布期间通过 `work/.incremental-publish.lock`（macOS/Linux `flock`）加锁，构建与校验时释放，**不要手动删除该锁文件**。等待者取得锁后以及备份、逐文件替换与整批完成时均复核哈希；仍须避免无锁工具并行写资产。
- **回滚与恢复**：替换前逐项记录状态，收到 `SIGINT` 时按实际哈希逐文件回滚；若替换后已被外部改动则保留并报冲突。确认原文件恢复、新增文件清除后才删备份；否则原始备份与 `recovery.json` 留在报错指定的 `work/gxu-publish-*` 目录并阻拦后续复制和发布。遇到异常遗留记录时，须先停掉其他写入者，按恢复目录中的哈希与备份手动还原一致资产集，再将该目录移出工作区归档，不可直接删除记录绕过检查。

```sh
npm run test:incremental -- --output-root=/path/to/new-regression-directory
# 仅测新东园门（含基于当前模型的重复生成）
npm run test:incremental -- --output-root=/path/to/new-gate-regression --kinds new_east_gate
```

回归需 `blender` 与 `node` 在 `PATH` 中（或设 `BLENDER_BIN`、`NODE_BIN`）且输出目录不存在；`test:data` 与 `scripts/test_incremental_publication.py` 覆盖节点保留、损坏拦截、外部篡改、并发竞争与恢复失败场景。

## 校验与基准

网页端检查见[网页开发和检查](#网页开发和检查)，Python 数据测试与独立几何回归如下：

```sh
work/venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
npm run test:geometry
# Blender 不在 PATH 时可指定：
BLENDER_BIN=/path/to/blender npm run test:geometry
```

`test:geometry` 在隔离的 factory 环境逐个运行 `blender/test_*.py`（仅用 Blender 内置 Python，不读本地 `.blend` 或写正式资产，自动发现地标双 LOD 回归）；但它主要保护生成规则，**不能替代对已发布 GLB 的实际解码验收**。

### 专项与前后对照

修改区域后请运行前文参数表中的专项脚本（普通建筑源模型按世界坐标比较，整栋检查需涵盖地形/道路侵入与墙脚贴合）。`inspect_foundation_clearance.py --root=/path/to/candidate --building-id=... --report=/path/to/report.json --fail-on-intrusion` 可检隔离候选；地形贴图用 `validate_terrain_texture.py`；基础历史边界由 `fixtures/civil-foundation-boundary.json` 回归。

针对汇学堂、综合实验大楼、大学生活动中心与西门等重点地标，可用 `blender/validate_landmark_refinements.py`（需本地 `.blend`）核对生成器、可编辑网格与两档解码 GLB；改动独立水塔时另需运行 `blender/validate_generic.py -- --chunk=chunk-p0-p0` 保护同分块内其余 37 栋普通建筑。

数学研究中心、道路、铺地、岸段与侧向接路的前后对比必须传入改动前基准（按项目结构含 `.blend`，铺地与岸段还需 `public/models/base.glb`；缺失时报错中止）：

```sh
blender --background --python-exit-code 1 --python blender/validate_shore.py -- --baseline-root=/path/to/pre-shore-baseline --report-prefix=shore-check
blender --background --python-exit-code 1 --python blender/validate_civil_whole.py -- --road-baseline-root=/path/to/pre-road-baseline --connection-baseline-root=/path/to/pre-connection-baseline --report-prefix=civil-review
```

### 浏览器与性能

专项浏览器脚本同样支持上述 Playwright 环境变量覆盖，输出仅存本地，阶段名与报告路径须唯一避免覆盖：

```sh
MENU_TEST_URL=http://127.0.0.1:3000/ node scripts/check-menu-interactions-browser.mjs
PANEL_TEST_URL=http://127.0.0.1:3000/ node scripts/check-panel-camera-browser.mjs
```

两项覆盖桌面和手机且需连接运行中的开发服务（未纳入 `npm test`）；改动可访问名称时须同步翻译与这些脚本中的定位器。`check-site-browser.mjs`、`check-paving-browser.mjs`、`check-shore-browser.mjs` 分别检验 `library-side`、`6b-paving-road-join`、`jinghu-auditorium-bank` 机位，需用 `REFINEMENT_CAMERAS` 传入相机清单：

```sh
REFINEMENT_URL=http://127.0.0.1:4300/gxu-campus-3d/ REFINEMENT_CAMERAS=/path/to/paving-cameras.json node scripts/check-paving-browser.mjs paving-review
BASELINE_URL=http://127.0.0.1:4432/gxu-campus-3d/ REFINEMENT_URL=http://127.0.0.1:4430/gxu-campus-3d/ PERFORMANCE_REPORT=work/performance-check.json node scripts/check-campus-performance.mjs
```

性能对照脚本 `check-campus-performance.mjs` 要求两端同视口、同相机、同画质与同构建前端（自动核对 JS 哈希），区分加载、静止与持续运动帧率；按真实耗时三组交替采样取中位数，由 `MutationObserver` 缓存在页面中，缺帧号、延迟超 `200` 毫秒或相位误差超 `0.03` 弧度即失败并保留已完成轮次（采集链路由 `scripts/check-benchmark-capture.mjs` 保护）。

### 历史复现

退役脚本不用于当前资产；如需复现早期方案，需配套对应历史输入与独立输出目录：`preview_civil_platform_west.py`、`update_chongzuo_bridge.py` 见 `b6215ab`；旧土木门廊见 `3004b87` 及本地 `work/archive/2026-10-14-modeling-cleanup-3004b87/`；旧道路合批比较见 `e927d0f`（当前合批实现在 `lib/campus/road-batching.ts`，由 `scripts/test-static-road-batching.mjs` 回归，跨版本球场比较见 `check-sports-batching-browser.mjs`）。
