"""Animals of two worlds by the chunk they stand in: same position, other position, missing, extra.

Usage: animals.py A_WORLD B_WORLD [RADIUS_CHUNKS]   (chunks beyond the radius are left out)
"""
import collections, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from entity_fields import entities

SKIP = {'minecraft:chest_minecart', 'minecraft:item', 'minecraft:falling_block', 'minecraft:drowned'}


def by_chunk(world, radius):
    out = collections.defaultdict(list)
    for (kind, x, y, z), e in entities(world, 'overworld').items():
        c = (int(x) >> 4, int(z) >> 4)
        if kind not in SKIP and max(abs(c[0]), abs(c[1])) <= radius:
            out[c].append((kind, x, y, z, e))
    return out


def main():
    a_dir, b_dir = sys.argv[1:3]
    radius = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    A, B = by_chunk(a_dir, radius), by_chunk(b_dir, radius)
    st = collections.Counter()
    for c in sorted(A.keys() | B.keys()):
        a, b = A.get(c, []), B.get(c, [])
        pa = {x[:4] for x in a}
        pb = {x[:4] for x in b}
        st['same position'] += len(pa & pb)
        ka = collections.Counter(x[0] for x in a)
        kb = collections.Counter(x[0] for x in b)
        if ka != kb:
            st['chunks with other animals'] += 1
            print(f'{c}: A {dict(ka)}  B {dict(kb)}')
    st['A total'] = sum(map(len, A.values()))
    st['B total'] = sum(map(len, B.values()))
    print(dict(st))


if __name__ == '__main__':
    main()
