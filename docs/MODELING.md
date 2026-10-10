# Blender 模型与重建

本页说明当前的源文件、构建与校验流程。数据来源、估算边界及坐标约定见 [DATA.md](DATA.md)，界面和加载行为见 [DESIGN.md](DESIGN.md)。

## 文件与版本控制

| 内容 | 保存位置与用途 |
| --- | --- |
| 可编辑模型 | 本地 `blender/gxu-campus.blend`，不纳入 Git；增量建模和源模型校验需要它。目前尚未提供 Release 下载。 |
| 建模规则与参数 | `blender/`、`scripts/`、`data/`，随代码版本管理。 |
| 网页资产 | `public/models/`、`public/data/`，网页直接使用，须成套更新。 |
| 参考资料、候选模型、临时输出 | `work/`，不纳入 Git。 |
| 验收记录和过程截图 | `docs/` 默认忽略，仅保留三份正式说明、README 展示图及五份校验输入；例外在 `.gitignore` 中列明。 |

网页开发和普通测试无需 `.blend`。本地源文件保留具名对象、材质、打包纹理以及 `featureId`、`landmark`、`sourceUrl` 属性；楼栋 ID 是关联模型、目录和拾取的稳定标识，不随显示名称变更。

开发、提交和推送使用 `dev`。主分支更新须另行取得授权。`dev` 已清除旧 Blender 源文件、过程截图和报告历史；主分支和本地恢复引用可能仍保存旧对象。不要把工作目录大小与完整 Git 对象库大小混为一谈。

## 网页开发和检查

使用 Node.js 22.13 或更高版本，CI 使用 Node.js 24。安装依赖后可直接使用仓库内的网页模型：

```sh
npm ci
npm run dev
npm run typecheck
npm run lint
npm test
npm run build:pages
```

`build:pages` 生成 `out/`，当前 CI 发布到 GitHub Pages；`PAGES_BASE_PATH` 可指定仓库子路径。`npm run preview` 默认在 4300 端口预览 `out/`。运行中的预览可能仍读取该目录，清理或重建前先确认使用情况。

## 数据和完整模型构建

数据处理使用 Python 3.12 和仓库内的依赖约束。模型构建需要 Blender（当前源文件记录为 5.2.2 LTS）以及提供 `jpegtran` 的 libjpeg-turbo。字体和自制纹理已包含在仓库中。

```sh
python3.12 -m venv work/venv
work/venv/bin/pip install -r scripts/requirements.txt -c scripts/constraints-geodata.txt
npm run data:restore
work/venv/bin/python scripts/prepare_geodata.py
npm run models:build
```

`blender` 需要位于 PATH，也可使用本机可执行文件的绝对路径。`data:restore` 使用已保存的 OSM 和高程快照；只有明确要更新底图时才运行 `scripts/fetch_geodata.py --refresh`。刷新后应同时核对来源日期、统计、稳定 ID 与模型。

完整构建会生成源文件及两档 GLB，但尚未验证能逐字节复现全部现有增量精修成果。更换 Blender、Draco 或几何依赖版本也可能改变导出结果。已有源文件和网页资产是增量修改的输入，不能无条件用一次全量重建覆盖。

数据依次处理建筑、最终道路、入口场地、铺地、岸段和植被；模型阶段先形成最终地形与场地，再生成树根高程并筛除实际树冠穿插。只跑数据准备不代表模型净空检查已完成。上下文哈希不匹配时应重新生成依赖，不手改指纹绕过检查。

## 几何与参数入口

| 对象 | 数据与实现 |
| --- | --- |
| 普通建筑 | `data/building-overrides.json` → `scripts/building_overrides.py` / `building_forms.py` → `blender/generic_buildings.py` |
| 独立地标 | `data/landmarks.json` 及专用建筑模块，如 `library.py`、`teaching_six.py`、`south_gate.py` |
| 道路与桥梁 | `scripts/infrastructure_data.py`、`campus_roads_data.py` → `blender/infrastructure.py`、`road_export.py` |
| 入口与铺地 | `data/site-overrides.json`、`paving-overrides.json` → `scripts/site_data.py`、`paving_data.py` |
| 岸段与局部基础 | `data/shore-overrides.json`、`foundation-overrides.json` → 对应数据和几何模块 |
| 植被与绿篱 | `data/vegetation-zones.json`、`vegetation-avenues.json`、`low-planting.json` → 植被准备及 `blender/tree_layout.py` |
| 南门字形与场地 | `blender/fonts/gxu-wordmark.json`、`data/south-gate-site.json`；维护入口为 `prepare_gate_wordmark.py`、`prepare_south_gate_site.py` |

普通楼主体、屋顶、入口和主要立面在基础与近景中共用形体，近景增加窗框等细构件。常用约束如下，完整取值和相交检查由相应解析器与测试定义：

- `parts` 必须覆盖原外环并保留内院；内部体量交界不生成默认窗。`floorHeights` 是逐层高度，不能用总高反推覆盖它。
- `parts.baseDepth` 仅用于封闭墙脚，默认 0.5 米，显式范围 0.5–2 米，不用于 `openBelow`；不改变楼底和主体顶高，也不是实测基础深度。
- `openBelow` 表达原轮廓内的开放底层；`entrances.attachedPortico` 表达外挑门廊。后者须有实体墙支撑，`parapetHeight: 0` 可关闭栏板，非零栏板仍需满足开孔尺寸约束。
- `facadeRules.part` 把规则限定到一个体量分段。`windowBands` 的 `firstLevel/lastLevel` 为零基索引且包含末层；窗带背后仍是实体墙，不能当成开放走廊。
- `openCorridor.lastLevel` 限定外廊或凹窗槽的楼层范围；窗带和面板不得侵入其完整楼板高度。工具名称不证明现实中的通行用途。
- `windows: false` 关闭默认窗列但不关闭显式 `panels`。`wallFinish` 直接改变墙面材质，不叠加重合面；`round-window-wall` 使用带孔墙面和后退玻璃，不生成室内。
- `exposedFacadeRules` 的 `above-roof` / `above-portico` 区域显式处理相邻低屋顶上方的墙面；`horizontalLedges`、显式窗和挑檐仍需检查相交。
- `roofVolumes`、`roofDome` 需要实体平屋面支撑并保留边界与内院净距；不自动计作新增楼层。`openBelow.slattedRoof` 使用透空梁顶，不叠加普通女儿墙。
- `courtyard-paving.stairConnection` 只连接有明确锚点的庭院边和楼梯底层，不自动推导远处道路路径。入口外扩前用 `scripts/audit_entry_road_context.py` 核对道路关系。

北校园的人工补绘体块与现有 OSM 建筑区分标注。普通平顶、未见背面、入口尺寸、景观与夜景均可能包含估算；具体来源和未知项随数据字段保存。

## 导出与增量修改

| 资源 | 内容 |
| --- | --- |
| `base.glb` | 地形、道路、水体、场地、基础建筑和地标体量 |
| `chunk-*.glb` | 普通建筑近景，加载后替换对应基础区块 |
| 地标与道路 GLB | 按目录和视距独立加载 |
| `trees.glb` / `trees-near.glb` | 远近景植物模板，网页按空间块实例化 |
| `public/data/models.json` | 资源 URL、大小、SHA256 和区块信息 |

模型采用 Draco 压缩，纹理嵌入 GLB，解码器本地托管。资源哈希参与网页 URL，更新 GLB 后必须同步清单。初始基础模型与树模板须满足 6,000,000 字节预算，实际值以清单和测试为准。

地形及普通道路使用共享量化范围；当前地形位置/UV 为18位，普通道路位置18位、普通UV12位、road材质UV10位，独立土木服务路保留专用编码。普通建筑和独立模型不因此统一改用同一精度。只去除严格零面积面和完全相同的重复载荷，保留有效几何、法线、材质与纹理像素。道路局部导出需要保留边界、垂直路缘和范围外网格。

`--base-only` 只适用于区块键不变且不需要同步近景的基础导出。几何或数据改变后，应同时更新本地源对象、基础节点、相关近景及清单，并核对无关资产未变。现有增量入口包括：

- `blender/update_south_gate.py`、`update_basketball.py`、`update_roads.py`：同步各自模型及相关场地。
- `blender/update_tree_layout.py`：同步树位和朝向；`-- --ground` 从最终地形更新树根高程。
- `blender/build_vegetation.py`：重导植物模板；模板几何改变时，仍须同步 `.blend` 源模型。
- `blender/repair_foundation_candidate.py`、`export_repaired_ground.py`：在独立候选中修补基础，再做局部导出与校验。

各入口的修改范围不同，调用前先阅读参数和脚本说明。先修改输入，在独立候选中验证，通过后才替换正式资产；保留仍用于对比的基准。网页只按实际发布的 GLB 验收，不能用截图代替几何、净空和性能检查。

已完成的一次性工具退出版本跟踪，本地副本与历史记录保留。`preview_civil_platform_west.py` 的西墙候选已集成到正式参数，不能再以当前模型作为修改前输入；`update_chongzuo_bridge.py` 的题名牌移除也已完成，不再用于日常更新。这两份原脚本可从提交 `b6215ab` 的 `blender/` 目录追溯；复现时需使用对应历史输入及独立输出，不能直接重跑到当前生产资产。

## 校验与基准

```sh
work/venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
npm test
npm run typecheck
npm run lint
```

Blender 专项校验必须提供本地源模型。常用入口为 `validate_generic.py`、`validate_landmarks.py`、`validate_terrain_texture.py`，以及对应楼栋校验；植物更新还需检查 `validate_tree_clearance.py`、`validate_site_tree_clearance.py`、`validate_vegetation.py`。模型检查通过不代表未见立面已获实景确认。

需要前后比较的数学研究中心、道路、铺地、岸段和侧向接路校验，必须显式提供基准，不再默认依赖旧实验目录。例如：

```sh
blender --background --python-exit-code 1 --python blender/validate_shore.py -- --baseline-root=/path/to/pre-shore-baseline --report-prefix=shore-check
blender --background --python-exit-code 1 --python blender/validate_civil_whole.py -- --road-baseline-root=/path/to/pre-road-baseline --connection-baseline-root=/path/to/pre-connection-baseline --report-prefix=civil-review
```

这些命令中的路径是占位符，需换成实际保留的、与该项检查语义一致的修改前版本。基准目录按项目结构包含 `blender/gxu-campus.blend`；铺地和岸段还需 `public/models/base.glb`。单项命令兼容原有 `--baseline=` 参数。土木整栋套件分别接受道路和接路基准，不强行共用一个历史阶段。

缺失基准时命令会停止并列出缺少的文件。不能用当前模型冒充修改前版本；旧 `.blend` 已删除的历史比较无法直接复跑，须有可靠基准后再做结论。校验不会因基准缺失而自动跳过。

浏览器检查脚本保留为可复用工具，使用 `PLAYWRIGHT_MODULE`、`CHROMIUM_PATH`、`REFINEMENT_URL` 等显式输入；前后截图工具还需相机列表与基准资源目录。输出只在本地保存。性能比较应使用同一视口、相机、前端和画质，区分资源加载、静止帧率及持续活动帧率。

`check-site-browser.mjs`、`check-paving-browser.mjs`、`check-shore-browser.mjs` 共用 `browser-check-helpers.mjs` 的面板导航、截图及报告流程，各自保留场地断言。可用 `REFINEMENT_CAMERAS` 指定相机列表；三个入口分别要求 `library-side`、`6b-paving-road-join`、`jinghu-auditorium-bank` 相机。省略时沿用本地历史相机文件，这些文件不随仓库发布，缺失时必须提供实际保留的输入。例如：

```sh
REFINEMENT_URL=http://127.0.0.1:4300/gxu-campus-3d/ REFINEMENT_CAMERAS=/path/to/paving-cameras.json node scripts/check-paving-browser.mjs paving-review
```

阶段名须唯一，已有报告不会被覆盖。当前前端检查使用“地点／图层／光影”和“返回地点列表”，画质检查会展开画质选项并返回原详情；`check-sports-batching-browser.mjs` 仅在修改前版本一侧兼容旧“探索”标签和“林木植被”开关，仍保留新旧前端对比能力。

界面与相机回归需要正在运行的 `npm run dev`，分别覆盖桌面和手机视口。使用开发服务器实际地址运行：

```sh
MENU_TEST_URL=http://127.0.0.1:3000/ node scripts/check-menu-interactions-browser.mjs
PANEL_TEST_URL=http://127.0.0.1:3000/ node scripts/check-panel-camera-browser.mjs
```

两项检查使用本地 Playwright 与 Chromium；未在项目安装 Playwright 时，将 `PLAYWRIGHT_MODULE` 指向可用模块的入口文件，`CHROMIUM_PATH` 指向浏览器可执行文件。它们不包含在 `npm test` 中；后者只运行 `scripts/test-*.mjs`。相机检查会在开发响应中注入观测代码，不能改用静态预览地址。

道路运行逻辑由 `lib/campus/road-batching.ts` 的 `batchStaticRoadSurfaces` 负责。原接缝合批实现保存在 `scripts/fixtures/legacy-road-batching.ts`，只供旧阶段的解码检查、回归测试与性能比较使用；历史比较不代表当前网页的完整加载顺序。
