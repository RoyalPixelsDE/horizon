"""List every block difference between two worlds in one dimension, chunk-full-only, inside a radius.

Usage: diffdump.py A_WORLD B_WORLD DIM RADIUS [--limit N]   (prints pos A-state B-state)
"""
import glob, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import compare as c

a, b, dim, r = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
limit = int(sys.argv[6]) if len(sys.argv) > 6 else 10**9
lo, hi = (-r) >> 4, r >> 4
n = 0
for f in sorted(glob.glob(f'{a}/dimensions/minecraft/{dim}/region/*.mca')):
    name = os.path.basename(f); rx, rz = map(int, name.split('.')[1:3])
    A = c.region(f); B = c.region(f'{b}/dimensions/minecraft/{dim}/region/{name}')
    for k in A:
        cx, cz = rx * 32 + k[0], rz * 32 + k[1]
        if not (lo <= cx <= hi and lo <= cz <= hi) or k not in B:
            continue
        ca, cb = c.nbt(A[k]), c.nbt(B[k])
        if not (c.is_full(ca) and c.is_full(cb)):
            continue
        sa = {s['Y']: s for s in ca.get('sections', [])}; sb = {s['Y']: s for s in cb.get('sections', [])}
        for y in sorted(set(sa) | set(sb)):
            c1 = sa.get(y, {}).get('block_states', {'palette': [{'Name': 'minecraft:air'}]})
            c2 = sb.get(y, {}).get('block_states', {'palette': [{'Name': 'minecraft:air'}]})
            if c1 == c2:
                continue
            n1, d1 = c.container(c1, 4096); n2, d2 = c.container(c2, 4096)
            v1 = np.array(n1, dtype=object)[d1 if d1 is not None else np.zeros(4096, np.int64)]
            v2 = np.array(n2, dtype=object)[d2 if d2 is not None else np.zeros(4096, np.int64)]
            for i in np.nonzero(v1 != v2)[0]:
                i = int(i)
                print(cx * 16 + (i & 15), y * 16 + (i >> 8), cz * 16 + ((i >> 4) & 15), v1[i], v2[i])
                n += 1
                if n >= limit:
                    sys.exit()
