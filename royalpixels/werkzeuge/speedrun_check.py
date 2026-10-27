"""Zero-tolerance speedrun checks of one world against vanilla's, inside the stronghold, fortress and bastion.

Usage: speedrun_check.py VANILLA_WORLD OTHER_WORLD BOXES_JSON
For each structure: its start NBT, every block inside its pieces' boxes, end portal frame eyes, containers
(loot table and seed or items), spawners, and the mobs standing in its boxes. Prints one line per check and the
differences, and the world spawn of both level.dat files.
"""
import collections, glob, gzip, json, os, struct, sys

import numpy as np

sys.path.insert(0, os.path.expanduser('~/worldgen-cmp/scripts'))
import compare as c

A_DIR, B_DIR, BOXES = sys.argv[1:4]
STRUCT = {'stronghold': 'minecraft:stronghold', 'fortress': 'minecraft:fortress', 'bastion_remnant': 'minecraft:bastion_remnant'}
CONTAINERS = {'minecraft:chest', 'minecraft:trapped_chest', 'minecraft:barrel', 'minecraft:dispenser'}
IGNORE_ENTITY = {'UUID', 'Motion', 'attributes', 'EggLayTime', 'Brain'}  # per-entity random, compared apart in noise


def chunks(world, dim, box):
    out = {}
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/region/*.mca'):
        rx, rz = map(int, os.path.basename(f).split('.')[1:3])
        for (x, z), raw in c.region(f).items():
            cx, cz = rx * 32 + x, rz * 32 + z
            if box[0] - 2 <= cx <= box[2] + 2 and box[1] - 2 <= cz <= box[3] + 2:
                ch = c.nbt(raw)
                if c.is_full(ch):
                    out[(cx, cz)] = ch
    return out


def entities(world, dim):
    out = []
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/entities/*.mca'):
        for raw in c.region(f).values():
            out += c.nbt(raw).get('Entities', [])
    return out


def find_start(chs, sid):
    for (cx, cz), ch in chs.items():
        st = ch.get('structures', {}).get('starts', {}).get(sid)
        if st and st.get('id', 'INVALID') != 'INVALID' and st.get('Children'):
            return (cx, cz), st
    return None, None


def ints(v):
    return struct.unpack(f'>{len(v[1]) // 4}i', v[1]) if isinstance(v, tuple) else tuple(v)


def boxes_of(start):
    return [ints(p['BB']) for p in start['Children']]


def inside(boxes, x, y, z):
    return any(b[0] <= x <= b[3] and b[1] <= y <= b[4] and b[2] <= z <= b[5] for b in boxes)


def block_map(chs, boxes):
    out = {}
    i = np.arange(4096)
    lx, ly, lz = i & 15, i >> 8, (i >> 4) & 15
    for (cx, cz), ch in chs.items():
        for s in ch.get('sections', []):
            x0, y0, z0 = cx * 16, s['Y'] * 16, cz * 16
            near = [b for b in boxes if b[0] <= x0 + 15 and b[3] >= x0 and b[1] <= y0 + 15 and b[4] >= y0
                    and b[2] <= z0 + 15 and b[5] >= z0]
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


def block_entities(chs, boxes):
    return {(e['x'], e['y'], e['z']): e for ch in chs.values() for e in ch.get('block_entities', [])
            if inside(boxes, e['x'], e['y'], e['z'])}


def spawn(world):
    d = c.nbt(gzip.open(f'{world}/level.dat').read())['Data']
    return struct.unpack('>3i', d['spawn']['pos'][1])


boxes_json = json.load(open(BOXES))
fails = 0
print(f'spawn point: vanilla {spawn(A_DIR)}, other {spawn(B_DIR)}', 'OK' if spawn(A_DIR) == spawn(B_DIR) else 'DIFFERS')
fails += spawn(A_DIR) != spawn(B_DIR)
for key, sid in STRUCT.items():
    site = boxes_json[key]
    dim = site['dim']
    A, B = chunks(A_DIR, dim, site['box']), chunks(B_DIR, dim, site['box'])
    (ca, sa), (cb, sb) = find_start(A, sid), find_start(B, sid)
    if sa is None:
        print(f'{key}: no start in the vanilla box'); fails += 1; continue
    print(f'{key}: start at chunk {ca}, {len(sa["Children"])} pieces;', 'start NBT equal' if sa == sb else f'START DIFFERS (other at {cb})')
    fails += sa != sb
    boxes = boxes_of(sa)
    ba, bb = block_map(A, boxes), block_map(B, boxes)
    diff = [(p, ba[p], bb.get(p)) for p in ba if ba[p] != bb.get(p)]
    print(f'  blocks in its pieces: {len(ba)} compared, {len(diff)} differ', *[f'\n    {d}' for d in diff[:5]])
    fails += bool(diff)
    ea, eb = block_entities(A, boxes), block_entities(B, boxes)
    if key == 'stronghold':
        eye = lambda st: st is not None and 'eye=true' in st
        frames = sorted(p for p, st in ba.items() if 'end_portal_frame' in st)
        bad = [(p, eye(ba[p]), eye(bb.get(p))) for p in frames if bb.get(p) is None or 'end_portal_frame' not in bb[p]
               or eye(ba[p]) != eye(bb[p])]
        print(f'  end portal frames: {len(frames)}, with an eye {sum(eye(ba[p]) for p in frames)}; {len(bad)} differ')
        fails += bool(bad) or not frames
    keys = lambda e: {k: e.get(k) for k in ('id', 'LootTable', 'LootTableSeed', 'Items', 'SpawnData', 'SpawnPotentials')}
    for kind, sel in [('containers', lambda e: e['id'] in CONTAINERS), ('spawners', lambda e: e['id'] == 'minecraft:mob_spawner')]:
        pa = {p: keys(e) for p, e in ea.items() if sel(e)}
        pb = {p: keys(e) for p, e in eb.items() if sel(e)}
        bad = [p for p in pa.keys() | pb.keys() if pa.get(p) != pb.get(p)]
        print(f'  {kind}: {len(pa)} in vanilla, {len(pb)} in other; {len(bad)} differ', *[f'\n    {p}: {pa.get(p)} / {pb.get(p)}' for p in bad[:3]])
        fails += bool(bad)
    ma = [e for e in entities(A_DIR, dim) if inside(boxes, *map(int, e['Pos']))]
    mb = [e for e in entities(B_DIR, dim) if inside(boxes, *map(int, e['Pos']))]
    key_of = lambda e: (e['id'], *(round(v, 2) for v in e['Pos']))
    da, db = {key_of(e): e for e in ma}, {key_of(e): e for e in mb}
    missing, extra = da.keys() - db.keys(), db.keys() - da.keys()
    fields = collections.Counter(k for p in da.keys() & db.keys() for k in da[p].keys() | db[p].keys()
                                 if k not in IGNORE_ENTITY and da[p].get(k) != db[p].get(k))
    print(f'  mobs: {len(da)} in vanilla, {len(db)} in other; missing {len(missing)}, extra {len(extra)}, field diffs {dict(fields) or 0}')
    fails += bool(missing or extra or fields)
print('ALL ZERO' if fails == 0 else f'{fails} CHECKS WITH DIFFERENCES')
