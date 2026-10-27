"""Blocks and biomes where two vanilla runs agree (order independent), and how often another world differs there.

Usage: stable_diff.py VANILLA1 VANILLA2 OUT.json RADIUS NAME=WORLD...
"""
import collections, json, os, sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import compare as c

v1, v2, out, radius = sys.argv[1:5]
others = dict(a.split('=', 1) for a in sys.argv[5:])
lo, hi = (-int(radius)) >> 4, int(radius) >> 4


def arrays(ch):
    res = {}
    for s in ch.get('sections', []):
        for key, size in (('block_states', 4096), ('biomes', 64)):
            if key in s:
                n, d = c.container(s[key], size)
                res[(s['Y'], key)] = np.array(n, dtype=object)[d if d is not None else np.zeros(size, np.int64)]
    return res


def job(a):
    dim, rx, rz = a
    name = f'r.{rx}.{rz}.mca'
    R = {k: c.region(f'{w}/dimensions/minecraft/{dim}/region/{name}') for k, w in
         [('v1', v1), ('v2', v2)] + list(others.items())}
    st, pairs = collections.Counter(), collections.Counter()
    for k in R['v1']:
        cx, cz = rx * 32 + k[0], rz * 32 + k[1]
        if not (lo <= cx <= hi and lo <= cz <= hi) or any(k not in r for r in R.values()):
            continue
        ch = {w: c.nbt(r[k]) for w, r in R.items()}
        if not all(c.is_full(x) for x in ch.values()):
            continue
        A = {w: arrays(x) for w, x in ch.items()}
        st['chunks'] += 1
        for sk, a1 in A['v1'].items():
            a2 = A['v2'].get(sk)
            if a2 is None:
                continue
            stable = a1 == a2
            kind = 'block' if sk[1] == 'block_states' else 'biome'
            st[f'{kind}_stable'] += int(stable.sum())
            st[f'{kind}_unstable'] += int((~stable).sum())
            for w in others:
                b = A[w].get(sk)
                if b is None:
                    continue
                d = stable & (a1 != b)
                n = int(d.sum())
                st[f'{w}_{kind}_diff_at_stable'] += n
                for i in np.nonzero(d)[0][:50]:
                    pairs[(w, kind, a1[i], b[i])] += 1
    return st, pairs


if __name__ == '__main__':
    res = {}
    for dim in ('overworld', 'the_nether', 'the_end'):
        regs = sorted({tuple(map(int, f.split('.')[1:3])) for f in os.listdir(f'{v1}/dimensions/minecraft/{dim}/region')})
        st, pairs = collections.Counter(), collections.Counter()
        with Pool(6) as p:
            for s, pr in p.imap_unordered(job, [(dim, x, z) for x, z in regs]):
                st.update(s)
                pairs.update(pr)
        res[dim] = {'stats': dict(st), 'top_pairs': [[*k, n] for k, n in pairs.most_common(60)]}
        print(dim, json.dumps(dict(st)))
    json.dump(res, open(out, 'w'), indent=1)
