import os, sys, functools
sys.path.insert(0, '/tmp/lightcmp')
from lightcmp import chunk_light, region, nbt

RUNS = os.path.expanduser('~/worldgen-cmp/runs')


@functools.lru_cache(None)
def reg(w, dim, rx, rz):
    return region(f'{RUNS}/{w}/world/dimensions/minecraft/{dim}/region/r.{rx}.{rz}.mca')


@functools.lru_cache(None)
def chunk(w, dim, cx, cz):
    return chunk_light(nbt(reg(w, dim, cx >> 5, cz >> 5)[(cx & 31, cz & 31)]))


def at(w, dim, x, y, z):
    sky, blk, blocks, stored = chunk(w, dim, x >> 4, z >> 4)
    sy = y >> 4
    b = blocks.get(sy)
    name = b[y & 15, z & 15, x & 15] if b is not None else '-'
    return int(sky[sy][y & 15, z & 15, x & 15]), int(blk[sy][y & 15, z & 15, x & 15]), name


def short(n):
    n = n.replace('minecraft:', '')
    return n.split('[')[0][:14]


def show(seed, dim, x, y, z, worlds=('r3-vanilla', 'r3-vanilla2', 'r3-hznew'), r=1, axis='xz'):
    for dy in range(r, -r - 1, -1):
        for dz in range(-r, r + 1):
            row = []
            for dx in range(-r, r + 1):
                vals = [at(f'{w}-{seed}', dim, x + dx, y + dy, z + dz) for w in worlds]
                row.append(f"{short(vals[0][2]):>14} s{'/'.join(str(v[0]) for v in vals)} b{'/'.join(str(v[1]) for v in vals)}")
            print(f'y{y+dy} z{z+dz}: ' + ' | '.join(row))
        print()


if __name__ == '__main__':
    a = sys.argv
    show(int(a[1]), a[2], int(a[3]), int(a[4]), int(a[5]), r=int(a[6]) if len(a) > 6 else 1)
