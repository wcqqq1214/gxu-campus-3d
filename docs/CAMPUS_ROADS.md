# 校内主路与汇学堂前草地

本轮以已有 OSM 主路面为边界，统一使用崇左桥等下穿道路的 `asphalt` 沥青纹理、`curb` 浅色路缘和 `roadYellow` 中心虚线材质。共覆盖 53 段、约 17.48 公里的道路轴线；路幅保持原场景数据，不加宽。包括君武路、崇文路、博萃路、荟贤东路、蝶山路、碧云路等有名主路，以及地图标为住宅道路等类别的未命名干路。

范围按校内、同层道路筛选：residential、living_street、unclassified、tertiary、secondary、primary；排除 service、步道、台阶、广场和桥梁。长度是所选 OSM 轴线长度之和，不是对现实道路等级或精确里程的认定。路名、版本、编辑日期和来源保存在 `public/data/campus-roads.json`。

## 表面细节与衔接

- 同层主路铺面合并后分成互不重叠的沥青、浅色路缘和中心虚线，避免交叉口重叠闪烁。
- 路缘宽 0.28 米，位于原道路范围内；中心线宽 0.18 米、实段 3 米、周期 9 米。路口附近留白，支路接口不封口。这些为视觉估算，并非逐条道路现场标线复原。
- 几何复用实际地形三角面的贴地采样。保留桥梁、下穿坡道、农院路及近景 GLB；只替换主路铺面所在的基础 roads 节点。
- 原支路与主路相交的重叠片段由主路铺面统一覆盖；其余支路、小路的几何、材质与范围保持原样，不额外增加路灯、围栏或人行道。

## 汇学堂正东草地

按用户现场指正，以 OSM `way/822812174` 的草地轮廓清除草地内及树冠触及草地的示意树，共移除 61 株，保留草地和周边道路。剩余 3,034 株示意树；不改汇学堂建筑、朝向或入口模型。树位本身原本即为示意配置，不是树木实测数据。

`python3 scripts/campus_roads_data.py` 更新主路派生数据和树木掩膜，`blender --background --python-exit-code 1 --python blender/update_roads.py` 更新基础模型及可编辑道路、树木对象。完整数据与模型流程已接入。原 OSM、地形快照和参考照片许可不变。

## 桥下接口自然衔接（2026-09-11）

崇左桥、博萃桥、荟贤桥共六处下穿道路末端改为独立过渡铺面。原模型在固定 10 米车道和两侧步道末端直接接回较窄主路，侧路被路缘横挡，横断面高程与地形采样方式也不同，因此出现硬边。

- 保留桥洞与坡道中段，将末端约 15.8 米渐变接出。崇左桥、博萃桥沿原 OSM 校道再延续约 20 米收窄；荟贤桥两端直接并入既有丁字路口。位置和支路开口来自已有道路数据，过渡长度与断面为显示估算。
- 沥青使用同一米制纹理投影；车道、路缘和步道逐步匹配原地形与路幅，路口合并后不再横置路缘。末端护栏同步收尾，过渡区域暂不铺中心虚线。
- 三座桥的中段、梁板、桥台与桥上农院路维持原几何。新铺装与全部 448 栋建筑轮廓核对无交叠；原树位、精选目录和地理数据不变。
- 不同 GLB 网格独立压缩会产生毫米至厘米级边缘偏差，接口采用低于面层 0.12 米的窄下承层封住缝隙，不叠放同高路面。此构造用于可视化，不表示实际道路施工断面。

派生模块为 `scripts/bridge_joins_data.py`，由 `campus_roads_data.py` 自动调用；接口层和参数保存在 `campus-roads.json` 的 `bridgeJoins`。`blender/bridge_joins.py` 构建过渡面，`update_roads.py` 同步基础模型、三座桥的近景末端护栏和可编辑源文件。验证命令：

```sh
work/venv/bin/python scripts/test_bridge_joins.py
blender --background --python-exit-code 1 --python blender/validate_bridge_joins.py
blender --background --python-exit-code 1 --python blender/validate_infrastructure.py -- --no-render --joins
```
