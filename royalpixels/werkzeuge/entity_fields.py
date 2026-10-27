"""Per entity type, the saved fields that differ between two worlds, over entities matched by position.

Usage: entity_fields.py A_WORLD B_WORLD [DIM]   (worlds are runs/<name>/world; DIM defaults to overworld)
"""
import collections, glob, os, sys

sys.path.insert(0, os.path.dirname(__file__))
import compare as c

SKIP = {'UUID', 'Pos', 'Motion', 'Rotation'}


def entities(world, dim):
    out = {}
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/entities/*.mca'):
        for raw in c.region(f).values():
            for e in c.nbt(raw).get('Entities', []):
                out[(e['id'], *(round(v, 1) for v in e['Pos']))] = e
    return out


def norm(v):
    if isinstance(v, list) and v and all(isinstance(x, dict) and 'id' in x for x in v):
        return sorted((repr(sorted(x.items())) for x in v))
    return v


def main():
    a_dir, b_dir = sys.argv[1:3]
    dim = sys.argv[3] if len(sys.argv) > 3 else 'overworld'
    A, B = entities(a_dir, dim), entities(b_dir, dim)
    found = collections.defaultdict(collections.Counter)
    example = {}
    matched = collections.Counter()
    for key in A.keys() & B.keys():
        a, b = A[key], B[key]
        matched[key[0]] += 1
        for k in (a.keys() | b.keys()) - SKIP:
            if k not in b:
                what = f'{k} only A'
            elif k not in a:
                what = f'{k} only B'
            elif norm(a[k]) != norm(b[k]):
                what = f'{k} differs'
            else:
                continue
            found[key[0]][what] += 1
            example.setdefault((key[0], what), (repr(a.get(k))[:120], repr(b.get(k))[:120]))
    for kind in sorted(found):
        print(f'{kind} ({matched[kind]} matched)')
        for what, n in found[kind].most_common():
            ea, eb = example[(kind, what)]
            print(f'  {n:4} {what:40} A={ea}  B={eb}')


if __name__ == '__main__':
    main()
