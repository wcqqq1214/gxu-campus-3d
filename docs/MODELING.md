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

`npm run data:export` 是离线发布收尾步骤：从已准备的数据中移除浏览器不使用的说明字段，只迁移通过校验的基础、绿篱与映射雨棚指纹，不抓取网络数据、不重算几何或导出 GLB。完整 `data:prepare` 在生成链结束时执行同一步骤。可用 `python3 scripts/check-public-export.py <导出前提交>` 核对仅有说明字段移除和指纹迁移。说明与依据仍保留在 `data/` 源数据中；需要完整说明字段的数据增量脚本，应从完整数据准备链中运行。

道路接台阶的 `anchorRevision` 和 `surfaceRevision` 同样排除说明字段。农学院南门原指纹包含已从发布数据移除的 `basis`，曾导致发布数据不能通过后续建模校验；现按完整旧入口与发布入口的几何一致性核对后迁移。坐标、方向、标高、台阶或路面变化仍使校验失败，不能用刷新指纹代替核对几何。

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

周边道路的展示收边由 `data/road-display-cleanup.json` 配置，`scripts/road_display_cleanup.py` 在最终普通道路网格上同步裁切路面、辅路和路缘。该步骤不修改 OSM 轴线及场地计算使用的原始道路数据；完整建模也会应用同一组裁切。当前覆盖东北、西北、西南路口、南门东侧大学东路及新东门外秀灵路西一里的外伸尾段。火炬路、农院路、秀灵路西二里及校门连接保留。

增量更新生成独立候选目录，保留其他 GLB 节点和源场景对象。网页候选从已发布道路的解码网格裁切，并固定原有 18 位压缩坐标范围，以保留既有导出接缝修整；源文件单独应用相同裁切。以下基准目录须包含修改前的 `blender/gxu-campus.blend` 和 `public/models/base.glb`。核对几何和浏览器效果后，成套更新 `.blend`、`base.glb` 和 `models.json`。

```sh
blender --background --python-exit-code 1 --python blender/update_road_display.py -- --output-dir=work/road-cleanup-candidate
blender --background --python-exit-code 1 --python blender/validate_road_display.py -- --baseline-root=/path/to/before --candidate-root=work/road-cleanup-candidate --report=work/road-cleanup-check.json
```

在已经收边的模型上继续增量清理时，两个命令均用可重复的 `--cut-id` 指定本轮新增截面，例如 `--cut-id=xiuxiang-west --cut-id=daxue-east --cut-id=xiuling-west-first-east`。更新工具通过 Node.js 和仓库自带的 Draco 解码器读取原有量化范围，避免多次裁切后因范围缩小导致未修改道路偏移。每个截面的 `removedProbe` 验证旧尾段确实被移除，`retainedProbes` 验证路口和必要连接仍在。

南门西侧空地的环路、向北断头段及残余接头由 `southwest-empty-loop`、`southwest-dead-end`、`southwest-service-stub` 三个截面移除；不规则截面可使用逆时针凸多边形 `polygon`，保留沿街辅路及楼栋入口。大学东路—火炬路口的地形穿透修复另见 `data/road-surface-clearance.json`：`scripts/road_surface_clearance.py` 在实际地形三角面交界处拆分原路面，仅抬高净空不足的部分，保持原 UV，避免叠加补丁。完整建模自动应用；增量更新和校验命令均加 `--repair-clearance`，校验会比较修改前穿透点及修改后路面与地形的间距。

净空配置还支持按 `material` 分别选择 `asphalt`（默认）、`road` 和 `path`。育才广场北端与办公楼片区服务路分别使用 `yucai-plaza-north`、`office-service-network`；仅修复地形遮挡，不改变地图平面轮廓。相同材质的修复范围不得重叠；最大抬升受 `maxLift` 限制。拆分后补齐共享边顶点并插值原 UV，避免压缩在长边与细分边之间产生裂缝。保留原地形和建筑高度，不用此方法消除有真实台阶或平台依据的高差。

对于已完成其他修补的场景，更新和校验均附加以下参数，只处理本轮两个区域：

```sh
--repair-clearance --clearance-only --repair-id=yucai-plaza-north --repair-id=office-service-network
```

`--clearance-only` 跳过既有道路裁切；`--repair-id` 可重复。校验同时检查区域内净空、旧穿透点、修复边界与原路面的标高一致，以及范围外道路保留情况。办公楼片区仍须联验办公南楼入口连接。

医学院与研究生院之间前场使用 `medical-plaza`，增量调用时选择 `--repair-id=medical-plaza`。约244.37平方米原铺地获得局部净空修复，最大抬升1.089米；发布模型按原压缩网格独立修复，约242.06平方米、最大1.087米。

三处 `highway=steps` 标注范围（`way/1501460955`、`way/1501460957`、`way/1501460959`）内及边界的表面高度保持，源/发布模型最大差约0.000061/0.002396米。邻接0.25米外侧个别点原净空不足，局部抬高约0.029米；不把这些外侧点计为原标高保留。现有台阶标注仍以简化坡面表达，未新增踏步，也不视为现场平台高程或入口完成校准。建筑、地形和树位保持。

育才广场、办公楼片区及医学院前场均已通过本地性能复验：固定测量轨迹并复用未变化的太阳阴影后，原始S0与当前模型的精细/流畅两档共12轮通过原门槛。既有失败记录保留；几何、入口和模型指纹保持。冷缓存及实机手机仍另验。

土木学院北翼两个端部采用 `civil-north-west-overlap`、`civil-north-east-overlap` 裁切掩膜，限制在 `relation/12875606` 的既有封闭主体内，移除约33.2平方米穿楼普通路面和路缘。增量更新及比较校验均重复传入对应 `--cut-id`。源/基础整栋各1,023点的道路侵入从28点降为0，三种表示各238个墙脚位置通过；建筑、地形及楼外道路保持。裁切测试对带 `buildingId` 的内部掩膜检查闭合楼体包含关系，禁止侵占内院及开放门廊；其余校外截面沿用校园口、地标和校园重叠范围约束。竖直路缘按三维面积裁切，UV随新交点插值。

西侧空地标注的横支路、三角岔路和小水塘两侧细支路使用 `west-vacant-spur`、`west-pond-service-loop` 截面；水体保留。两组棕色场地面另由 `data/surface-display-cleanup.json` 配置，记录对应的三个原始场地 ID。完整建模在创建普通运动场源对象之前应用同一组裁切。增量更新及校验均支持 `--layer=sports`；更新可用 `--input-root` 接续上一阶段候选目录。场地更新只替换 `sport` 材质的压缩网格，沿用其原始坐标量化范围，其余材质与模型节点逐字节保留。

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

普通台阶的 `front-connection` 可显式配置 `roadSpan: [左端, 右端]`，单位米、坐标相对入口局部横轴。它保留台阶全宽，只在道路一端收窄；两端必须位于原台阶宽度内、跨过入口中轴，并落在同一已映射道路上。未配置时仍等宽连接；不适用于无台阶门口或阶梯建筑。该参数不能扩大道路轮廓，也不能代替前场实测边界。

办公南楼 `way/759132930` 西门采用此连接：24.7549米台阶接至 `way/759628239` 服务路，接路横向范围为 `[-11.7, 8.0]`，面积约82.66平方米。2025年寒假环卫简报的分析测试中心照片支持连续硬质前场；梯形边界、材质与标高为估算。原台阶底为3.35米，现有路面约3.94–4.01米，连接坡度约15%–19%，不是无障碍路线认定。门厅台阶已接通该段道路；片区服务路的地形遮挡另由 `office-service-network` 修复，完整前场仍需单独核对。建筑、其他近景模型及树位保持；本地源文件与基础模型同步更新。

已完成的一次性工具退出版本跟踪，可从历史记录追溯；本地退役脚本及 `__pycache__` 缓存可清理。正式源模型 `blender/gxu-campus.blend`、仍在使用的建模与校验脚本、纹理和对比基准须保留。`preview_civil_platform_west.py` 的西墙候选已集成到正式参数，不能再以当前模型作为修改前输入；`update_chongzuo_bridge.py` 的题名牌移除也已完成，不再用于日常更新。这两份原脚本可从提交 `b6215ab` 的 `blender/` 目录追溯；复现时需使用对应历史输入及独立输出，不能直接重跑到当前生产资产。

## 校验与基准

```sh
work/venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
npm test
npm run typecheck
npm run lint
```

Blender 专项校验必须提供本地源模型。`inspect_foundation_clearance.py --root=/path/to/candidate --building-id=... --report=/path/to/report.json --fail-on-intrusion` 可在隔离候选上检查完整闭合楼体的地形与普通道路侵入；`inspect_wall_ground_gaps.py` 另验实际墙脚接触。土木学院整栋套件已将两项检查接在既有23项建筑/入口专项后，不能仅凭立面与屋顶检查宣称接地通过。常用入口为 `validate_generic.py`、`validate_landmarks.py`、`validate_terrain_texture.py`，以及对应楼栋校验；植物更新还需检查 `validate_tree_clearance.py`、`validate_site_tree_clearance.py`、`validate_vegetation.py`。模型检查通过不代表未见立面已获实景确认。

需要前后比较的数学研究中心、道路、铺地、岸段和侧向接路校验，必须显式提供基准，不再默认依赖旧实验目录。例如：

```sh
blender --background --python-exit-code 1 --python blender/validate_shore.py -- --baseline-root=/path/to/pre-shore-baseline --report-prefix=shore-check
blender --background --python-exit-code 1 --python blender/validate_civil_whole.py -- --road-baseline-root=/path/to/pre-road-baseline --connection-baseline-root=/path/to/pre-connection-baseline --report-prefix=civil-review
```

这些命令中的路径是占位符，需换成实际保留的、与该项检查语义一致的修改前版本。基准目录按项目结构包含 `blender/gxu-campus.blend`；铺地和岸段还需 `public/models/base.glb`。单项命令兼容原有 `--baseline=` 参数。土木整栋套件分别接受道路和接路基准，不强行共用一个历史阶段。

缺失基准时命令会停止并列出缺少的文件。不能用当前模型冒充修改前版本；旧 `.blend` 已删除的历史比较无法直接复跑，须有可靠基准后再做结论。校验不会因基准缺失而自动跳过。

浏览器检查脚本保留为可复用工具，使用 `PLAYWRIGHT_MODULE`、`CHROMIUM_PATH`、`REFINEMENT_URL` 等显式输入；前后截图工具还需相机列表与基准资源目录。输出只在本地保存。性能比较应使用同一视口、相机、前端和画质，区分资源加载、静止帧率及持续活动帧率。

`check-campus-performance.mjs` 提供原始S0与当前模型的固定镜头活动对照。两个预览应使用**同一份构建后的前端**，只替换对应的模型与清单；脚本会核对实际响应的JS哈希。每档三组交替对照，各采21个1.5秒窗口，丢弃前两个预热窗口，再比较各轮中位数的中位数。不得按FPS筛掉失败轮次。

```sh
BASELINE_URL=http://127.0.0.1:4432/gxu-campus-3d/ REFINEMENT_URL=http://127.0.0.1:4430/gxu-campus-3d/ PERFORMANCE_REPORT=work/performance-check.json node scripts/check-campus-performance.mjs
```

同样可设置 `PLAYWRIGHT_MODULE` 和 `CHROMIUM_PATH`。报告路径须唯一；失败也写出原因和已完成轮次。`debug&benchmark=fixed-orbit` 模式按起始姿态和实际经过时间计算角度；普通游览保留原来的慢帧限幅。指标带 `sampleIndex` 和 `elapsedMs`，检查会拒绝漏采、超过200毫秒的窗口延迟或超过0.03弧度的配对偏差；失败时保留完整记录并排查原因。

阴影按变化刷新：`ShadowFrustum` 比较太阳方向、目标点和覆盖范围；仅环绕相机时复用既有阴影图。平移、缩放、光照切换、模型加载/释放、图层和树木LOD变化、画质切换及图形上下文恢复会触发更新。后续若加入移动的投影物体或修改几何，必须同时使 `renderer.shadowMap.needsUpdate` 生效，不能仅设置普通重绘标记。`shadowUpdates` 调试指标用于观察刷新次数。

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
