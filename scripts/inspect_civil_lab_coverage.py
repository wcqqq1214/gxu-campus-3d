"""Read-only footprint inventory for the next civil laboratory work package.

The search rectangle is a manual location aid, NOT a surveyed hall footprint.
Run with work/refinement-venv/bin/python scripts/inspect_civil_lab_coverage.py.
"""
import hashlib
import html
import json
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/buildings.json"
OUT = ROOT / "docs/model-checks/refinement/s2-civil-lab-coverage"
SEARCH_BOUNDS = [-650, -780, -470, -695]
VIEW_BOUNDS = [-760, -880, -400, -625]


def main():
    raw = SOURCE.read_bytes()
    buildings = json.loads(raw)
    search, view = box(*SEARCH_BOUNDS), box(*VIEW_BOUNDS)
    shapes = {
        b["id"]: unary_union([Polygon(p[0], p[1:]) for p in b["polygons"]])
        for b in buildings
    }
    nearby = [b for b in buildings if shapes[b["id"]].intersects(view)]
    cases = []
    for margin in [0, 5, 10]:
        region = search.buffer(margin, join_style=2)
        hits = []
        for b in buildings:
            area = shapes[b["id"]].intersection(region).area
            if area > 1e-8:
                hits.append({"id": b["id"], "name": b["name"],
                             "intersectionAreaM2": round(area, 6)})
        cases.append({"outwardMarginM": margin, "hits": hits})
    report = {
        "status": "location-screening-only-not-registered-or-production-ready",
        "productionReady": False,
        "source": "public/data/buildings.json",
        "sourceSha256": hashlib.sha256(raw).hexdigest(),
        "buildingCount": len(buildings),
        "coordinateSystem": "campus local east/north metres",
        "searchBounds": SEARCH_BOUNDS,
        "searchBasis": "Manual search rectangle north of the civil college and east of the new platform, guided by the school construction location map. Not a traced or registered footprint.",
        "sourceUrls": [
            "https://www.gxu.edu.cn/info/1365/36792.htm",
            "https://www.gxu.edu.cn/info/1364/36271.htm",
            "https://tmjz.gxu.edu.cn/info/1452/5053.htm",
        ],
        "sensitivityCases": cases,
        "nearbyBuildings": [{"id": b["id"], "name": b["name"],
                             "bounds": b["bounds"], "chunk": b["chunk"]}
                            for b in nearby],
        "limitations": [
            "An empty search rectangle is not proof of demolition or current absence.",
            "The old hall may be absent from this source dataset; identity, historical footprint and current existence remain unconfirmed.",
            "Do not create a building, assign a height or rename an existing object from this rectangle.",
            "The new platform candidate way/957404988 is one existing compound footprint; its internal hall must not be duplicated as another whole building.",
        ],
    }
    OUT.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    scale = 2.5
    def point(p):
        return 50 + (p[0] - VIEW_BOUNDS[0]) * scale, 100 + (VIEW_BOUNDS[3] - p[1]) * scale
    def path(poly):
        commands = []
        for ring in [poly.exterior, *poly.interiors]:
            points = [point(p) for p in ring.coords]
            commands.append("M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points) + " Z")
        return " ".join(commands)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="870" viewBox="0 0 1000 870">',
           '<rect width="1000" height="870" fill="#fafaf7"/>',
           '<g font-family="Arial,sans-serif" fill="#26323b">',
           '<text x="50" y="38" font-size="24">Civil laboratory queue: existing footprint coverage</text>',
           '<text x="50" y="68" font-size="15">Location screening only — search box is NOT a hall footprint or demolition boundary.</text>']
    for b in nearby:
        geom = shapes[b["id"]].intersection(view)
        polygons = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        color = {"way/957404988": "#9ebcd9", "relation/12875606": "#d4ba91",
                 "way/957404989": "#c1c9be"}.get(b["id"], "#deded8")
        for poly in polygons:
            if poly.geom_type == "Polygon":
                svg.append(f'<path d="{path(poly)}" fill="{color}" fill-rule="evenodd" stroke="#66737b"/>')
        x, y = point(geom.representative_point().coords[0])
        label = {"way/957404988": "New platform candidate", "relation/12875606": "Civil college",
                 "way/957404989": "Physics college"}.get(b["id"], "Existing building")
        svg.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="12" text-anchor="middle">{html.escape(label)}</text>')
    svg.append(f'<path d="{path(search)}" fill="#d8876930" stroke="#b05a3d" stroke-width="2" stroke-dasharray="7 5"/>')
    x, y = point(search.centroid.coords[0])
    svg.extend([f'<text x="{x}" y="{y}" text-anchor="middle" font-size="17">Old-hall search area</text>',
                f'<text x="{x}" y="{y+24}" text-anchor="middle" font-size="14">{len(cases[0]["hits"])} existing footprint intersections</text>',
                '<path d="M 920,195 L 920,130 M 913,145 L 920,130 L 927,145" fill="none" stroke="#26323b" stroke-width="2"/>',
                '<text x="914" y="119" font-size="17">N</text>',
                '<path d="M 50,773 L 175,773 M 50,768 L 50,778 M 175,768 L 175,778" stroke="#26323b"/>',
                '<text x="83" y="798" font-size="14">50 m</text>',
                '<text x="240" y="781" font-size="14">Blue: way/957404988 · Tan: relation/12875606 · Grey-green: way/957404989</text>',
                '<text x="50" y="835" font-size="14">Source: current buildings.json + school location-map screening. No production geometry changed.</text>',
                '</g></svg>'])
    OUT.with_suffix(".svg").write_text("\n".join(svg) + "\n")
    print(json.dumps({"output": str(OUT), "cases": cases}, ensure_ascii=False))


if __name__ == "__main__":
    main()
