"""Classify SkyLight/BlockLight differences between two worlds. Usage: light_diff.py A B RADIUS [dim]"""
import collections, glob, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import compare as c

A, B, radius = sys.argv[1], sys.argv[2], int(sys.argv[3])
dim = sys.argv[4] if len(sys.argv) > 4 else 'overworld'
lo, hi = (-radius) >> 4, radius >> 4
for kind in ('SkyLight', 'BlockLight'):
    st = collections.Counter()
    for f in sorted(glob.glob(f'{A}/dimensions/minecraft/{dim}/region/*.mca')):
        rx, rz = map(int, os.path.basename(f).split('.')[1:3])
        V, H = c.region(f), c.region(f.replace(A, B))
        for k in V:
            if not (lo <= rx * 32 + k[0] <= hi and lo <= rz * 32 + k[1] <= hi) or k not in H:
                continue
            a = {s['Y']: s for s in c.nbt(V[k])['sections']}
            b = {s['Y']: s for s in c.nbt(H[k])['sections']}
            for y in a:
                la, lb = a[y].get(kind), b.get(y, {}).get(kind)
                if la == lb:
                    continue
                if la is None or lb is None:
                    st['one_side_missing'] += 1
                    continue
                x, z = np.frombuffer(la[1], np.uint8), np.frombuffer(lb[1], np.uint8)
                d = np.abs(np.concatenate([(x & 15).astype(int) - (z & 15), (x >> 4).astype(int) - (z >> 4)]))
                st['sections_value_diff'] += 1
                st['values_diff'] += int((d > 0).sum())
                st['sections_delta_ge_8'] += int(d.max() >= 8)
    print(kind, json.dumps(dict(st)))
