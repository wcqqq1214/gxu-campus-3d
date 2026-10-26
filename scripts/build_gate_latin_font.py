#!/usr/bin/env python3
"""Derive the gate's small Latin OTF from the existing Noto Serif SC UI subset.

Run with fontTools and brotli installed. The renamed derivative is covered by
blender/fonts/GXUGateSerif-OFL.txt; no system font or network fetch is needed.
"""
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    font = TTFont(ROOT / 'app/fonts/gxu-serif.woff2', recalcTimestamp=False)
    options = subset.Options()
    options.hinting = False
    options.layout_features = []
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
    worker = subset.Subsetter(options=options)
    worker.populate(text='GUANGXI UNIVERSITY')
    worker.subset(font)
    names = {1: 'GXU Gate Serif', 2: 'Regular', 3: 'GXUGateSerif-1',
             4: 'GXU Gate Serif', 6: 'GXUGateSerif'}
    for record in font['name'].names:
        if record.nameID in names:
            record.string = names[record.nameID].encode(record.getEncoding())
    cff = font['CFF '].cff
    cff.fontNames = ['GXUGateSerif']
    cff.topDictIndex[0].FamilyName = 'GXU Gate Serif'
    cff.topDictIndex[0].FullName = 'GXU Gate Serif'
    font.flavor = None
    target = ROOT / 'blender/fonts/GXUGateSerif.otf'
    font.save(target)
    print(f'{target.relative_to(ROOT)}: {target.stat().st_size} bytes')


if __name__ == '__main__':
    main()
