# 土木学院附楼三角形高墙与小拱窗

2026-09-21，接续前场连接，补入西南附楼面向前庭的三角形高墙及小拱窗。定位于`relation/12875606`的`southwest-annex`东侧上层墙面，沿该体块外环第3边。后方原平屋面保持，本批不据单面照片生成整片双坡屋顶，也不计为整栋完成。

## 依据及估算

[学院英文官网宽幅](https://tmjz-en.gxu.edu.cn/images/banner_six.jpg)可辨附楼上层窗墙之上的三角形高墙、小拱窗和前方露台；[完整正面图](https://tmjz.gxu.edu.cn/__local/A/7E/69/4A06C7C98FB4DD485911A8F3606_2806A0A4_AFCA6.jpg)从另一角度显示该高墙和窗洞，但左端部分出画。两图拍摄日期未知，后方屋顶没有足够可见信息。原图仅本机参考，[证据记录](model-checks/refinement/s2-civil-gable-evidence.json)保存来源与哈希。

| 项目 | 参数 | 口径 |
| --- | --- | --- |
| 支撑及方向 | 附楼既有10.8米屋面，沿东侧约16.70米边界 | 既有体块及照片对应；原地面轮廓不变 |
| 墙顶轮廓 | 两端11.6米，中央14.4米 | 延续0.8米女儿墙高度；峰高和对称位置为估算 |
| 墙厚 | 0.30米，向屋面内侧延伸 | 展示尺寸估算，不是结构设计 |
| 拱窗 | 宽、高均1.8米，底11.4米，半圆拱顶 | 存在与形状有照片支持；尺寸及居中位置为估算 |
| 窗框及玻璃 | 框宽0.09米，玻璃内退0.08米，简化竖向窗格 | 构件与分格估算，不推定室内用途或可开启方式 |

所有标高均相对本栋既有地面基准；并非实测高程。保留主楼、低附楼分段、入口、塔冠、台阶及两处前场连接的已有参数。

## 实现

新增`gableScreen`配置，限定在一个实体平屋面体块的外边缘。解析器检查支撑范围、墙顶轮廓、开窗净边距和参数范围，并单独记录依据。拱窗从薄墙网格中挖出真实洞口，再添加窗框、内退玻璃和简化窗格；窗口前后都有有效开口，不在完整实墙表面贴一块玻璃。

原东侧上缘的直女儿墙由高墙替代，其他女儿墙保留。形体放在远近景共享生成部分，切换细节级别时保留墙顶与窗洞。后方屋顶坡向、完整屋面分区、其他立面及前庭布局继续待核对。

## 验证

新增数据测试覆盖洞口面积、重复解析、旋转和反向环、女儿墙替换、越界与庭院冲突，以及不合适的轮廓和窗口尺寸。Blender小样从正反两侧检查墙面、玻璃和窗框，验证弧形上缘、顶面封口、法线及旋转后的结果。

[实际模型专项](model-checks/refinement/s2-civil-gable-geometry.json)在源文件、基础GLB和近景GLB分别记录46处探针结果，并检查轮廓以上无多余墙面。探针坐标和预期高度独立固定，不从新配置中读取尺寸；后方10.8米平屋面、前方7.2米露台同时保留检查。[旧资产反例](model-checks/refinement/s2-civil-gable-negative-geometry.json)按预期检出缺失高墙。

原退台专项继续检查屋面、后退墙、窗组和低层墙面；已被高墙替换的五处直女儿墙探针仅在显式`--gable-screen-added`模式下交给本批墙顶检查，不把旧的11.6米平直轮廓当作新预期。其他原有专项照常执行。

206项Python测试、56项Node测试、类型检查、lint及Pages生产构建通过。[数据比对](model-checks/refinement/s2-civil-gable-data.json)确认仅本栋增加新形体字段，全部既有形体字段保持，其他447栋、原轮廓、树位及场地数据保持。[资产比对](model-checks/refinement/s2-civil-gable-assets.json)确认仅`base.glb`和本栋近景区块变化，其他67个模型与93个基础节点保持，69个模型与生产产物一致。

[源文件比对](model-checks/refinement/s2-civil-gable-source-preservation.json)确认533个非树对象中仅土木建筑工程学院变化，其余532个对象的几何、UV、材质及变换保持，3063棵树实例保持。首载模型共5,331,292字节，比本批前增加4,660字节；最大普通建筑近景区块1,684,868字节，分别满足600万和200万字节预算。

## 性能验收

[最终汇总](model-checks/refinement/s2-civil-gable-summary.json)采用同系统S0基线、同浏览器与1280×720视口。精细模式三次为60/60/60 FPS，中位三角面4,184,666、绘制调用569，相对S0增加4.10%和4.02%；流畅模式为27/28/30 FPS，中位28 FPS，比S0下降6.67%，中位三角面1,153,130、绘制调用301，增加9.62%和14.45%。均满足帧率下降不超过10%、三角面及绘制调用增加不超过15%的现有预算；流畅模式绘制调用已接近上限。

[首轮记录](model-checks/refinement/s2-civil-gable-initial-summary.json)保留为未接受：数值预算通过，但计时窗口采样捕获一条17.2% CPU的短时Python进程，累计CPU时间仅0.12秒，不能据此推断其造成帧率变化。随后使用完全相同资产复测，未修改门槛；[复测环境记录](model-checks/refinement/s2-civil-gable-recheck-performance-performance-context.json)的24次CPU采样未捕获计时窗口内超过2%的Python或Blender进程。采样间隔10秒，此结论不代表完全没有后台活动。

## 画面对照

[修改前](screenshots/refinement/s2-civil-gable-visible/before/civil-annex-gable-trees-off-day.png) / [修改后](screenshots/refinement/s2-civil-gable-visible/after/civil-annex-gable-trees-off-day.png)显示高墙轮廓与拱窗新增关系。[南侧全貌](screenshots/refinement/s2-civil-gable-visible/after/civil-south-overview-trees-off-day.png)、[树木开启](screenshots/refinement/s2-civil-gable-visible/after/civil-south-overview-trees-on-day.png)和[夜景](screenshots/refinement/s2-civil-gable-visible/after/civil-annex-gable-trees-off-night.png)已直接核看，主体、露台与台阶关系保持。

[手机尺寸](screenshots/refinement/s2-civil-gable-visible/after/civil-annex-gable-trees-off-day-mobile.png)中可辨高墙轮廓，但窗洞较小，不用此图判断细窗格；细节由桌面图与模型探针验证。此为桌面竖屏模拟，不是实体设备测试。

[复测图书馆竖屏](screenshots/refinement/s2-civil-gable-recheck-performance/library-mobile.png)已直接核看，入口、台阶及前庭显示正常。本批仅验收附楼高墙与拱窗；累计仍为21条部分对象记录，新增整栋验收数为零。当前学院楼完成后，依用户指定顺序推进实验大厅、新结构大楼；后两栋身份与范围仍需在建模前核实。
