"""Status and light of every chunk inside a pre-generated square, per dimension: all must be full and lit.

Usage: area_status.py WORLD RADIUS_BLOCKS   (the square of chunks -(r>>4)..(r>>4) around 0,0, as /pregen and gen.py cover)
"""
import collections, glob, os, sys

sys.path.insert(0, os.path.expanduser('~/worldgen-cmp/scripts'))
import compare as c

world, radius = sys.argv[1], int(sys.argv[2])
lo, hi = (-radius) >> 4, radius >> 4
bad_total = 0
for dim in ('overworld', 'the_nether', 'the_end'):
    seen, bad = set(), collections.Counter()
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/region/*.mca'):
        rx, rz = map(int, os.path.basename(f).split('.')[1:3])
        for (x, z), raw in c.region(f).items():
            cx, cz = rx * 32 + x, rz * 32 + z
            if not (lo <= cx <= hi and lo <= cz <= hi):
                continue
            ch = c.nbt(raw)
            seen.add((cx, cz))
            lit = ch.get('isLightOn') == 1
            if not c.is_full(ch) or not lit:
                bad[(ch.get('Status'), 'lit' if lit else 'unlit', 'edge' if max(abs(cx), abs(cz)) in (abs(lo), hi) else 'inside')] += 1
    missing = (hi - lo + 1) ** 2 - len(seen)
    bad_total += sum(bad.values()) + missing
    print(f'{dim}: {len(seen)} of {(hi - lo + 1) ** 2} chunks saved, {missing} missing, not full or unlit: {dict(bad) or 0}')
print('OK' if bad_total == 0 else f'FAIL: {bad_total}')
