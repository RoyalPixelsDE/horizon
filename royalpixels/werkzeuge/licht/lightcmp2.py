import sys, json, collections, pickle
import os; sys.path.insert(0, os.path.expanduser('~/worldgen-cmp/scripts'))
from compare import region, nbt, is_full, container
import numpy as np
from multiprocessing import Pool

DIMS = sys.argv[1].split(',')
RUNS = os.path.expanduser('~/worldgen-cmp/runs')


def nib(arr):
    b = np.frombuffer(arr[1], np.uint8)
    out = np.empty(4096, np.uint8)
    out[0::2] = b & 15
    out[1::2] = b >> 4
    return out.reshape(16, 16, 16)  # y, z, x


def chunk_light(c):
    secs = {s['Y']: s for s in c.get('sections', [])}
    ys = sorted(secs)
    sky_raw = {y: nib(secs[y]['SkyLight']) for y in ys if 'SkyLight' in secs[y]}
    sky, blk, blocks, stored = {}, {}, {}, {}
    above = None  # bottom layer of nearest stored section above
    for y in reversed(ys):
        if y in sky_raw:
            sky[y] = sky_raw[y]
            above = sky_raw[y][0]
        else:
            layer = np.full((16, 16), 15, np.uint8) if above is None else above
            sky[y] = np.broadcast_to(layer, (16, 16, 16))
        stored[y] = y in sky_raw
        blk[y] = nib(secs[y]['BlockLight']) if 'BlockLight' in secs[y] else np.zeros((16, 16, 16), np.uint8)
        if 'block_states' in secs[y]:
            names, d = container(secs[y]['block_states'], 4096)
            blocks[y] = np.array(names, dtype=object)[d].reshape(16, 16, 16) if d is not None else np.full((16, 16, 16), names[0], dtype=object)
    return sky, blk, blocks, stored


def job(args):
    seed, dim, other, rx, rz = args
    base = f'{RUNS}/r3-vanilla-{seed}/world/dimensions/minecraft/{dim}/region/r.{rx}.{rz}.mca'
    oth = f'{RUNS}/{other}-{seed}/world/dimensions/minecraft/{dim}/region/r.{rx}.{rz}.mca'
    A, B = region(base), region(oth)
    st = collections.Counter()
    diffs = []
    zero_extra = collections.Counter()
    for k in set(A) & set(B):
        cx, cz = rx * 32 + k[0], rz * 32 + k[1]
        if abs(cx) > 29 or abs(cz) > 29:
            continue
        ca, cb = nbt(A[k]), nbt(B[k])
        if not (is_full(ca) and is_full(cb)):
            continue
        st['chunks'] += 1
        sa, ba, bla, sta = chunk_light(ca)
        sb, bb, blb, stb = chunk_light(cb)
        for y in sorted(set(sa) & set(sb)):
            same = y in bla and y in blb and np.array_equal(bla[y], blb[y])
            tag = 'same' if same else 'diff'
            st[f'sections_{tag}'] += 1
            if stb[y] and not sta[y]:
                zero_extra['extra_array'] += 1
                if not sb[y].any():
                    zero_extra['extra_all_zero'] += 1
                    if sa[y].any():
                        zero_extra['extra_zero_but_vanilla_effective_nonzero'] += 1
            for kind, la, lb in (('sky', sa[y], sb[y]), ('block', ba[y], bb[y])):
                m = la != lb
                n = int(m.sum())
                if not n:
                    continue
                st[f'{kind}_{tag}_sections'] += 1
                st[f'{kind}_{tag}_blocks'] += n
                if same:
                    idx = np.nonzero(m)
                    names = collections.Counter(bla[y][idx])
                    d = lb.astype(int) - la.astype(int)
                    border = int(((idx[1] == 0) | (idx[1] == 15) | (idx[2] == 0) | (idx[2] == 15)).sum())
                    first = (int(idx[2][0]), int(idx[0][0]), int(idx[1][0]))
                    diffs.append(dict(seed=seed, dim=dim, kind=kind, cx=cx, cz=cz, sy=y, n=n,
                                      maxd=int(np.abs(d[m]).max()), hgt=int((d > 0).sum()), hlt=int((d < 0).sum()),
                                      a_stored=sta[y], b_stored=stb[y], b_zero=not sb[y].any(),
                                      names=dict(names.most_common(6)), border=border,
                                      ex=(cx * 16 + first[0], y * 16 + first[1], cz * 16 + first[2],
                                          int(la[idx[0][0], idx[1][0], idx[2][0]]), int(lb[idx[0][0], idx[1][0], idx[2][0]]))))
    return (seed, dim, other), st, zero_extra, diffs


if __name__ == '__main__':
    jobs = [(s, d, o, rx, rz) for s in (12345, 1, 8675309) for d in DIMS
            for o in ('r3-hznew', 'r3-vanilla2') for rx in (-1, 0) for rz in (-1, 0)]
    tot = collections.defaultdict(collections.Counter)
    zx = collections.defaultdict(collections.Counter)
    alld = collections.defaultdict(list)
    with Pool(8) as p:
        for key, st, ze, d in p.imap_unordered(job, jobs):
            tot[key] += st
            zx[key] += ze
            alld[key] += d
    for key in sorted(tot):
        print(key, dict(tot[key]), dict(zx[key]))
    pickle.dump(dict(alld), open('/tmp/lightcmp/diffs.pkl', 'wb'))
