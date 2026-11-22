from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageStat
import hashlib
import json
import math
import os

ROOT = Path(__file__).resolve().parent
ready = json.loads((ROOT / 'ready.json').read_text())
native = json.loads((ROOT / 'native-check.json').read_text())
sections = json.loads((ROOT / 'sections.json').read_text())
assets = json.loads((ROOT / 'asset-check.json').read_text())['cases']
protection = json.loads((ROOT / 'protection-check.json').read_text())
reimported = json.loads((ROOT / 'export-check.json').read_text())

assert hashlib.sha256((ROOT / ready['source']).read_bytes()).hexdigest() == ready['sha256']
assert ready['sha256'] == 'a7ea63e9c8b29af54712ad24617637d6710642252b8dcb7fbb1cc99493906c3f'

JUNWU_URL = 'https://mapsv0.bdimg.com/?qt=pr3d&panoid=09007200121903051331124519B&heading=173&pitch=-6&fovy=76&width=960&height=640&quality=94'
JUNWU_RETURN_URL = 'https://mapsv0.bdimg.com/?qt=pr3d&panoid=09007200121903051331138309B&heading=359&pitch=-6&fovy=76&width=960&height=640&quality=94'
BOLLARDS_URL = 'https://mapsv0.bdimg.com/?qt=pr3d&panoid=09007200121903051151271329B&heading=178&pitch=-6&fovy=76&width=960&height=640&quality=94'
BOLLARDS_SIDE_URL = 'https://mapsv0.bdimg.com/?qt=pr3d&panoid=09007200121903051151252049B&heading=224&pitch=-6&fovy=76&width=960&height=640&quality=94'
PLATFORM_URL = 'https://mapsv0.bdimg.com/?qt=pr3d&panoid=09007200121903051337243069B&heading=170&pitch=-3&fovy=70&width=960&height=640&quality=96'


def source(label, url, file=None, camera=None, target=None):
    result = {'label': label, 'url': url}
    if file:
        result['file'] = file
    if camera:
        result['cameraXY'] = camera
    if target:
        result['targetXY'] = target
    return result


junwu_sources = [
    source('君武路沿车道向南，连续路缘及两侧步行带', JUNWU_URL, 'junwu-reference.jpg', [-461.4508267612532, -638.8539026056368], [-460.643, -645.341]),
    source('沿同一道路向北复核', JUNWU_RETURN_URL, camera=[-460.53562916422794, -648.1112021789139], target=[-460.73, -635.36]),
    source('底图道路', 'https://www.openstreetmap.org/way/685682496'),
    source('君武文化艺术教育中心完整外墙轮廓', 'https://www.openstreetmap.org/way/759337787'),
]
bollards_sources = [
    source('横街向南正对六个石球与铺装入口', BOLLARDS_URL, 'bollards-reference.jpg', [-407.2392369851761, -591.0733293802537], [-406.893, -599.586]),
    source('横街斜看入口及缘石收头', BOLLARDS_SIDE_URL, camera=[-396.21628555468357, -590.9699745631491], target=[-406.859, -602.082]),
    source('底图道路', 'https://www.openstreetmap.org/way/699156923'),
    source('大礼堂完整外墙轮廓', 'https://www.openstreetmap.org/way/671978892'),
]
platform_sources = [
    source('大型结构试验平台西侧车道定位全景', PLATFORM_URL, 'platform-reference.jpg', [-725.39, -785.58], [-725.284, -786.721]),
    source('底图道路', 'https://www.openstreetmap.org/way/759096572'),
]


def probes(rows):
    result = []
    for row in rows:
        item = dict(row)
        item['terrainDeltaM'] = row['terrainZ']['after'] - row['terrainZ']['before']
        item['roadMinusTerrainM'] = {}
        for phase in ('before', 'after'):
            road = row['roadZ'][phase]
            ground = row['terrainZ'][phase]
            item['roadMinusTerrainM'][phase] = None if road is None or ground is None else road - ground
        result.append(item)
    return result


case_ids = ('way/685682496', 'way/699156923', 'way/699156923#west-curb')
case_titles = ('君武路礼堂侧路外草坡过渡', '石球步行入口东侧草坡过渡', '石球外西侧横街缘石路床')
case_files = ('junwu', 'bollards', 'cross')
changes = (
    '保留铺面、实际水域和建筑脚线，把东侧回接从原4.6–9米突变带扩展到10.5米外圈控制点，西侧在楼体保护带外平顺回接。Y=-644米东侧路外一米窗由56.39%降至29.94%，西侧由27.43%降至20.48%。',
    '将修补局限到实景可定位的入口附近，Y<-606.5米保持原地形；以每米0.09米的绝对填挖量上限替代三米硬缓入。Y=-601米东侧路外一米窗由48.37%降至20.55%，两个大礼堂固定窗无新增坡度。',
    '保留横街车面，在X=-417至-409.3米范围补实路床并向两侧原土回接。X=-412.4米标记点路地高差由0.41650米降至0.04642米，密测无土面穿路。',
)
limitations = (
    '街景支持连续步行带和湖岸相对形态，但没有现场水准。Y=-644米内侧2.340米与外圈0.573米均为模型控制高程，约30%是保留这两点所得的拟合坡度，不是实测真实坡。总控全窗检查仍记录局部新增坡，焦点结果不代表所有窗口均下降；详见native-grades.log。',
    'Y=-601米关键站已修复，但Y=-603米原陡沿仅从58.82%降至47.65%，这是为消除保护区新增尖坡而保留的残余。总控路外P95由46.19%降至32.45%；既有最大72.32%窗口未新增。精确坡脚与填挖厚度仍需现场水准。',
    '本轮解决悬空路床，不承诺横街所有接坡低缓；总控全窗检查局部最高约27.32%，需在现场路缘与坡脚水准取得后复核。石球、铺面和排水设施外形沿用基线。',
)
field_checks = (
    '联测道路两侧步行带、湖岸坡脚与楼体墙脚，替换拟合的内外圈控制高程。',
    '在石球横断面、Y=-603米残余陡沿及大礼堂墙脚联测草面与铺面高程。',
    '沿横街两侧缘石和路外坡脚量测，复核局部约27%的模型接坡。',
)
cases = []
for i, case in enumerate(native['cases']):
    name = case_files[i]
    record = {
        'id': case_ids[i],
        'title': case_titles[i],
        'change': changes[i],
        'focusXY': ready['cases'][i]['focusXY'],
        'boundsXY': ready['cases'][i]['boundsXY'],
        'before': f'{name}-before.jpg',
        'after': f'{name}-after.jpg',
        'reference': 'bollards-reference.jpg' if i == 2 else f'{name}-reference.jpg',
        'sources': junwu_sources if i == 0 else bollards_sources,
        'limitations': limitations[i],
        'fieldCheck': field_checks[i],
        'probes': probes(case['probes']),
        'roadClearance': case['roadClearance'],
        'unchangedOutside': case['unchangedOutside'],
        'assetCheck': {
            'newCoverCount': assets[i]['newCoverCount'],
            'assetHits': assets[i]['assetHits'],
        },
        'reimported': reimported[name],
    }
    if i < 2:
        record['offPavementOneMetreSectionPctAndOffsets'] = case['offPavementOneMetrePctAndOffsets']
        record['crossSectionPeakByY'] = case['crossSectionPeakByY']
        record['extendedLongitudinalMaxOneMetrePct'] = case['extendedLongitudinalMaxOneMetrePct']
        record['extendedLongitudinalMaxNewOneMetrePct'] = case['extendedLongitudinalMaxNewOneMetrePct']
    else:
        record['markedCurbGapM'] = case['markedCurbGapM']
    cases.append(record)
cases[1]['auditoriumGrassFixedWindows'] = native['auditoriumGrassFixedWindows']
cases[1]['auditoriumGrassPeripheral'] = native['auditoriumGrassPeripheral']

platform_assessment = {
    'id': 'way/759096572',
    'title': '大型结构试验平台西侧车道',
    'decision': '保留',
    'xy': [-722.58, -786.22],
    'reason': '同一局部一米高差在V4已为1.29347米，当前为1.88804米，说明陡沿并非V5从零挖成；V5约增加0.59457米。实景能辨认路侧绿带与围栏，但无法确认挡墙坡脚、楼座标高或安全挖填范围，按任务限制不修改。',
    'v4MaxOneMetreWindow': {'fromXY': [-722.73, -786.22], 'toXY': [-721.73, -786.22], 'riseM': 1.2934722900390625},
    'currentMaxOneMetreWindow': {'fromXY': [-721.78, -786.22], 'toXY': [-720.78, -786.22], 'riseM': 1.8880386352539062},
    'reference': 'platform-reference.jpg',
    'sources': platform_sources,
    'fieldCheck': '取得挡墙、围栏基础和楼座脚线断面后，才可区分真实台地与模型陡沿。',
}

decisions = [
    {'id': case['id'], 'title': case['title'], 'decision': '修复', 'reason': case['change'], 'url': case['sources'][0]['url'], 'sources': case['sources'], 'focusXY': case['focusXY'], 'fieldCheck': case['fieldCheck']}
    for case in cases
]
decisions.append({
    'id': platform_assessment['id'],
    'title': platform_assessment['title'],
    'decision': '保留',
    'reason': platform_assessment['reason'],
    'url': PLATFORM_URL,
    'sources': platform_sources,
    'focusXY': platform_assessment['xy'],
    'fieldCheck': platform_assessment['fieldCheck'],
})

report = {
    'role': 'verge-west',
    'frozenAt': ready['frozenAt'],
    'readyRevision': ready['readyRevision'],
    'baselineSha256': ready['baselineSha256'],
    'source': ready['source'],
    'sha256': ready['sha256'],
    'nodes': ['terrain'],
    'decisions': decisions,
    'cases': cases,
    'platformAssessment': platform_assessment,
    'protection': protection,
    'comparison': 'comparison.jpg',
    'sections': 'profiles.jpg',
    'verification': {
        'native': 'native-check.json',
        'nativeGrades': 'native-grades.log',
        'assets': 'asset-check.json',
        'protection': 'protection-check.json',
        'reimported': 'export-check.json',
        'profiles': 'sections.json',
        'cameras': 'cameras.json',
        'method': '原生Mesh逐点比较修前修后高程、路地高差与东西/南北一米坡率；横断面0.1米采样，路床0.10–0.13米密测。完整外墙轮廓按0.5米采样，并检查保守外接矩形1米环带、水域与近岸。局部GLB重新导入复验探针和焦点指标，同机位实渲。',
        'limits': '数值均为模型网格高程及坡比，不是现场测量。局部GLB回读已完成；整校导出与回读由总控完成。断面表的机器可读版本为sections.json及本报告probes。',
    },
}
temporary = ROOT / 'report.tmp'
temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
os.replace(temporary, ROOT / 'report.json')

FONT_PATH = '/System/Library/Fonts/STHeiti Medium.ttc'
def font(size):
    return ImageFont.truetype(FONT_PATH, size)

# Reference / before / after contact sheet.
sheet = Image.new('RGB', (1440, 1090), '#f9f9f7')
pen = ImageDraw.Draw(sheet)
for column, title in enumerate(('地点实景', '修复前（同一基线）', '修复后（冻结源码）')):
    pen.text((12 + column * 480, 12), title, font=font(22), fill='#0b0b0b')
for i, case in enumerate(cases):
    top = 56 + i * 340
    pen.text((10, top), case['title'], font=font(18), fill='#0b0b0b')
    for column, key in enumerate(('reference', 'before', 'after')):
        image = Image.open(ROOT / case[key]).convert('RGB')
        image.thumbnail((470, 282))
        x = column * 480 + (480 - image.width) // 2
        y = top + 30 + (282 - image.height) // 2
        sheet.paste(image, (x, y))
    if i == 0:
        metric = '东侧一米窗 56.39% → 29.94%'
    elif i == 1:
        metric = 'Y=-601 东侧一米窗 48.37% → 20.55%'
    else:
        metric = '路地高差 0.4165 m → 0.0464 m'
    pen.text((12, top + 315), metric, font=font(16), fill='#52514e')
    before = Image.open(ROOT / case['before']).convert('RGB')
    after = Image.open(ROOT / case['after']).convert('RGB')
    assert before.size == after.size
    assert max(ImageStat.Stat(ImageChops.difference(before, after)).mean) > 0
sheet.save(ROOT / 'comparison.jpg', quality=94)

# One-axis sections; sections.json is the accessible table twin.
SURFACE = '#fcfcfb'
PRIMARY = '#0b0b0b'
SECONDARY = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
BEFORE = '#eb6834'
AFTER = '#2a78d6'
ROAD = '#52514e'
profile = Image.new('RGB', (1240, 990), SURFACE)
draw = ImageDraw.Draw(profile)
draw.text((28, 18), '地形修复前后断面', font=font(24), fill=PRIMARY)
for x, label, color in ((280, '修前土面', BEFORE), (480, '修后土面', AFTER), (680, '既有铺面（未改）', ROAD)):
    draw.line((x, 34, x + 30, 34), fill=color, width=2)
    draw.text((x + 40, 23), label, font=font(16), fill=SECONDARY)
for i, case in enumerate(cases):
    name = case_files[i]
    kind = 'along' if i == 2 else 'across'
    rows = sections[name][kind]
    coordinate = 'y' if i == 2 else 'dx'
    paths = {}
    for phase in ('before', 'after'):
        paths[phase] = [(row[coordinate], row['terrain'][phase]) for row in rows if row['terrain'][phase] is not None]
    road_points = [(row[coordinate], row['road']['after'][0]) for row in rows if row['road']['after'][0] is not None]
    all_paths = list(paths.values()) + [road_points]
    x_values = [point[0] for path in all_paths for point in path]
    z_values = [point[1] for path in all_paths for point in path]
    xmin, xmax = min(x_values), max(x_values)
    zmin = math.floor(min(z_values) * 2) / 2 - 0.15
    zmax = math.ceil(max(z_values) * 2) / 2 + 0.15
    left, top, width, height = 88, 90 + i * 295, 1090, 190
    draw.text((28, top - 32), case['title'], font=font(19), fill=PRIMARY)
    for tick in range(5):
        value = zmin + (zmax - zmin) * tick / 4
        y = top + height - height * tick / 4
        draw.line((left, y, left + width, y), fill=GRID, width=1)
        draw.text((28, y - 9), f'{value:.1f} m', font=font(12), fill=MUTED)
    def point(x, z):
        return (left + width * (x - xmin) / (xmax - xmin), top + height * (1 - (z - zmin) / (zmax - zmin)))
    def segments(points):
        groups = []
        current = []
        previous = None
        for item in points:
            if previous is not None and abs(item[0] - previous - 0.100001) > 0.02:
                if len(current) > 1:
                    groups.append(current)
                current = []
            current.append(item)
            previous = item[0]
        if len(current) > 1:
            groups.append(current)
        return groups
    for phase, color in (('before', BEFORE), ('after', AFTER)):
        for group in segments(paths[phase]):
            draw.line([point(x, z) for x, z in group], fill=color, width=2, joint='curve')
        x, z = paths[phase][-1]
        cx, cy = point(x, z)
        draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=SURFACE)
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=color)
    for group in segments(road_points):
        draw.line([point(x, z) for x, z in group], fill=ROAD, width=2)
    for value in (xmin, (xmin + xmax) / 2, xmax):
        x, _ = point(value, zmin)
        draw.text((x - 25, top + height + 10), f'{value:.1f}', font=font(12), fill=MUTED)
    axis_label = '校园 Y（米）' if i == 2 else '距道路中心的东西偏移（米）'
    draw.text((left + width - 250, top + height + 30), axis_label, font=font(13), fill=SECONDARY)
    metric = ('峰值 56.39% → 29.94%', '关键站峰值 48.37% → 20.55%', '路地高差 0.4165 m → 0.0464 m')[i]
    draw.text((left + 10, top + 8), metric, font=font(14), fill=SECONDARY)
profile.save(ROOT / 'profiles.jpg', quality=94)
print('WROTE report.json comparison.jpg profiles.jpg')
