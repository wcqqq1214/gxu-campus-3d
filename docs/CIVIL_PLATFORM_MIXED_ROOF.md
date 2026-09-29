# 结构平台门廊：中部实顶与两侧格栅的生成支持

2026-09-30，接续[完整门廊照片复核](CIVIL_PLATFORM_WIDE_ENTRY_REVIEW.md)。照片可支持中间实体顶面、两侧格栅的构成；现有生成器只能生成整板或全部格栅。本批补齐混合屋面能力并完成独立小样验证，作为下一次整体门廊替换的准备。**平台的实际位置、完整柱网及尺度尚未对应照片，生产模型本批未修改。**

## 参数与几何

`openBelow.slattedRoof` 新增可选 `solidBays`，表示填实哪些梁间空档。空档从四边形第一条边一侧起，沿与梁方向垂直的方向编号；有 `slatCount + 1` 个空档，编号为 `0` 至 `slatCount`。梁仍平行第一条边。

```json
{
  "edgeWidth": 0.8,
  "slatWidth": 0.3,
  "slatCount": 7,
  "solidBays": [2, 3, 4, 5]
}
```

这是9×16米的**合成测试小样**：七根梁形成八个空档，中间四档填实，两端各保留两个孔洞。上述尺寸、梁数及四根小样柱均不是平台设计建议，也没有写入建筑覆盖表。

参数拒绝重复、越界、布尔值和非整数编号，不允许填满所有空档；全实顶沿用原普通平顶配置。未指定或指定空数组时，保持旧格栅几何。柱顶中心必须落在梁或实顶范围，仍拒绝位于保留孔洞下方的柱子；该检查只验证模型支撑关系，不代替结构设计。

中间实顶与周边梁先合并为一个带孔多边形，再三角化并生成顶、底和洞壁，不叠放另一张板掩盖原孔洞。首次旋转测试发现独立变换后的边缘存在浮点细缝，已将混合屋面的合并放在单位方形内完成，再映射到原四边形；原未填实格栅沿用原路径。两级模型继续共用 `shared_form`，没有引入新材质或专属细节级别。

## 验证与复现

263项Python测试通过，包含真实孔洞、独立面积公式、填实区/开放区柱顶支撑、非法编号、边缘填实、旋转及空配置兼容。Blender直接调用生产 `shared_form`，在0°和31°小样上执行62条记录，检查顶面/底面高度和法线、两端孔洞穿透、四边屋顶及连续地坪；见[几何记录](model-checks/refinement/s2-platform-mixed-roof-geometry.json)。

```sh
mkdir -p work/refinement-s2-platform-mixed-roof
work/refinement-venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
work/refinement-venv/bin/python scripts/make_mixed_roof_fixture.py \
  --output work/refinement-s2-platform-mixed-roof/fixture.json
blender --background --python-exit-code 1 \
  --python blender/test_mixed_portico_roof.py -- \
  --fixture work/refinement-s2-platform-mixed-roof/fixture.json \
  --report work/refinement-s2-platform-mixed-roof/geometry-rerun.json
```

全部448栋经过完整解析和跨楼上下文处理，结果与现有生产记录一致；69个GLB在 `public` 与 `out` 中逐一符合原清单。生产数据、场景代码和已有模型资产保持，未重建全校模型、Pages或重测FPS。[本批汇总](model-checks/refinement/s2-platform-mixed-roof-summary.json)记录基准提交与代码指纹。这些是生成器和小样验证，不是平台真实门廊或整栋验收。

下一步将本能力用于已完成位置对应的门廊整体方案，同时处理前后柱列、石色玻璃围合与前缘；既有门、台阶和接路需随整体方案重新检查。C区运输口仍独立定位。累计22个校准对象、1栋首轮整栋通过、21个部分校准，S0–S5目标保持；开发、提交和推送只在`dev`。
