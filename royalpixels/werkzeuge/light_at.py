"""Saved block, block light and sky light at positions, in several worlds.

Usage: light_at.py DIM X,Y,Z [X,Y,Z ...] -- WORLD [WORLD ...]
A missing BlockLight layer is 0; a missing SkyLight layer reads as '-'.
"""
import os, sys

sys.path.insert(0, os.path.expanduser('~/worldgen-cmp/scripts'))
import compare as c

args = sys.argv[1:]
cut = args.index('--')
dim, points, worlds = args[0], [tuple(map(int, p.split(','))) for p in args[1:cut]], args[cut + 1:]
cache = {}


def chunk(world, cx, cz):
    key = (world, cx, cz)
    if key not in cache:
        rx, rz = cx >> 5, cz >> 5
        f = f'{world}/dimensions/minecraft/{dim}/region/r.{rx}.{rz}.mca'
        raw = c.region(f).get((cx & 31, cz & 31)) if os.path.exists(f) else None
        cache[key] = c.nbt(raw) if raw else None
    return cache[key]


def nibble(layer, i):
    b = layer[1][i >> 1] if isinstance(layer, tuple) else layer[i >> 1] & 255
    return (b >> 4) & 15 if i & 1 else b & 15


def at(world, x, y, z):
    ch = chunk(world, x >> 4, z >> 4)
    if ch is None:
        return 'not saved'
    sec = next((s for s in ch.get('sections', []) if s['Y'] == y >> 4), None)
    if sec is None:
        return 'no section'
    i = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
    names, data = c.container(sec.get('block_states', {}), 4096)
    block = str(names[0 if data is None else int(data[i])]).replace('minecraft:', '')
    bl = nibble(sec['BlockLight'], i) if 'BlockLight' in sec else 0
    sl = nibble(sec['SkyLight'], i) if 'SkyLight' in sec else '-'
    return f'{block} block {bl} sky {sl}'


for p in points:
    print(f'{p[0]},{p[1]},{p[2]}')
    for w in worlds:
        print(f'  {w:40} {at(w, *p)}')
