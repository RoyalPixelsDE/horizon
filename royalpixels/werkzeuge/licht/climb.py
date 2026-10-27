import sys
sys.path.insert(0, '/tmp/lightcmp')
import look

W = ('r3-vanilla', 'r3-vanilla2', 'r3-hznew')


def climb(seed, dim, p, idx=1, w='r3-vanilla'):
    path = [p]
    while True:
        x, y, z = p
        cur = look.at(f'{w}-{seed}', dim, x, y, z)[idx]
        best = max(((x + dx, y + dy, z + dz) for dx, dy, dz in
                    ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))),
                   key=lambda q: look.at(f'{w}-{seed}', dim, *q)[idx])
        if look.at(f'{w}-{seed}', dim, *best)[idx] <= cur:
            return path
        p = best
        path.append(p)


if __name__ == '__main__':
    seed, dim, x, y, z = int(sys.argv[1]), sys.argv[2], *map(int, sys.argv[3:6])
    idx = int(sys.argv[6]) if len(sys.argv) > 6 else 1
    for q in climb(seed, dim, (x, y, z), idx):
        vals = [look.at(f'{w}-{seed}', dim, *q) for w in W]
        print(q, look.short(vals[0][2]), 'V/V2/H', [v[idx] for v in vals], 'chunk', (q[0] >> 4, q[2] >> 4))
