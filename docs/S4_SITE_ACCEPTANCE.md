# 镜湖岸段与6B铺地：补齐性能验收

2026-09-16，`dev`。镜湖大礼堂侧29.50米岸段和6B小广场两个既有样板完成联合验收，关闭此前因并发计算干扰而保留的性能待办。本次复查资产版本为 `ba7b95c`，没有重新修改或导出模型。**这两处样板通过不等于S4全面完成。**

## 当前资产重新核验

| 项目 | 当前结果 | 报告 |
| --- | --- | --- |
| 镜湖岸壁、水线、岸顶及陆侧 | 源文件/GLB各26条水线射线及原12个失效岸站通过；水位和原通道保持，陆侧高出水面至少约0.425米 | [岸段几何](model-checks/refinement/s4-shore-current-geometry.json) |
| 6B铺地与主路接缝 | 源文件/GLB各101个密集接缝点通过，GLB最大高差约1.11毫米；17个原露空边缘采样均有封口 | [铺地几何](model-checks/refinement/s4-paving-current-geometry.json) |
| 铺地内部与下方地形 | 975个内部点无穿出，GLB最小模型净距约11.4厘米；原轮廓及范围外地形/道路比较通过 | 同上 |
| 关闭道路后的地形纹理 | 源文件/GLB各100,000条覆盖射线无缺口，UV投影及三角形面积检查通过 | [纹理检查](model-checks/refinement/s4-paving-current-terrain-texture.json) |
| 日夜及图层恢复 | 镜湖9张、铺地7张逐张核看，页面和资源无错误 | [镜湖图层](model-checks/refinement/s4-shore-current-interaction.json)、[铺地图层](model-checks/refinement/s4-paving-current-interaction.json)、[人工记录](model-checks/refinement/s4-site-current-visual-review.json) |

岸段、铺地和纹理验证器新增可选 `--report-prefix`，保存本次独立记录及资产指纹，原几何阈值不变。浏览器图层脚本也记录实际加载的模型清单哈希。旧失败记录及旧汇总保持原样，当前状态以[本次联合验收](model-checks/refinement/s4-site-current-acceptance.json)为准。

## 性能依据与适用范围

原来两项性能待办都采用图书馆活动镜头：每档三次30秒环绕。本次使用刚完成的[同一资产集测量](model-checks/refinement/s2-physics-corridor-performance-browser.json)，对比当前系统与浏览器上重录的[S0基线](model-checks/refinement/s2-arts-s0-current-os-browser.json)。当前几何报告、图层截图和性能报告的模型清单均一致，SHA256为 `a13fc5886e3f029337fecc0f3bd658f7a283d834b74b1cdef17b6d0b36288a81`。

| 指标 | 精细 | 流畅 | 原门槛 |
| --- | ---: | ---: | --- |
| 三次FPS | 60 / 60 / 60 | 29 / 29 / 29 | 中位数下降不超过10% |
| FPS相对S0 | 0% | −3.33% | 通过 |
| 三角形相对S0 | +3.55% | +7.92% | 增长不超过15% |
| 绘制调用相对S0 | +2.38% | +11.03% | 增长不超过15% |

24次进程快照中，六个计时窗口未记录到超过2%阈值的Python/Blender计算；三次LOD往返无错误。正常桌面应用保持运行，此结果不是隔离基准、岸段/广场各个局部镜头的帧率保证或手机真机测量。首屏模型5,150,788 bytes、最大普通近景1,684,868 bytes，分别低于6 MB/2 MB预算。

历史[岸段增量检查](model-checks/refinement/s4-incremental-summary.json)和[铺地增量检查](model-checks/refinement/s4-paving-incremental-summary.json)作为已通过的维护证据保留；本次只读复核没有重新运行这两组隔离变体，也没有将旧受干扰测量改判为通过。

## 继续保留的范围限制

- 岸高、岸顶宽度及照片对应的具体岸段仍含估算；其他岸线尚未推广。
- 6B广场实际红色分带、坐台和花坛尚未重建。本次通过的是既定铺地连接与防穿地工作包。
- 广场接触窄带以外曾记录的44个道路压缩缺口采样点，本次没有修复或宣称消除。
- S2整批楼栋、S3六栋邻楼与完整场地、剩余S4/S5继续按计划推进。
