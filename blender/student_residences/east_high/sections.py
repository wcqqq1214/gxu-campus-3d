# Each entry specifies ring edges and the elevation section used on that wall.
# "pier" only partitions the two existing solid cheeks of a recessed gable.
PLANS = {
    19: (7, {7: 'red_bays', 11: 'red_bays', 15: 'red_bays'}),
    20: (7, {1: 'peijia', 3: 'peijia'}),
    22: (6, {10: 'paired'}),
    27: (5, {1: 'east27', 2: 'east27_end', 3: 'east27'}),
    29: (7, {10: 'mixed', 5: 'slot'}),
    30: (
        7,
        {10: 'mixed', 5: 'pier', 9: 'pier', 3: 'slot', 11: 'slot'},
    ),
    31: (7, {10: 'ribbon', 3: 'slot', 5: 'slot'}),
    32: (7, {2: 'mixed', 9: 'mixed', 8: 'pier'}),
    33: (7, {1: 'mixed', 0: 'pier', 2: 'slot'}),
    34: (7, {1: 'mixed', 0: 'pier', 2: 'slot'}),
    35: (7, {1: 'mixed', 0: 'pier', 2: 'slot'}),
}


def omit_replaced_rows(hall, edges, levels):
    for index, kind in PLANS[hall][1].items():
        if kind != 'pier':
            edges[index]['rule']['skipWindowLevels'] = range(1, levels)
