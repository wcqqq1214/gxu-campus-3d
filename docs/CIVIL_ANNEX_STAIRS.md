# 土木学院附楼两段外台阶与平台

2026-09-20，接续[东南玻璃幕墙转角](CIVIL_CURTAIN_RETURN.md)，为西南低附楼补充宽下梯、中间平台及向主楼侧偏置的窄上梯。模型同时进入基础与近景，原主入口、主楼/附楼分段及屋面保持。本批仍为局部实现，不计整栋完成。

## 依据、位置与估算

[官网宽幅](https://tmjz-en.gxu.edu.cn/images/banner_six.jpg)及[完整正面图](https://tmjz.gxu.edu.cn/__local/A/7E/69/4A06C7C98FB4DD485911A8F3606_2806A0A4_AFCA6.jpg)显示附楼外台阶由宽下梯、中间平台和偏向主楼的窄上梯组成。结合此前定位的南主立面和原C形附楼轮廓，采用附楼东侧原外环第4边为锚点；这一位置对应及尺寸是照片约束估算，不是测绘或可确认的逐级计数。

| 部位 | 本批参数 | 口径 |
| --- | --- | --- |
| 宽下梯 | 宽12米、九级，按0.18米标高增量 | 实际级数与尺寸未知 |
| 中间平台 | 标高1.62米，上梯前净深1.6米 | 统一相对本栋基准，不解释为测得的室内楼层 |
| 窄上梯 | 宽4.8米、五级，向主楼侧偏置3.2米 | 阶段关系有照片支持；尺寸为估算 |
| 上平台 | 标高2.52米、进深1.2米 | 未凭平台补一扇未经定位的房门 |
| 踏面与范围 | 踏面0.32米，总外伸6.64米 | 原锚边长约16.70米；结构不进入原建筑轮廓 |
| 底座 | 到建筑基准以下0.25米 | 防止实体平台悬空，非基础结构设计 |

平台采用落地实体表达，窄上梯之外保留同高的侧向平台。与平台相交的通用低层窗整组停用，避免台阶遮挡后留下半截窗框；上层及其余墙面窗列保持。未增加无依据的扶手、花池或屋顶坡面；照片中的三角形高墙不足以证明后方整片屋顶为双坡屋面。附楼的分级屋顶、台阶侧墙、内部门槛关系和完整道路连接继续核对。

## 数据与生成约束

`terracedStairs` 是限定的两段台阶参数，不改原OSM建筑轮廓，也不自动声明一个入口。锚点必须落在同一个实体体块的完整外墙段；上下梯必须容纳于平台内，保留侧向净距，踏步增量及平台尺寸均受界限检查。解析阶段拒绝未知字段、错误锚点、跨体块支撑、平台越界以及与邻楼、已有显式门廊/台阶或外廊相交。

两级模型共用同一组平台及踏步实体。新增旋转、保留原轮廓、解析幂等性、非法尺寸/高差、跨体块支撑和邻楼/入口冲突测试；其余建筑继续走原生成路径。

## 几何与地面

[专项检查](model-checks/refinement/s2-civil-stairs-final-geometry.json)在源文件、基础GLB与近景GLB各核对101处：两段各级踏面与立面、上下平台、侧向平台、宽度边界、表面法线及范围外留空。[原无台阶模型反例](model-checks/refinement/s2-civil-stairs-negative-geometry.json)如预期失败。

另在源地形和基础模型各采样12处底座/梯脚地面。底座与地面相接，地形未穿出踏面；最外一级露出高度约9–17厘米，与建筑基准上的0.18米内部踏步增量不同。这是现有地面微小起伏造成的模型差异，已保留在报告中；没有为使数字整齐而修改地形。该检查不代表梯脚到校道已经完成连续铺装。

首次画面检查发现平台切到通用低层窗，留下半截窗框，因此[初稿画面验收](model-checks/refinement/s2-civil-stairs-initial-visual-review.json)记录为未通过。修复只排除与新台阶实体相交的通用窗，未补未经定位的门洞；两级实际生成小样验证上层及范围外窗列保留。初稿模型检查与截图保留，最终验收使用 `s2-civil-stairs-final` 记录。

## 最终构建与画面对照

193项Python测试、56项Node测试、类型检查、lint及Pages构建通过。源文件、基础和近景模型均通过上述101处专项检查，既有幕墙、凹窗、窗带、附楼与主入口回归通过；通用建筑、树木和道路碰撞检查通过。源文件除土木学院外的530个非树对象及3063个树实例保持，建筑数据仅此一栋变化。

首屏模型为5,174,864字节，比本批前增加1,352字节；最大普通近景块为1,684,868字节。资产清单与Pages产物一致，见[资产检查](model-checks/refinement/s2-civil-stairs-final-assets.json)。重建生成的重复清树日志未替换原清树历史，本批树木检查单独保存在最终报告中。

| 画面 | 对照 |
| --- | --- |
| 附楼近景 | [改前](screenshots/refinement/s2-civil-stairs-final-visible/before/civil-annex-stairs-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-stairs-final-visible/after/civil-annex-stairs-trees-off-day.png) |
| 南侧全貌 | [改前](screenshots/refinement/s2-civil-stairs-final-visible/before/civil-south-overview-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-stairs-final-visible/after/civil-south-overview-trees-off-day.png) |
| 树木与夜景 | [树木开启](screenshots/refinement/s2-civil-stairs-final-visible/after/civil-south-overview-trees-on-day.png) / [夜景](screenshots/refinement/s2-civil-stairs-final-visible/after/civil-annex-stairs-trees-off-night.png) |
| 手机尺寸 | [桌面浏览器竖屏模拟](screenshots/refinement/s2-civil-stairs-final-visible/after/civil-annex-stairs-trees-off-day-mobile.png)，非实体手机测试 |

七张最终建筑画面已逐张检查；与平台相交的半截窗框已消除。台阶到墙的门洞尚未定位，不将这次平台补充记作完整入口验收。下一批继续主楼冠部、附楼屋顶及空间连接的取证与实现，整栋完成后按用户顺序转实验大厅、再转新结构大楼。

最终[联合验收](model-checks/refinement/s2-civil-stairs-final-summary.json)通过。与原S0基线使用相同浏览器与环境，精细档三轮均为60 FPS，流畅档三轮均为29 FPS（基线30 FPS，下降3.33%）。两档三角形增幅分别为3.81%和8.41%，绘制调用增幅为2.38%和11.41%，均在原计划预算内。24次CPU采样未在计时窗口发现高占用Python或Blender；这是10秒间隔、2%CPU阈值的采样结论。图书馆入口竖屏回归画面亦已检查，见[最终画面记录](model-checks/refinement/s2-civil-stairs-final-visual-review.json)。
