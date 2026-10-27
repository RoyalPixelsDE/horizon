import sys; import os; sys.path.insert(0, os.path.expanduser('~/worldgen-cmp/scripts'))
from compare import region, nbt, container
import struct, functools
_reg = {}
def chunk(world, dim, cx, cz):
    base = f'{world}/dimensions/minecraft/{dim}/region' if dim != 'overworld' else f'{world}/dimensions/minecraft/overworld/region'
    key = (base, cx >> 5, cz >> 5)
    if key not in _reg:
        r = region(f'{base}/r.{cx>>5}.{cz>>5}.mca')
        _reg[key] = {k: v for k, v in r.items()}
    raw = _reg[key].get((cx & 31, cz & 31))
    return nbt(raw) if raw else None
_sec = {}
def block(world, dim, x, y, z):
    k = (world, dim, x >> 4, z >> 4)
    if k not in _sec:
        c = chunk(world, dim, x >> 4, z >> 4)
        _sec[k] = {s['Y']: s for s in c['sections']} if c else {}
    s = _sec[k].get(y >> 4)
    if not s: return None
    names, data = container(s['block_states'], 4096)
    return names[0] if data is None else names[data[((y & 15) << 8) | ((z & 15) << 4) | (x & 15)]]
