"""Every saved start of some structure types: start NBT, blocks in its pieces, containers, against vanilla.

Usage: struct_check.py VANILLA_WORLD OTHER_WORLD [DIM]
Only starts whose pieces lie fully inside the chunks both worlds saved as full.
"""
import glob, os, struct, sys

import numpy as np

sys.path.insert(0, os.path.expanduser('~/worldgen-cmp/scripts'))
import compare as c

A_DIR, B_DIR = sys.argv[1:3]
DIM = sys.argv[3] if len(sys.argv) > 3 else 'overworld'
TYPES = ('shipwreck', 'buried_treasure', 'village', 'ruined_portal')
CONTAINERS = {'minecraft:chest', 'minecraft:trapped_chest', 'minecraft:barrel', 'minecraft:suspicious_sand',
              'minecraft:suspicious_gravel'}


def world(d):
    out = {}
    for f in glob.glob(f'{d}/dimensions/minecraft/{DIM}/region/*.mca'):
        rx, rz = map(int, os.path.basename(f).split('.')[1:3])
        for (x, z), raw in c.region(f).items():
            ch = c.nbt(raw)
            if c.is_full(ch):
                out[(rx * 32 + x, rz * 32 + z)] = ch
    return out


def ints(v):
    return struct.unpack(f'>{len(v[1]) // 4}i', v[1]) if isinstance(v, tuple) else tuple(v)


def blocks(chs, boxes):
    out = {}
    i = np.arange(4096)
    lx, ly, lz = i & 15, i >> 8, (i >> 4) & 15
    cover = {(cx, cz) for b in boxes for cx in range(b[0] >> 4, (b[3] >> 4) + 1) for cz in range(b[2] >> 4, (b[5] >> 4) + 1)}
    for key in cover:
        ch = chs.get(key)
        if ch is None:
            return None
        for s in ch.get('sections', []):
            x0, y0, z0 = key[0] * 16, s['Y'] * 16, key[1] * 16
            near = [b for b in boxes if b[1] <= y0 + 15 and b[4] >= y0]
            if not near:
                continue
            names, data = c.container(s.get('block_states', {}), 4096)
            if not names:
                continue
            x, y, z = x0 + lx, y0 + ly, z0 + lz
            hit = np.zeros(4096, bool)
            for b in near:
                hit |= (x >= b[0]) & (x <= b[3]) & (y >= b[1]) & (y <= b[4]) & (z >= b[2]) & (z <= b[5])
            for j in np.nonzero(hit)[0]:
                out[(int(x[j]), int(y[j]), int(z[j]))] = str(names[0 if data is None else int(data[j])])
    return out


def containers(chs, boxes):
    inside = lambda e: any(b[0] <= e['x'] <= b[3] and b[1] <= e['y'] <= b[4] and b[2] <= e['z'] <= b[5] for b in boxes)
    return {(e['x'], e['y'], e['z']): {k: e.get(k) for k in ('id', 'LootTable', 'LootTableSeed', 'Items', 'item')}
            for ch in chs.values() for e in ch.get('block_entities', []) if inside(e)}


A, B = world(A_DIR), world(B_DIR)
for (cx, cz), ch in sorted(A.items()):
    for sid, st in ch.get('structures', {}).get('starts', {}).items():
        if st.get('id', 'INVALID') == 'INVALID' or not any(t in sid for t in TYPES):
            continue
        boxes = [ints(p['BB']) for p in st['Children']]
        ba = blocks(A, boxes)
        if ba is None:
            continue
        sb = B.get((cx, cz), {}).get('structures', {}).get('starts', {}).get(sid)
        bb = blocks(B, boxes) or {}
        diff = [(p, ba[p], bb.get(p)) for p in ba if ba[p] != bb.get(p)]
        ca, cb = containers(A, boxes), containers(B, boxes)
        cdiff = [p for p in ca.keys() | cb.keys() if ca.get(p) != cb.get(p)]
        ok = sb == st and not diff and not cdiff
        print(f'{sid} chunk {cx},{cz}: {len(st["Children"])} pieces, {len(ba)} blocks, {len(ca)} containers;',
              'OK' if ok else f'start {"same" if sb == st else "DIFFERS"}, {len(diff)} blocks differ, {len(cdiff)} containers differ')
        for d in diff[:4]:
            print('    block', d)
        for p in cdiff[:3]:
            print('    container', p, ca.get(p), '/', cb.get(p))
