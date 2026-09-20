# 土木学院东南门厅侧向玻璃与转角顶板

2026-09-21，接续连续白色斜墙，为东南主门厅补入沿东墙的两层玻璃、石色柱梁与L形转角顶板。原侧面两排通用窗被替换；主入口仍为同一个入口，没有额外声明侧门、台阶或平台。正面门厅、上部玻璃塔头和白色斜墙保持。

## 依据与估算

[英文官网入口近照](https://tmjz-en.gxu.edu.cn/info/1050/1096.htm)和[宽幅照片](https://tmjz-en.gxu.edu.cn/images/banner_six.jpg)可以辨认门厅东侧的两层玻璃、竖向柱、层间横梁，以及围绕转角的顶板。沿用原东南转角及第16边定位，未用透视照片修改地面轮廓。拍摄日期未知，原照片仅留在本机参考。

| 部位 | 本批参数 | 口径 |
| --- | --- | --- |
| 侧向玻璃 | 沿墙进深3.8米，两端各留0.1米，分两开间 | 形制有照片支持；进深与开间为简化估算 |
| 标高 | 下缘0.1米，层间3.6米，玻璃上缘7.2米 | 沿用正面门厅估算标高 |
| 柱梁 | 柱宽0.4米、深0.3米，层间梁高0.45米 | 展示估算，不作为结构尺寸 |
| 侧顶板 | 外挑1.4米，下缘7.2米、上缘7.8米 | 与既有正面顶板共边，补齐角部空隙 |

主门的宽高与正面玻璃、柱、原顶板参数未改；侧玻璃没有绘制一套未经定位的门框或新增导航入口。白色斜墙上的局部低层小开口仍待核对，不能将侧门厅本批校准视为全部侧立面完成。来源文件哈希与完整参数见[证据记录](model-checks/refinement/s2-civil-portal-return-evidence.json)。

## 数据与生成

`flushEntrance.returnGlazing` 复用现有门厅标高，显式指定转角端、沿墙深度、开间、柱梁和出挑。仅支持有足够支撑长度的近直角凸角；要求同一实体墙段高于顶板，拒绝邻翼碰撞、无前顶板、过窄开间和低层显式面板重叠。原顶板的默认规则仍不允许自行跨角，转角由这个单独校准的构件表达。

L形顶板与原顶板端边对齐，具有完整顶面、底面及外侧面。基础与近景共享侧玻璃和柱梁；与侧玻璃相交的通用窗整组避让。保留原唯一主入口，未改变建筑、庭院及附楼轮廓。

## 验证与画面

200项Python测试、56项Node测试、类型检查、lint和Pages构建通过。新增数据测试覆盖旋转后的左右转角、顶板共边、解析幂等性、非法参数、相邻翼楼碰撞及低层面板冲突。两级生成小样检查侧玻璃、柱梁和顶板法线。

[正式模型专项](model-checks/refinement/s2-civil-portal-return-geometry.json)在源文件、基础和近景GLB各检查59处，包含新旧顶板接缝两侧、玻璃与框柱、梁、顶板上下及外侧、范围外留空，并确认未增加地面平台。[旧模型反例](model-checks/refinement/s2-civil-portal-return-negative-geometry.json)按预期失败。

原正面入口每级69处、塔头92处、上部幕墙216处、白墙52处、附楼台阶101处及其他既有专项回归通过。幕墙和白墙回归中原侧门厅两处石色探针已改由本批玻璃探针接管，不将材料变化伪称为原几何未变。

首次近景镜头被前方楼栋遮挡，不能用于验收，已留下[未通过记录](model-checks/refinement/s2-civil-portal-return-initial-visual-review.json)。模型未改动，改从楼间空地重拍；最终画面采用 `visible-reframed` 记录，初稿截图保留。

| 画面 | 对照 |
| --- | --- |
| 门厅转角 | [改前](screenshots/refinement/s2-civil-portal-return-visible-reframed/before/civil-portal-return-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-portal-return-visible-reframed/after/civil-portal-return-trees-off-day.png) |
| 南侧全貌 | [改前](screenshots/refinement/s2-civil-portal-return-visible-reframed/before/civil-south-overview-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-portal-return-visible-reframed/after/civil-south-overview-trees-off-day.png) |
| 树木与夜景 | [树木开启](screenshots/refinement/s2-civil-portal-return-visible-reframed/after/civil-south-overview-trees-on-day.png) / [夜景](screenshots/refinement/s2-civil-portal-return-visible-reframed/after/civil-portal-return-trees-off-night.png) |
| 手机尺寸 | [桌面竖屏模拟](screenshots/refinement/s2-civil-portal-return-visible-reframed/after/civil-portal-return-trees-off-day-mobile.png)，非实体设备测试 |

七张最终建筑画面已直接核看，侧玻璃和柱梁清楚可见，未见原通用窗残片或明显顶板裂缝；正面门厅、塔冠、白墙和附楼台阶保留。该检查不等同入口到校道的铺装连接已经完成。

[源对象比对](model-checks/refinement/s2-civil-portal-return-source-preservation.json)确认仅土木学院变化，其他530个非树对象和3063个树实例保持。建筑数据仍为同一栋改动，侧顶板不与其他建筑轮廓相交。[资产检查](model-checks/refinement/s2-civil-portal-return-assets.json)确认69个GLB与Pages产物一致，仅基础模型和本栋近景块改变；首屏5,176,736字节，增加816字节，最大普通近景1,684,868字节。

## 性能与阶段状态

[联合验收](model-checks/refinement/s2-civil-portal-return-summary.json)通过。三次LOD往返及两档各三次30秒采样完成，精细档60/60/60 FPS，流畅档29/29/29 FPS。相对原同系统S0基线，帧率变化0%/−3.33%，三角形增加3.65%/8.45%，绘制调用增加2.38%/11.03%，均在原预算内。

24次CPU快照未在计时窗口捕获超过2%阈值的Python或Blender进程；10秒间隔采样不证明完全没有后台活动。图书馆入口竖屏回归画面亦已核看，见[最终画面验收](model-checks/refinement/s2-civil-portal-return-visual-review.json)。

本批仅完成侧门厅玻璃与转角顶板。累计仍为21条部分对象记录、0栋新增整栋验收；接下来继续附楼屋顶与场地连接，学院建筑完成后依次开展实验大厅、新结构大楼。
