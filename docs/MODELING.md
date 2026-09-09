# Blender 模型与重建

源文件 `blender/gxu-campus.blend` 由 Blender 5.2.1 LTS 构建，使用米制坐标；建筑、树木与道路水体为具名对象，建筑带 `featureId` / `landmark` / `sourceUrl` 属性。材质与自制 JPEG 纹理均打包在 .blend 内，不需要额外下载摄影贴图。

## 可重复构建

网页运行只需要 npm；重新制作模型需要 Blender 和 Python 3.9+。

```sh
python3 -m venv work/venv
work/venv/bin/pip install -r scripts/requirements.txt
npm run data:restore
work/venv/bin/python scripts/prepare_geodata.py
npm run models:build
```

`blender` 必须位于 PATH，也可改用本机 Blender 可执行文件绝对路径。工作文件位于 `work/`，不纳入 Git。固定随机种子使植物配置和纹理一致；不同 Blender/Draco 版本可能改变二进制压缩结果。

数据流程：OSM JSON → Shapely 合并关系和内环 → 校园外扩 300 米裁剪 → Earcut 多边形三角化 → 米制地形、轮廓及 POI 目录 → Blender 几何 → 自包含 Draco GLB。`data:restore` 使用已发布快照；要更新数据，运行 `python3 scripts/fetch_geodata.py --refresh` 后重新准备和构建。

## 模型分级

| 资源 | 用途 |
| --- | --- |
| base.glb | 地形、路面、水体、绿地、运动场、周边建筑、带窗格的全校基础建筑和地标体量 |
| west / east / north.glb | 普通建筑近景，增加窗框、窗梃、阳台、入口雨棚、女儿墙等；加载后替换对应基础分区 |
| 10 个地标 GLB | 独立加载，可点选、巡游和单独修改；使用一致的米制位置 |
| trees.glb | 3 个多材质模板，网页合并为顶点色几何后分块实例化 |

模板材质包括石材、白色涂层、玻璃、深色金属、灰青屋瓦、铺装、草地、树皮和三种树冠色。9 张 128 × 128 自制 JPEG 纹理采用米制平面 UV；没有大尺寸摄影贴图。几何使用 Draco，解码器本地托管。东/西/北是场景加载分区，并不逐线等同于校方的行政分区。网页以视距触发普通分区近景，树木按空间块进行视锥剔除。精细和流畅档共用约 5 MB 基础资源，流畅档减少实例数量与渲染像素。

## 10 处地标检查

下面两个视角由实际 .blend 源文件渲染。用于检查几何、屋顶、入口和未见面的处理，不表示两张参考照片均覆盖每个面。全部模型为人工规则生成的外部建筑模型，没有室内重建。

| 地标 | 主要检查点及依据 | 视角 1 | 视角 2 |
| --- | --- | --- | --- |
| 南大门 | 2022 校方、2024 日期水印和 2026 活动照片：三跨石门、四门柱、弧形承托、叠檐、雕花嵌板、顶部小亭及红色立体校名；尺寸估算 | [查看](model-checks/south-gate-1.png) | [查看](model-checks/south-gate-2.png) |
| 图书馆 | 2026 图文正面及图库侧面：檐架、阶梯体量、入口柱廊；后部构造简化 | [查看](model-checks/library-1.png) | [查看](model-checks/library-2.png) |
| 汇学堂 | 2026 图文正面：灰青坡顶、木门、竖向柱廊；入口按用户确认转向东，背面推定 | [查看](model-checks/huixue-1.png) | [查看](model-checks/huixue-2.png) |
| 大礼堂 | 官方图库现状斜视：三角山花、六柱门廊、侧面窗列、台阶 | [查看](model-checks/auditorium-1.png) | [查看](model-checks/auditorium-2.png) |
| 综合体育馆 | 2021 官方视频 7 秒/12 秒：浅坡大屋盖、采光构件、百叶、柱墩；辅以 2024 场馆用途 | [查看](model-checks/stadium-1.png) | [查看](model-checks/stadium-2.png) |
| 大学生活动中心 | 2026 图文：曲线轮廓、白色水平带、深色玻璃；保留 OSM 内院 | [查看](model-checks/student-center-1.png) | [查看](model-checks/student-center-2.png) |
| 第六教学楼 | 官方图库：竖向窗列、平屋顶挑檐、雨棚、台阶；保留真实内院，未见面推定 | [查看](model-checks/teaching-six-1.png) | [查看](model-checks/teaching-six-2.png) |
| 第二教学楼 | OSM 轮廓、7 层标签及 2024 导览位置；立面主要按教学楼类型推定，未取得可确认的近期外观 | [查看](model-checks/teaching-two-1.png) | [查看](model-checks/teaching-two-2.png) |
| 综合实验大楼 | 校门与实验楼官方图库：双翼与中央上部桥体，底部通孔保持开放；后立面推定 | [查看](model-checks/laboratory-1.png) | [查看](model-checks/laboratory-2.png) |
| 计算机与电子信息学院 | 官方 PDF 第 1 页：竖向玻璃核心、粉色侧墙、窗列与悬挑平檐；背面及细节推定 | [查看](model-checks/computer-1.png) | [查看](model-checks/computer-2.png) |

重新生成视角：

```sh
blender --background --python-exit-code 1 --python blender/render_checks.py
```

维护时先修改 `data/landmarks.json` 的位置及来源，再修改 `blender/landmarks.py` 中对应造型。普通楼宇规则位于 `blender/build_campus.py`，几何组装器位于 `blender/geometry.py`。不要修改稳定 ID 来解决显示名称变化；模型、目录和拾取应保持一致。

## 南大门现状重建与汇学堂朝向修正（2026-09-09）

旧版误用了官方无日期图库中的旧南门柱列照片，现已完全替换为近期照片一致可见的三跨石门。现模型保留三处真实贯通门洞、四个分块石柱、弧形承托、叠层檐口、石雕嵌板、双排顶部小亭和横向红色校名。近景含门柱分缝、几何花纹、檐下纹饰、匾额嵌框及立体字；基础 LOD 保留相同现状轮廓与校名。门前花坛和矮栏按近期照片示意配置，不包含临时活动帐篷。

依据为 [2022 年校方毕业季第二张照片](https://news.gxu.edu.cn/info/1002/39575.htm)、[2024-10-10 日期水印现场照片](https://www.lun51.com/homepage/index.php?a=index&aid=1069&c=View&m=home)、[2026 年活动报道首图](https://www.5iidea.com/contents/47982)。2026 文章发布于 4 月 27 日、活动发生于 4 月 14 日，但单张门口照片的拍摄日未知。没有使用旧门照片恢复现门。

门的位置、宽度和进深绑定 OSM way/1492215424 门楼轮廓；门高及构件比例、未见背面为照片估算；雕花为几何近似，非扫描。校名使用 [Ma Shan Zheng](https://github.com/google/fonts/tree/main/ofl/mashanzheng) 开源书法字形替代原题字，不能称为原笔迹精确复刻。完整字体及 SIL OFL 许可位于 `blender/fonts/`；仅字形网格进入 GLB，网页不加载字体文件。

源模型南大门保留具名顶点组，方便分别编辑门柱、各门跨、匾额、校名和景观。规则位于 `blender/south_gate.py`。汇学堂先交换建模局部宽深再绕中心旋转 +90°，入口由南转东且主体仍适配原 OSM 边界框；导览镜头同步切换到东侧。朝向修正依据用户确认，不代表 OSM 数据在该日重新测量。

```sh
npm run models:build
blender --background --python-exit-code 1 --python blender/validate_landmarks.py
blender --background --python-exit-code 1 --python blender/render_checks.py -- south-gate huixue
```

几何检查直接读取保存后的 .blend：射线检查三门洞贯通、四门柱和三横梁存在，并检查汇学堂木门顶点位于东立面。结果见 [geometry-check.json](model-checks/geometry-check.json)。

现南门直接绑定 OSM `way/1492215424`（`building=gatehouse`、`man_made=ceremonial_gate`），替换原先在该轮廓生成的通用建筑。原版独立 POI 位于其北侧约 90 米，已经移除该误定位；稳定地标 ID 仍是 `south-gate`。

入口轴线上 OSM 标注 `memorial=column` 的四根历史门柱按纪念构筑物生成柱身、凹槽和柱帽，避免套用通用房屋的窗格、入口规则。南门模型基底对齐抬高 0.40 米的网页路面，保留可见柱脚。

模型清单保存各 GLB 的 SHA-256，网页把哈希附在资源 URL 上；更新模型后不会继续使用同名旧文件缓存。
