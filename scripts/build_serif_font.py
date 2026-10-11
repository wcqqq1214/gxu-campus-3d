#!/usr/bin/env python3
"""Subset Noto Serif SC for the interface headings.

The serif face is only used for place names and dialog titles, so the subset
covers the characters of every landmark and building name plus the interface
copy in app/page.tsx. Rerun after adding names with new characters:

    python3 scripts/build_serif_font.py /path/to/NotoSerifSC-SemiBold.otf

Requires fontTools and brotli. The source font is not kept in the repository;
download it from https://github.com/notofonts/noto-cjk (Serif/SubsetOTF/SC).
"""
import json
import re
import sys
from pathlib import Path

from fontTools import subset

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'app/fonts/gxu-serif.woff2'
BASIC = ''.join(chr(c) for c in range(0x20, 0x7F)) + '·「」（）—…、，。：'
CJK = re.compile('[\\u3000-\\u303f\\u3400-\\u9fff\\uff00-\\uffef]')


def characters() -> str:
    names = []
    for file in ('buildings.json', 'landmarks.json'):
        data = json.loads((ROOT / 'public/data' / file).read_text('utf-8'))
        names += [item.get('name') or '' for item in data]
    copy = (ROOT / 'app/page.tsx').read_text('utf-8')
    text = ''.join(names) + ''.join(CJK.findall(copy)) + BASIC
    return ''.join(sorted(set(text)))


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    text = characters()
    options = subset.Options()
    options.flavor = 'woff2'
    options.layout_features = ['kern', 'palt', 'vert']
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
    options.notdef_outline = True
    options.hinting = False
    font = subset.load_font(sys.argv[1], options)
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(font, str(OUT), options)
    print(f'{OUT.relative_to(ROOT)}: {len(text)} characters, {OUT.stat().st_size} bytes')


if __name__ == '__main__':
    main()
