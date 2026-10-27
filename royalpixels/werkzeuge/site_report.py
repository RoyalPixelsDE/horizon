"""Per structure site: compare vanilla and other world inside each site's chunk box.

Usage: site_report.py SITES.json VANILLA_WORLD OTHER_WORLD OUT.json
"""
import collections, json, os, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
import compare as c

sites, A, B, out = sys.argv[1:5]


def site(item):
    name, s = item
    x0, z0, x1, z1 = s['box']
    da, db = (f'{w}/dimensions/minecraft/{s["dim"]}' for w in (A, B))
    regs = {(x >> 5, z >> 5) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}
    tot = dict(stats=collections.Counter(), pairs=collections.Counter(), be_paths=collections.Counter(),
               ent=collections.Counter(), poi=collections.Counter(), ex=collections.defaultdict(list))
    for rx, rz in regs:
        r = c.compare_region((da, db, rx, rz, (x0, z0, x1, z1)))
        for k in ('stats', 'pairs', 'be_paths', 'ent', 'poi'):
            tot[k].update(r[k])
        for k, v in r['ex'].items():
            tot['ex'][k] += v[:20]
    return name, {'dim': s['dim'], 'pos': [s['x'], s['z']], 'stats': dict(tot['stats']),
                  'block_entity_paths': [[i, p, n] for (i, p), n in tot['be_paths'].most_common(40) if 'sculk' not in i],
                  'entity_diffs': [[i, p, n] for (i, p), n in tot['ent'].most_common(40)],
                  'top_block_pairs': [[a, b, n] for (_, a, b), n in tot['pairs'].most_common(15)],
                  'examples': {k: v[:8] for k, v in tot['ex'].items()}}


if __name__ == '__main__':
    items = [(k, v) for k, v in json.load(open(sites)).items() if v]
    with Pool(6) as p:
        res = dict(p.map(site, items))
    json.dump(res, open(out, 'w'), indent=1, default=str)
    for k, r in res.items():
        st = r['stats']
        print(f"{k:24} chunks {st.get('chunks', 0):4} blocks {st.get('block_diff', 0):7} starts {st.get('structure_starts_diff', 0):3} "
              f"BE {st.get('be_compared', 0):4}/{st.get('be_diff', 0):3} ent {st.get('entities_A', 0):4}/{st.get('entities_B', 0):4}")
