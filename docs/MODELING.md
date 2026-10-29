# Blender 模型与重建

本页维护构建、增量修改与验收流程；来源和估算边界见 [DATA.md](DATA.md)，界面与加载行为见 [DESIGN.md](DESIGN.md)。具体尺寸和阈值以链接的配置、生成器及校验脚本为准，逐次修复记录保留在 Git 历史和本地验收资料中。

## 文件与版本控制

| 内容 | 位置与用途 |
| --- | --- |
| 可编辑模型 | 本地 `blender/gxu-campus.blend`，不纳入 Git，目前未提供 Release 下载；增量建模和源模型校验需要它，网页开发和普通测试不需要。 |
| 建模规则与参数 | `blender/`、`scripts/`、`data/`，随代码管理。 |
| 网页资产 | `public/models/`、`public/data/`，模型与清单须成套更新。 |
| 参考资料、候选、基准与归档 | `work/`，不纳入 Git。 |
| 文档与回归输入 | `docs/` 默认忽略，仅跟踪三份正式说明和 README 展示图；测试夹具在 `scripts/fixtures/`、`blender/fixtures/`。 |

源文件保留具名对象、材质、打包纹理及 `featureId`、`landmark`、`sourceUrl` 属性。楼栋 ID 关联模型、目录与拾取，不随显示名称变更。开发、提交、推送均使用 `dev`，完整规则见 [AGENTS.md](../AGENTS.md)。

## 网页开发和检查

Node.js 最低版本见 [package.json](../package.json)（当前为 22.13）；CI 使用 Node.js 24。

```sh
npm ci
npm run dev
npm run typecheck
npm run lint
npm test
npm run build:pages
```

`build:pages` 生成 `out/`，`PAGES_BASE_PATH` 可指定仓库子路径；`npm run preview` 默认在 4300 端口预览该目录。清理或重建前确认是否仍有预览使用它。`out/data/buildings.json` 只保留网页读取的字段，轮廓取整到厘米（`scripts/runtime-data.mjs`）；建模、校验和指纹始终以 `public/data/buildings.json` 的完整记录为准。前端 `Building` 类型增减字段时同步该清单，`test-runtime-data.mjs` 会检查两者一致。

`gh workflow run pages.yml --ref dev` 可运行 Linux 完整检查，包含 Blender 几何回归。非 `main` 分支使用 `/gxu-campus-3d` 前缀且跳过部署；只有 `main` 的非 PR 运行允许发布。依赖版本和检查顺序见 [pages.yml](../.github/workflows/pages.yml)；CI 安装 `libjpeg-turbo-progs`，确保需要 `jpegtran` 的回归不因缺少工具而跳过。

## 数据和完整模型构建

数据处理使用 Python 3.12 及仓库依赖约束；建模需要 Blender（当前源文件和 CI 使用 5.2.2）与提供 `jpegtran` 的 libjpeg-turbo。字体和自制纹理随仓库提供。

```sh
python3.12 -m venv work/venv
work/venv/bin/pip install -r scripts/requirements.txt -c scripts/constraints-geodata.txt
npm run data:restore
work/venv/bin/python scripts/prepare_geodata.py
npm run models:build
```

`blender` 须位于 PATH，也可用本机绝对路径执行对应脚本。全新重建必须先恢复快照，再准备数据并运行不带 `--base-only` 的完整构建；不能拿已生成的建筑数据代替首次构建验证。仅在明确更新底图时运行 `scripts/fetch_geodata.py --refresh`，随后核对来源日期、统计、稳定 ID 和模型。

完整构建生成源文件及两档 GLB，**尚未验证能逐字节复现全部现有增量精修成果**；工具版本变化也可能改变导出。保留现有源文件与资产，不无条件用全量重建覆盖。

数据依次准备建筑、最终道路、入口场地、铺地、岸段和植被；模型形成最终地形与场地后，才补树根高程并检查实际树冠净空。入口标高从本次地形采样，不能依赖旧 `buildings.json` 写回的 `elevation`；旧场地含 `buildingElevation` 时须重新准备。道路接台阶使用本次建筑标高，锚点指纹仍须匹配。

`npm run data:export` 是离线收尾步骤，完整数据准备也会调用：仅删除浏览器不使用的说明字段并迁移已验证的依赖指纹，不抓取数据或导出几何。说明仍保留在 `data/`；需要完整说明字段的增量脚本须从完整准备链运行。导出前核对铺装、岸线、基础和低矮绿化原始指纹，导出后按依赖顺序更新；道路接台阶的 `anchorRevision` / `surfaceRevision` 迁移也须核对完整与公开数据的几何一致性。轮廓、道路、方向、标高或台阶变化必须重建依赖，不能刷新指纹掩盖过期几何。可用 `python3 scripts/check-public-export.py <导出前提交>` 检查差异；首次准备、重复导出和过期输入由 `test_public_data_export.py`、`test_recessed_entry_site_data.py`、`test_road_landing_contract.py` 回归保护。

## 几何与参数入口

| 对象 | 数据与生成入口 | 主要校验入口（`blender/` 下） |
| --- | --- | --- |
| 普通建筑 | [building-overrides.json](../data/building-overrides.json) → `scripts/building_overrides.py` / `building_forms.py` → `blender/generic_buildings.py` | `validate_generic.py` |
| 独立地标 | [landmarks.json](../data/landmarks.json) 及 `blender/` 专用模块，如 `library.py`、`teaching_six.py`、`south_gate.py` | `validate_landmarks.py` 及对应地标专项 |
| 道路与桥梁 | `scripts/infrastructure_data.py`、`campus_roads_data.py` → `blender/infrastructure.py`、`road_export.py` | 对应道路专项与 `validate_civil_whole.py` |
| 入口与铺地 | [site-overrides.json](../data/site-overrides.json)、[paving-overrides.json](../data/paving-overrides.json) → `scripts/site_data.py`、`paving_data.py` | `validate_materials_entry.py`、`validate_courtyard_connection.py` |
| 岸段与局部基础 | [shore-overrides.json](../data/shore-overrides.json)、[foundation-overrides.json](../data/foundation-overrides.json) | `validate_shore.py`、`inspect_foundation_clearance.py`、`inspect_wall_ground_gaps.py` |
| 植被与绿篱 | `data/vegetation-zones.json`、`vegetation-avenues.json`、`low-planting.json` → 植被准备及 `blender/tree_layout.py` | `validate_tree_clearance.py`、`validate_site_tree_clearance.py`、`validate_vegetation.py` |
| 南门字形与场地 | `blender/fonts/gxu-wordmark.json`、`data/south-gate-site.json`；`scripts/prepare_gate_wordmark.py`、`prepare_south_gate_site.py` | 南门专项及入口场地检查 |

### 普通建筑与基础约束

源配置保存逐栋取值和依据，解析器与测试负责完整参数校验。维护时尤其注意：

- `parts` 覆盖原外环并保留内院；内部体量交界不生成默认窗。`floorHeights` 是逐层高度，不能用总高反推覆盖。`parts.baseDepth` 只封闭墙脚，不用于 `openBelow`，不改变楼底与主体顶高，也不是实测基础深度。
- `openBelow` 表示轮廓内开放底层；`entrances.attachedPortico` 是有实体墙支撑的外挑门廊，`parapetHeight: 0` 关闭栏板。`roofVolumes`、`roofDome` 需实体屋面支撑并保留边界及内院净距，不自动计作楼层；`openBelow.slattedRoof` 不叠加普通女儿墙。
- `facadeRules.part` 限定体量；`segment` 按原边方向选择不连续墙段，须指定 `part`，不能与同边同体量的整段规则混用，也不切分楼体。轮廓改变后重新核对索引。`windowBands.firstLevel/lastLevel` 为含末层的零基索引，背后仍是实体墙。
- `openCorridor.lastLevel` 限定外廊或凹槽范围，窗带与面板不得侵入其完整楼板高度。`windows: false` 不关闭显式 `panels`；`wallFinish` 直接换材质，不叠面；`round-window-wall` 使用带孔墙与后退玻璃，不生成室内。`exposedFacadeRules` 处理低屋顶或门廊上方外露墙面，仍须检查窗、挑檐和 `horizontalLedges` 相交。
- `courtyard-paving.stairConnection` 仅连接明确的庭院边与楼梯锚点。入口外扩前运行 `scripts/audit_entry_road_context.py`，不自动推导远处接路路径。
- `roadProtectionMargin` 改变后须重做准备并联验完整楼体、道路支承、范围外地形和邻楼。`preserveRoads: true` 输出空的道路裁切掩膜，核心及过渡退让道路保护区；记录主体与道路相交面积，不能把退让区算作已修复。
- `repairBounds` 限定局部矩形；`repairRegions` 合并多个矩形后一次生成过渡，两者不能同用。选区之外仍须采样整栋。庭院保护使用实际 `pavingPolygon` 和 `stairConnection.polygon`，含树池；不能用侵入楼翼的包围盒代替，其他场地仍保护 `gradingBounds`。
- 墙脚检查须覆盖开放外廊的实际楼板和退后墙；不能填实外廊来通过检查。局部修整不改原始 DEM，侵入诊断门槛不代表测绘精度。

### 道路与场地收边

[road-display-cleanup.json](../data/road-display-cleanup.json) 与 `scripts/road_display_cleanup.py` 在最终普通道路上同步裁切路面、辅路和路缘，不改 OSM 轴线及场地计算输入。[surface-display-cleanup.json](../data/surface-display-cleanup.json) 保存运动场地裁切。截面 ID、范围及保留探针以配置为准。

```sh
blender --background --python-exit-code 1 --python blender/update_road_display.py -- --output-dir=work/road-cleanup-candidate
blender --background --python-exit-code 1 --python blender/validate_road_display.py -- --baseline-root=/path/to/before --candidate-root=work/road-cleanup-candidate --report=work/road-cleanup-check.json
```

基准须含修改前的 `.blend` 与 `public/models/base.glb`。在已收边资产上继续裁切时，两个命令均以可重复的 `--cut-id` 指定本轮新增截面，避免重复处理；`removedProbe` 和 `retainedProbes` 分别保护移除及保留部分。更新依赖 Node.js 与仓库 Draco 解码器，沿用原量化范围，避免多次裁切导致未修改道路偏移。核对后成套更新 `.blend`、`base.glb` 与清单。

不规则截面使用逆时针凸多边形；带 `buildingId` 的掩膜须包含于封闭楼体，不侵占内院和开放门廊。校外截面保留校园口、地标及必要连接；路缘按三维面积裁切并插值 UV。场地裁切使用 `--layer=sports`，更新可用 `--input-root` 接续候选；只替换 `sport` 压缩网格，其余资源保持。

地形穿透由 [road-surface-clearance.json](../data/road-surface-clearance.json) 配置，`scripts/road_surface_clearance.py` 沿地形三角面拆分原路面，仅抬高不足净空，保留 UV 并补齐共享边顶点。完整构建自动应用；增量更新和校验均加 `--repair-clearance`。仅处理指定修复时，例如：

```sh
--repair-clearance --clearance-only --repair-id=yucai-plaza-north --repair-id=office-service-network
```

`--repair-id` 可重复，`--clearance-only` 跳过道路裁切；同材质范围不得重叠，抬升受 `maxLift` 限制。须比较旧穿透点、区域净空、边界标高与范围外保留，不用此法抹平有实景依据的台阶。`medical-plaza` 保留三处 `highway=steps`（`way/1501460955`、`way/1501460957`、`way/1501460959`）内及边界高程；现有简化坡面不代表平台已校准。

普通台阶的 `front-connection.roadSpan: [左端, 右端]` 以入口局部横轴米制坐标限定道路端宽度，保留台阶全宽；两端须在原宽度内、跨中轴并落在同一映射道路上。未配置则等宽，不适用于无台阶入口或阶梯建筑，不扩大道路。办公南楼西门（`way/759132930`）接服务路 `way/759628239` 时，须与 `office-service-network` 联验；梯形前场及标高仍是估算，不构成无障碍路线认定。

### 入口与地形衔接

| 区域 | 当前入口与必须保留的约束 |
| --- | --- |
| 资环材学院 | `recessedStairEntry`、`landscape.groundPatches` 保存入口和停车接路参数；`blender/entry_forecourt_geometry.py`、`entry_ground_bedding.py` 共用铺装与整地控制面，保留下沉庭院、真实挡墙及道路原覆盖范围。重新定位须重采地形与前后接路标高，不沿用旧值。 |
| 土木学院 | [civil-forecourt-grade.json](../data/civil-forecourt-grade.json) → `blender/civil_forecourt_grade.py`，在道路与连接面采样前统一切分土体、道路共边，再施加有界渐变；保留道路轮廓、附楼台阶、保护区及外边界。`contextPads` 在源模型与两档 GLB 共用落地标高，`edgePads` / `northTie` 接回邻楼和路口。 |

资环材验收覆盖完整楼体、三段台阶与下行梯、门厅和雨棚净空、铺装接地、停车前后缘、横坡、墙脚收边与内院留空。接路须采实际 `campus-roads.layers`，不能仅看已被覆盖的旧道路；南北停车区需联验回转车道。铺装与窄石材带共面分区并补齐共享边，不用叠面消除裂缝。土层和外缘过渡以准备后的铺装及本次地形为准，不依赖旧源文件的手工修补；仅此入口允许 2 毫米舍入容差，真正下挖与其他路径仍严格处理。完整场地参与植被排除，上下游指纹不匹配须重建依赖。

```sh
blender --background --python-exit-code 1 --python blender/validate_materials_entry.py -- --check-root=/path/to/candidate --report=/path/to/report.json
```

土木整坡须保护资环材停车及后缘过渡，不能把高差挤到两院交界。非线性渐变前补齐 T 形共边接点，避免长短边插值不同；消退道路多余悬高时，零权重保护区和外边界保持。验收使用 `validate_civil_grade.py`、`validate_civil_edges.py` 检查门前、外围断面、北侧车道、建筑落地及解码高度，不能只验门前平台。独立几何回归见 `test_civil_forecourt_grade.py`、`test_entry_ground_bedding.py`、`test_paving_roundoff.py`。

## 导出与增量修改

| 资源 | 内容 |
| --- | --- |
| `base.glb` | 地形、道路、水体、场地、基础建筑和地标体量 |
| `chunk-*.glb` | 普通建筑近景，加载后替换对应基础区块 |
| 地标与道路 GLB | 按目录与视距独立加载 |
| `basketball-bank-*.glb` | 完整篮圈与镂空篮网，近景替换基础球场 |
| `trees.glb` / `trees-near.glb` | 远近植物模板，网页按空间块实例化 |
| `public/data/models.json` | URL、大小、SHA256 与区块信息；哈希参与资源 URL |

模型采用 Draco，纹理嵌入 GLB，解码器本地托管。源对象、基础节点、相关近景和清单须同步更新，并核对无关资产未变。`--base-only` 仅用于区块键不变、无需同步普通建筑近景的基础导出；两档篮球场仍会更新。

初始 `base.glb + trees.glb` 的统一预算见 [initial-model-budget.json](../data/initial-model-budget.json)：实际文件合计超过 8,000,000 字节提醒，超过 10,000,000 字节阻止构建。完整、base-only 与增量入口均检查；JS、JSON、解码器另计，真实加载与交互性能须另外验证。

### 导出约束

- 普通建筑两档共用主体、屋顶、入口和主要立面；近景增加细部。墙脚等修改可能改变整块量化范围，须核对所在区块两档的实际解码几何，不能只比较局部源网格。
- 地形与普通道路采用共享位置量化范围，专用精度见 `blender/terrain_precision.py`、`road_export.py`、`terrain_export.py` 与 `build_campus.py`；不统一套用到普通建筑或独立模型。增量地形使用 `terrain_export.py --source=候选.blend --target=候选/base.glb`，只替换地形，避免覆盖道路修补。
- [terrain-export-regions.json](../data/terrain-export-regions.json) 可指定局部高精度范围。分区使用完整源面，接缝吸附外围实际解码坐标，解码差须小于 0.1 毫米；两个不重叠图元仍属同一地形节点，不是覆盖补丁。配置空缺时沿用单图元；新增范围须回归旧区域、外围与预算。
- 去重只合并全部顶点属性逐字节相同的载荷，保留 UV 接缝与硬边；仅移除严格零面积面。地形与道路近共面重三角化保留外边界、材质边界及空隙，最大平面误差 0.2 毫米，法线仍受原容差约束。`test_vertex_dedup.py`、`test_road_planar.py` 保护这些边界。
- `gltf_bounds.compact_glb_float_bounds` 仅缩短可还原同一 Float32 位模式的 accessor 边界 JSON；不改整数边界、压缩几何或纹理。回归见 `test_gltf_bounds.py`。
- 新东园门完整与增量出口共用 `blender/detail_export.py`，以足够的纹理坐标精度保护薄面板细砂比例；完整基础包只重打包该节点。`test_new_east_export.py` 解码基础、近景和增量出口并检查其余节点保留。英文字形由 `scripts/build_gate_latin_font.py` 生成，版权与 OFL 随字体保存，构建不依赖系统字体。
- 篮球基础档简化篮圈并省略镂空篮网，近景保留完整球场；两档位置与法线精度一致。`models.json` 的 `sports` 可选，旧清单兼容；加载失败或流畅档保留基础球场。`basketball_export.py --source=源文件.blend --candidate=候选目录` 仅用于尚含完整球场的旧基础包迁移，重复迁移已简化包会拒绝。迁移须联验解码、加载回退、图层/画质/距离切换与预算。

### 增量入口

脚本位于 `blender/`，按 `blender --background --python-exit-code 1 --python <脚本> -- <参数>` 调用；具体修改范围以各脚本说明为准。

| 入口 | 范围与调用方式 |
| --- | --- |
| `update_roads.py`、`update_basketball.py` | 独立候选中更新目标模型、相关地形与场地，验证后默认发布；传 `--output-root=/path/to/new-candidate` 只生成并校验候选。 |
| `update_new_east_gate.py` | 必须传 `--output-root=work/new-east-candidate`；加 `--publish` 才安装。`new_east_gate.py` 保留具名构件，`validate_new_east_gate.py` 验证源模型、两档解码、通道净空、接地与围合；相机回归另验桌面、竖屏及横屏构图。 |
| `update_new_east_neighbours.py` | 同样要求新 `--output-root`，加 `--publish` 才安装。`new_east_neighbours.py` 细化三栋邻楼及两侧沿街立面，保留主体、屋顶、入口和地图数据；只重导共享区块，并以 `validate_generic.py` 联验区块所有楼体、店面碰撞及铺装接地。 |
| `update_south_gate.py` | 同步南门与相关场地，运行前阅读脚本输入和覆盖范围。 |
| `update_tree_layout.py`、`build_vegetation.py` | 前者同步树位与朝向，`--ground` 从最终地形更新树根高程；后者重导模板，模板变化仍须同步源模型。 |

新东园门及邻楼的形制、未见面和商铺估算范围统一见 [DATA.md](DATA.md#校门与邻楼)，不在这里重复逐构件尺寸。道路、篮球、新东园门及邻楼的候选目录必须不存在；保留修改前基准直到比较完成。

### 发布与恢复

道路、篮球、新东园门及邻楼入口共用 [incremental_update.py](../blender/incremental_update.py)：先复制已发布资产与源文件，再构建、校验，最后成套安装。基础包仅拼入目标节点，无关压缩载荷、访问器、材质、纹理、变换和附加属性保留；对应源对象保留、实际解码、哈希与预算检查失败时只留下候选和日志。

复制与发布使用 `work/.incremental-publish.lock`（macOS/Linux `flock`），构建和校验期间释放锁。**不要删除长期保留的锁文件。** 发布锁覆盖基线检查、备份、替换和回滚；等待者取得锁后，以及备份、逐文件替换与整批替换完成时均重新核对哈希。不遵守锁的工具仍须避免同时写资产：哈希检查不能消除所有竞争窗口，多文件发布也不是读者可见的原子切换，不提供断电持久性保证。

每次替换先记录尝试项，SIGINT 后也按实际哈希逐文件回滚；恢复单项失败不阻断其余项。备份通过副本恢复，已被外部再次修改的文件保留并报告冲突。清理备份前须确认原文件恢复、新增文件删除；否则原始备份和 `recovery.json` 留在报错指定的 `work/gxu-publish-*`，后续复制与发布拒绝继续，记录写入失败也不删除最初记录或备份。

恢复时先停止其他写入者，按记录中的原始/候选哈希、备份路径和失败项恢复一致资产集，再将整个恢复目录移出扫描范围保留归档，才能重试。进程异常退出遗留记录也按此处理，不能直接删记录绕过阻拦。

```sh
npm run test:incremental -- --output-root=/path/to/new-regression-directory
# 仅新东园门，含当前模型重复生成
npm run test:incremental -- --output-root=/path/to/new-gate-regression --kinds new_east_gate
```

回归从当前 `public/` 和本地 `.blend` 分别运行道路、篮球、新东园门入口，检查正式输入及无关资源引用保持。需要 Blender、Node.js 在 PATH，也可设 `BLENDER_BIN`、`NODE_BIN`；输出目录须不存在。`test:data` 包含节点保留、损坏检测和失败不发布回归；`scripts/test_incremental_publication.py` 另验外部修改、竞争发布、持锁回滚及恢复失败。

## 校验与基准

网页检查见[网页开发和检查](#网页开发和检查)，数据与几何回归另运行：

```sh
work/venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
npm run test:geometry
# Blender 不在 PATH 时：
BLENDER_BIN=/path/to/blender npm run test:geometry
```

`test:geometry` 在独立 factory 环境运行每份 `blender/test_*.py`，禁用自动执行，异常返回非零；只依赖 Blender 内置 Python，不打开本地源模型或写发布资产。CI 运行同一入口。它保护生成规则，**不能代替当前发布 GLB 的实际解码验收**，截图也不能代替几何、净空或性能检查。

按修改范围运行参数入口表中的专项：普通建筑源模型用世界坐标比较；整栋检查包含地形/道路侵入和墙脚接触，不能只验立面与屋顶。`inspect_foundation_clearance.py --root=/path/to/candidate --building-id=... --report=/path/to/report.json --fail-on-intrusion` 可检查隔离候选；地形贴图使用 `validate_terrain_texture.py`。基础历史网格由 `fixtures/civil-foundation-boundary.json` 回归，外廊、篮球 LOD 与墙脚接触也有独立几何测试；校验通过不提高未见立面的实景证据等级。

数学研究中心、道路、铺地、岸段和侧向接路等前后比较必须显式提供语义正确的修改前基准：

```sh
blender --background --python-exit-code 1 --python blender/validate_shore.py -- --baseline-root=/path/to/pre-shore-baseline --report-prefix=shore-check
blender --background --python-exit-code 1 --python blender/validate_civil_whole.py -- --road-baseline-root=/path/to/pre-road-baseline --connection-baseline-root=/path/to/pre-connection-baseline --report-prefix=civil-review
```

基准按项目结构含 `.blend`，铺地与岸段还需 `public/models/base.glb`；单项兼容 `--baseline=`，土木套件分别接受道路和接路基准。缺失时停止，不自动跳过，也不能用当前模型冒充；旧源文件已删除的比较须取得可靠基准后再做结论。

### 浏览器与性能

检查脚本使用 `PLAYWRIGHT_MODULE`、`CHROMIUM_PATH`、`REFINEMENT_URL` 等显式输入，输出仅保存在本地。阶段名和报告路径须唯一，已有报告不覆盖。

```sh
MENU_TEST_URL=http://127.0.0.1:3000/ node scripts/check-menu-interactions-browser.mjs
PANEL_TEST_URL=http://127.0.0.1:3000/ node scripts/check-panel-camera-browser.mjs
```

两项覆盖桌面和手机，需运行中的开发服务器；相机检查在开发响应中注入观测代码，不能改用静态预览。它们不包含在 `npm test`（只运行 `scripts/test-*.mjs`）中。修改可访问名称时同步中英文与这些脚本。

`check-site-browser.mjs`、`check-paving-browser.mjs`、`check-shore-browser.mjs` 共用导航与报告工具，但保留各自断言，分别要求 `library-side`、`6b-paving-road-join`、`jinghu-auditorium-bank` 相机。通过 `REFINEMENT_CAMERAS` 指定列表，不能假定仓库包含默认历史相机文件；前后截图还需实际基准资产。

```sh
REFINEMENT_URL=http://127.0.0.1:4300/gxu-campus-3d/ REFINEMENT_CAMERAS=/path/to/paving-cameras.json node scripts/check-paving-browser.mjs paving-review
BASELINE_URL=http://127.0.0.1:4432/gxu-campus-3d/ REFINEMENT_URL=http://127.0.0.1:4430/gxu-campus-3d/ PERFORMANCE_REPORT=work/performance-check.json node scripts/check-campus-performance.mjs
```

性能对照须同一视口、相机、画质和构建后的前端，仅替换模型与清单，脚本核对实际 JS 哈希。区分加载、静止与持续活动帧率；固定镜头按真实经过时间运动，三组交替采样后比较中位数，不按 FPS 剔除失败轮次。采样发布由 `MutationObserver` 保存，外部读取延迟不丢窗口；页面自身缺号、超过 200 毫秒迟到或超过 0.03 弧度配对误差仍失败，失败报告保留原因与已完成轮次。采集链由 `scripts/check-benchmark-capture.mjs` 的真实浏览器夹具验证。

### 历史复现

退役候选工具不用于当前资产，恢复时必须配套历史输入与独立输出：`preview_civil_platform_west.py`、`update_chongzuo_bridge.py` 见提交 `b6215ab`；旧土木门廊候选见 `3004b87` 及本地 `work/archive/2026-10-14-modeling-cleanup-3004b87/`；旧道路合批比较见 `e927d0f`。当前运行逻辑为 `lib/campus/road-batching.ts`，由 `scripts/test-static-road-batching.mjs` 回归；跨前端的球场比较仍由 `check-sports-batching-browser.mjs` 兼容旧标签。

可清理退役脚本和缓存，但保留正式源模型、现用脚本、纹理及仍用于比较的基准。本地归档与移出版本跟踪不等于删除 Git 历史对象。

## 四地标联合增量验收

独立候选若来自同一基线，不能逐份覆盖整个 base.glb。按目标节点合并地标；独立水塔须同时更新所属 chunk-p0-p0 近景和基础节点。合并数据按稳定 ID 处理，随后重新生成地基依赖并核对实际几何，不能只刷新指纹。

`blender/validate_landmark_refinements.py` 需要本地源文件，比较汇学堂、综合实验大楼、活动中心、西门生成器与可编辑网格及实际解码的两档 GLB。独立水塔另外运行 `blender/validate_generic.py -- --chunk=chunk-p0-p0`，保护分块内其他37栋。`npm run test:geometry` 自动发现各地标双 LOD 回归，不需要本地 blend。数据测试中的证据断言从 data/ 源配置读取，不能依赖公开导出时移除的 evidence 字段。
