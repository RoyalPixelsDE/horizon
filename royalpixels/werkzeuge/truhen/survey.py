import sys, os, glob
import os; sys.path.insert(0, os.path.expanduser('~/worldgen-cmp/scripts'))
from compare import region, nbt, container, is_full
import numpy as np
def chests(world, dim):
    out = {}
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/region/*.mca'):
        for (lx, lz), raw in region(f).items():
            c = nbt(raw)
            if not is_full(c): continue
            cx, cz = c['xPos'], c['zPos']
            for s in c['sections']:
                bs = s.get('block_states')
                if not bs: continue
                names, data = container(bs, 4096)
                idx = [i for i, n in enumerate(names) if n.startswith(('minecraft:chest', 'minecraft:trapped_chest'))]
                if not idx: continue
                if data is None: data = np.zeros(4096, np.int64)
                for i in idx:
                    for p in np.nonzero(data == i)[0]:
                        p = int(p)
                        out[(cx*16 + (p & 15), s['Y']*16 + (p >> 8), cz*16 + ((p >> 4) & 15))] = names[i]
    return out
R = os.path.expanduser('~/worldgen-cmp/runs/')
for seed in sys.argv[1:]:
    for dim in ('overworld', 'the_nether'):
        v, v2, h = (chests(R + f'r3-{k}-{seed}/world', dim) for k in ('vanilla', 'vanilla2', 'hznew'))
        common = set(v) & set(v2) & set(h)
        print(seed, dim, 'chests v/v2/h/common', len(v), len(v2), len(h), len(common))
        for pos in sorted(common):
            if v[pos] == v2[pos] and h[pos] != v[pos]:
                print('  DIFF', pos, v[pos], '->', h[pos])
            elif v[pos] != v2[pos]:
                print('  vanilla-unstable', pos, v[pos], v2[pos], h[pos])
