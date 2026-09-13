# 树木与场地实际模型的三维检查

本批检查当前3,050株树与实际道路、桥梁、水面和运动场几何，补齐[最终占地](VEGETATION_FINAL_GROUND.md)及[模型保留区](VEGETATION_FINAL_RESERVATIONS.md)规则之外的几何证据。当前场景未发现需要处理的新穿插，因此没有删除或移动树，也没有修改场地模型。

## 覆盖范围

[场地检查器](../blender/validate_site_tree_clearance.py)读取保存的Blender源文件及模型清单中的全部69个GLB，包括基础模型、普通近景区块、地标、基础设施和两种树模板。筛选实际标记为 `roads`、`water`、`sports` 的网格，包含已有入口场地、普通铺地、岸壁和全部桥梁资源。

| 资产 | 道路及交通/入口 | 运动场及器材 | 水面及岸壁 | 合计 |
| --- | ---: | ---: | ---: | ---: |
| 保存源文件 | 26 | 36 | 2 | 64 |
| 基础与近景GLB | 45 | 5 | 2 | 52 |

源文件与导出模型的对象合并方式不同，数量不要求相等。源几何使用近景树模板及准备好的实例参数；导出几何检查基础/近景两种树模板。另行读取保存的树实例，确认类型、缩放、朝向及地面锚点一致。

树木在各自实际位置、缩放、朝向和地形标高下参与检查，先用三维包围盒筛选，再做三角面相交和可识别闭合组件的双向包含。树冠在道路上方、但与道路结构没有三维相交的情况不会被判作碰撞。

## 结果与回归

- 源场地几何检查7,501对候选，实际GLB检查15,240对候选，表面相交和可识别闭合组件包含冲突均为零。
- 同步重跑建筑检查：452个源建筑网格、95个实际基础/近景建筑网格通过。
- 3,050株保存树实例的类型、缩放、朝向和锚点与准备数据一致。源地形最大贴地误差约0.00051毫米；实际GLB地形最大锚点偏差约6.54毫米。
- 5组已知几何场景通过：道路上方树冠、穿过树冠的竖向构件、双向完全包含、仅一种LOD发生冲突，以及平移/缩放/地面高程变化。
- 共享检查模块从原建筑检查器提取，语法树对照确认几何算法不变，仅改为显式传入树行并调整函数名。建筑实际资产回归也通过。

源文件、全部树行、公共数据、69个GLB以及输出包均保持。此次仅新增检查器、测试和报告，没有重新构建模型、页面或采集相同资产的浏览器/FPS数据。

```sh
blender --background --python-exit-code 1 --python blender/test_site_tree_clearance.py
blender --background --python-exit-code 1 --python blender/validate_site_tree_clearance.py -- --report-prefix=s4-site-trees
blender --background --python-exit-code 1 --python blender/validate_tree_clearance.py -- --report-prefix=s4-shared-tree-audit
blender --background --python-exit-code 1 --python blender/validate_vegetation.py -- --report-prefix=s4-site-clearance
```

[当前汇总与哈希](model-checks/refinement/s4-site-clearance-summary.json) · [实际场地几何](model-checks/refinement/s4-site-trees-geometry.json) · [建筑回归](model-checks/refinement/s4-shared-tree-audit-geometry.json) · [树实例与贴地](model-checks/refinement/s4-site-clearance-tree-source.json)。

## 证据边界和下一步

本次通过证明当前输入与渲染几何之间未发现上述冲突。开放或非流形组件不自动封口；检查不凭空定义道路下方的实心体，也不定义运动场上方的整片净空。它不证明工程净高、现场树种、真实树冠尺寸，或未有资料的入口朝向。

已有897个占地范围、32个模型树冠保留范围及两处显式禁植区继续作为准备流程约束。之后新增树位或修改场地应重跑本检查，不能沿用当前资产哈希下的通过结论。

S4接续重点转为有资料依据的行道树、庭院和低矮景观试点。校方项目册第33页提供具名道路两侧行道树的历史线索，仍需与地图位置、照片和现状不确定性共同核对。完整S2楼栋校准、S3邻楼联合验收及S5也继续保留。
