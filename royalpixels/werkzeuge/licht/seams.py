"""Self-consistency of saved light: between two air cells, light may differ by at most 1."""
import os, sys, collections, pickle
sys.path.insert(0, '/tmp/lightcmp')
from lightcmp import chunk_light, region, nbt, is_full
import numpy as np
from multiprocessing import Pool

RUNS = os.path.expanduser('~/worldgen-cmp/runs')
AIR = ('minecraft:air', 'minecraft:cave_air', 'minecraft:void_air')


def load(w, dim):
    out = {}
    for rx in (-1, 0):
        for rz in (-1, 0):
            R = region(f'{RUNS}/{w}/world/dimensions/minecraft/{dim}/region/r.{rx}.{rz}.mca')
            for k, data in R.items():
                cx, cz = rx * 32 + k[0], rz * 32 + k[1]
                if abs(cx) > 29 or abs(cz) > 29:
                    continue
                c = nbt(data)
                if not is_full(c):
                    continue
                sky, blk, blocks, _ = chunk_light(c)
                ys = sorted(blocks)
                air = np.concatenate([np.isin(blocks[y], AIR) for y in ys])  # Y, z, x
                out[(cx, cz)] = (ys[0] * 16, air, np.concatenate([sky[y] for y in ys]).astype(np.int8),
                                 np.concatenate([blk[y] for y in ys]).astype(np.int8))
    return out


def job(args):
    w, dim = args
    C = load(w, dim)
    st = collections.Counter()
    seams = []
    for (cx, cz), (y0, air, sky, blk) in C.items():
        for name, L in (('sky', sky), ('block', blk)):
            for axis in (1, 2):  # z, x
                a = air[:, :-1, :] if axis == 1 else air[:, :, :-1]
                b = air[:, 1:, :] if axis == 1 else air[:, :, 1:]
                la = L[:, :-1, :] if axis == 1 else L[:, :, :-1]
                lb = L[:, 1:, :] if axis == 1 else L[:, :, 1:]
                st[f'{name}_interior'] += int((a & b & (np.abs(la - lb) > 1)).sum())
            for (dx, dz) in ((1, 0), (0, 1)):
                n = C.get((cx + dx, cz + dz))
                if n is None or n[0] != y0:
                    continue
                L2 = n[2] if name == 'sky' else n[3]
                if dx:
                    a, b, la, lb = air[:, :, 15], n[1][:, :, 0], L[:, :, 15], L2[:, :, 0]
                else:
                    a, b, la, lb = air[:, 15, :], n[1][:, 0, :], L[:, 15, :], L2[:, 0, :]
                m = a & b & (np.abs(la - lb) > 1)
                k = int(m.sum())
                st[f'{name}_border'] += k
                if k:
                    idx = np.argwhere(m)[0]
                    seams.append((name, (cx, cz), (cx + dx, cz + dz), k, int(idx[0]) + y0,
                                  int(np.abs(la - lb)[m].max())))
            # vertical: sky 15 above air must give 15 below in air
            if name == 'sky':
                st['sky_vertical'] += int((air[:-1] & air[1:] & (L[1:] == 15) & (L[:-1] != 15)).sum())
    return w, dim, st, seams


if __name__ == '__main__':
    jobs = [(f'{p}-{s}', d) for s in (12345, 1, 8675309) for p in ('r3-vanilla', 'r3-vanilla2', 'r3-hznew')
            for d in ('overworld', 'the_end', 'the_nether')]
    res = {}
    with Pool(9) as pool:
        for w, d, st, seams in pool.imap_unordered(job, jobs):
            res[(w, d)] = (st, seams)
            print(w, d, dict(st), 'seams', len(seams), flush=True)
    pickle.dump(res, open('/tmp/lightcmp/seams.pkl', 'wb'))
