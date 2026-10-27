import pickle, collections, sys
D = pickle.load(open('/tmp/lightcmp/diffs3.pkl', 'rb'))
OUT = {}
agg = collections.defaultdict(collections.Counter)
for (seed, dim, other), parts in D.items():
    diffs = [r for p in parts for r in p[0]]
    uneq = set().union(*(p[1] for p in parts))
    seen = set().union(*(p[2] for p in parts))

    def clean(cx, y, cz):
        return all((cx + a, cz + c) in seen and (cx + a, y + b, cz + c) not in uneq
                   for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1))
    for r in diffs:
        fmt = r['kind'] == 'sky' and r['b_stored'] and not r['a_stored'] and r['b_zero']
        cat = 'fmt_zero' if fmt else 'value'
        r['clean'] = clean(r['cx'], r['sy'], r['cz'])
        k = (other, dim, r['kind'], cat, 'clean' if r['clean'] else 'nbr_blocks_differ')
        a = agg[k]
        a['sections'] += 1; a['blocks'] += r['n']; a['B>A'] += r['hgt']; a['B<A'] += r['hlt']
        a[f"maxd{min(r['maxd'], 15)}"] += 1
        OUT.setdefault(k, []).append(r)
for k in sorted(agg):
    print(k, dict(sorted(agg[k].items())))
pickle.dump(OUT, open('/tmp/lightcmp/cat.pkl', 'wb'))
