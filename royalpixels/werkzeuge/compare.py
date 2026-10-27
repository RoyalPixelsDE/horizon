"""Compare two worlds chunk by chunk: blocks, biomes, block entities, structures, entities, POI, light, ticks.

Usage: compare.py WORLD_A WORLD_B OUT.json [--dims overworld,the_nether,the_end] [--jobs N] [--radius R]
Only chunks that are fully generated in both worlds are compared.
"""
import argparse, collections, json, math, os, struct, sys, zlib
from multiprocessing import Pool

import numpy as np

EXAMPLES = 60


# ---- NBT --------------------------------------------------------------------------------------------------
class R:
    __slots__ = ('b', 'i')

    def __init__(self, b):
        self.b, self.i = b, 0

    def take(self, n):
        s = self.b[self.i:self.i + n]
        self.i += n
        return s

    def u(self, fmt, n):
        v = struct.unpack_from(fmt, self.b, self.i)[0]
        self.i += n
        return v

    def string(self):
        return self.take(self.u('>H', 2)).decode('utf-8', 'surrogateescape')


def payload(r, t):
    if t == 1: return r.u('>b', 1)
    if t == 2: return r.u('>h', 2)
    if t == 3: return r.u('>i', 4)
    if t == 4: return r.u('>q', 8)
    if t == 5: return round(r.u('>f', 4), 4)
    if t == 6: return round(r.u('>d', 8), 6)
    if t == 7: return ('B', r.take(r.u('>i', 4)))
    if t == 8: return r.string()
    if t == 9:
        et, n = r.u('>b', 1), r.u('>i', 4)
        return [payload(r, et) for _ in range(n)]
    if t == 10:
        d = {}
        while True:
            et = r.u('>b', 1)
            if et == 0: return d
            k = r.string()
            d[k] = payload(r, et)
    if t == 11: return ('I', r.take(4 * r.u('>i', 4)))
    if t == 12: return ('L', r.take(8 * r.u('>i', 4)))
    raise ValueError(t)


def nbt(b):
    r = R(b)
    t = r.u('>b', 1)
    r.string()
    return payload(r, t)


def region(path):
    if not os.path.exists(path):
        return {}
    f = open(path, 'rb').read()
    out = {}
    if len(f) < 8192:
        return out
    for i in range(1024):
        o = struct.unpack_from('>I', f, i * 4)[0]
        off, cnt = o >> 8, o & 0xff
        if not off:
            continue
        n, c = struct.unpack_from('>IB', f, off * 4096)
        data = f[off * 4096 + 5: off * 4096 + 4 + n]
        if c == 2:
            data = zlib.decompress(data)
        elif c == 1:
            import gzip
            data = gzip.decompress(data)
        elif c != 3:
            raise ValueError(f'compression {c} in {path}')
        out[(i & 31, i >> 5)] = data
    return out


# ---- canonical forms --------------------------------------------------------------------------------------
def state_name(e):
    # 26.3 writes a mixed list: {'': name} for a default state, {'id', 'properties'} otherwise
    if '' in e:
        return e['']
    p = e.get('Properties', e.get('properties'))
    return e.get('Name', e.get('id')) + ('[' + ','.join(f'{k}={v}' for k, v in sorted(p.items())) + ']' if p else '')


def unpack(data, n, size):
    if n <= 1:
        return np.zeros(size, np.int64)
    bits = max(4 if size == 4096 else 1, math.ceil(math.log2(n)))
    vpl = 64 // bits
    a = np.frombuffer(data[1], '>u8').astype(np.uint64)
    mask = np.uint64((1 << bits) - 1)
    cols = [(a >> np.uint64(j * bits)) & mask for j in range(vpl)]
    return np.stack(cols, 1).reshape(-1)[:size].astype(np.int64)


def container(c, size):
    pal = c.get('palette', [])
    names = [state_name(e) if isinstance(e, dict) else e for e in pal]
    if 'data' not in c:
        return names, None
    return names, unpack(c['data'], len(names), size)


def freeze(v):
    if isinstance(v, dict):
        return tuple(sorted((k, freeze(x)) for k, x in v.items()))
    if isinstance(v, list):
        return tuple(freeze(x) for x in v)
    if isinstance(v, tuple):
        return (v[0], v[1].hex() if len(v[1]) < 64 else zlib.crc32(v[1]))
    return v


def dict_diff(a, b, path=''):
    """Paths where two NBT values differ."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f'{path}/{k}' + (' (only A)' if k in a else ' (only B)'))
            elif a[k] != b[k]:
                out += dict_diff(a[k], b[k], f'{path}/{k}')
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                out += dict_diff(x, y, f'{path}[]')
        return sorted(set(out))
    return [path or '/']


ENTITY_VOLATILE = {'UUID', 'Motion', 'Rotation', 'FallDistance', 'Fire', 'Air', 'OnGround', 'PortalCooldown',
                   'HurtTime', 'HurtByTimestamp', 'DeathTime', 'Brain', 'Pos', 'Age', 'ForcedAge', 'InLove',
                   'LastPoiReleaseTime', 'Gossips', 'LastGossipDecay', 'LastRestock', 'RestocksToday', 'Xp',
                   'sleeping_pos', 'home_pos', 'last_hurt_by_mob', 'ticks_since_last_hurt_by_mob', 'leash',
                   'Health', 'AbsorptionAmount', 'attributes', 'fall_distance', 'FoodLevel'}
BE_IGNORE = {'keepPacked'}


def is_full(c):
    return c.get('Status', '').split(':')[-1] == 'full'


# ---- per region -------------------------------------------------------------------------------------------
def compare_region(job):
    a_dir, b_dir, rx, rz, lim = job
    name = f'r.{rx}.{rz}.mca'
    st = collections.Counter()
    pairs, be_paths, ent_ids, poi_types = (collections.Counter() for _ in range(4))
    ex = collections.defaultdict(list)

    def example(kind, item):
        if len(ex[kind]) < EXAMPLES:
            ex[kind].append(item)

    A, B = region(f'{a_dir}/region/{name}'), region(f'{b_dir}/region/{name}')
    full = {}
    for k in set(A) | set(B):
        cx, cz = rx * 32 + k[0], rz * 32 + k[1]
        box = lim if lim is None or len(lim) == 4 else (lim[0], lim[0], lim[1], lim[1])
        if box is not None and not (box[0] <= cx <= box[2] and box[1] <= cz <= box[3]):
            continue
        if k not in A or k not in B:
            st['chunk_missing_A' if k not in A else 'chunk_missing_B'] += 1
            continue
        ca, cb = nbt(A[k]), nbt(B[k])
        if not (is_full(ca) and is_full(cb)):
            st['chunk_not_full_both'] += 1
            continue
        full[k] = (cx, cz)
        st['chunks'] += 1
        chunk_diff_blocks = 0
        sa = {s['Y']: s for s in ca.get('sections', [])}
        sb = {s['Y']: s for s in cb.get('sections', [])}
        for y in sorted(set(sa) | set(sb)):
            s1, s2 = sa.get(y, {}), sb.get(y, {})
            for key, size, tag in (('block_states', 4096, 'block'), ('biomes', 64, 'biome')):
                c1 = s1.get(key, {'palette': [{'Name': 'minecraft:air'}] if size == 4096 else []})
                c2 = s2.get(key, {'palette': [{'Name': 'minecraft:air'}] if size == 4096 else []})
                if c1 == c2:
                    continue
                n1, d1 = container(c1, size)
                n2, d2 = container(c2, size)
                if not n1 or not n2:
                    continue
                v1 = np.array(n1, dtype=object)[d1 if d1 is not None else np.zeros(size, np.int64)]
                v2 = np.array(n2, dtype=object)[d2 if d2 is not None else np.zeros(size, np.int64)]
                diff = np.nonzero(v1 != v2)[0]
                if not len(diff):
                    st[f'{tag}_palette_order_only'] += 1
                    continue
                st[f'{tag}_diff'] += len(diff)
                if tag == 'block':
                    chunk_diff_blocks += len(diff)
                for i in diff:
                    pairs[(tag, v1[i], v2[i])] += 1
                i = int(diff[0])
                if size == 4096:
                    pos = (cx * 16 + (i & 15), y * 16 + (i >> 8), cz * 16 + ((i >> 4) & 15))
                else:
                    pos = (cx * 16 + (i & 3) * 4, y * 16 + (i >> 4) * 4, cz * 16 + ((i >> 2) & 3) * 4)
                example(tag, {'pos': pos, 'A': v1[i], 'B': v2[i], 'n_in_section': int(len(diff))})
            for lk in ('SkyLight', 'BlockLight'):
                if s1.get(lk) != s2.get(lk):
                    st[f'light_{lk}_sections_diff'] += 1
        if chunk_diff_blocks:
            st['chunks_with_block_diff'] += 1
        # block entities
        bea = {(e['x'], e['y'], e['z']): e for e in ca.get('block_entities', [])}
        beb = {(e['x'], e['y'], e['z']): e for e in cb.get('block_entities', [])}
        for p in set(bea) | set(beb):
            ea, eb = bea.get(p), beb.get(p)
            if ea is None or eb is None:
                bid = (ea or eb)['id']
                st['be_only_A' if eb is None else 'be_only_B'] += 1
                be_paths[(bid, 'only A' if eb is None else 'only B')] += 1
                example('block_entity_missing', {'pos': p, 'id': bid, 'in': 'A' if eb is None else 'B',
                                                 'loot': (ea or eb).get('LootTable')})
                continue
            st['be_compared'] += 1
            if 'LootTable' in ea:
                st['be_with_loot_table'] += 1
            ea = {k: v for k, v in ea.items() if k not in BE_IGNORE}
            eb = {k: v for k, v in eb.items() if k not in BE_IGNORE}
            if ea != eb:
                st['be_diff'] += 1
                paths = dict_diff(ea, eb)
                for path in paths:
                    be_paths[(ea['id'], path)] += 1
                example('block_entity_diff', {'pos': p, 'id': ea['id'], 'paths': paths[:6],
                                              'A': {q.strip('/'): repr(_get(ea, q))[:160] for q in paths[:3]},
                                              'B': {q.strip('/'): repr(_get(eb, q))[:160] for q in paths[:3]}})
        # structures
        stA, stB = ca.get('structures', {}), cb.get('structures', {})
        for part in ('starts', 'References'):
            pa, pb = stA.get(part, {}), stB.get(part, {})
            for sid in set(pa) | set(pb):
                if pa.get(sid) != pb.get(sid):
                    st[f'structure_{part}_diff'] += 1
                    example(f'structure_{part}', {'chunk': (cx, cz), 'structure': sid,
                                                  'paths': dict_diff(pa.get(sid), pb.get(sid))[:6]
                                                  if sid in pa and sid in pb else ['only ' + ('A' if sid in pa else 'B')]})
                elif part == 'starts' and pa[sid].get('id', 'INVALID') != 'INVALID':
                    st['structure_starts_equal'] += 1
        for hk in set(ca.get('Heightmaps', {})) | set(cb.get('Heightmaps', {})):
            if ca.get('Heightmaps', {}).get(hk) != cb.get('Heightmaps', {}).get(hk):
                st[f'heightmap_{hk}_diff'] += 1
        for tk in ('block_ticks', 'fluid_ticks'):
            ta = collections.Counter(freeze(t) for t in ca.get(tk, []))
            tb = collections.Counter(freeze(t) for t in cb.get(tk, []))
            st[f'{tk}_A'] += sum(ta.values())
            st[f'{tk}_B'] += sum(tb.values())
            st[f'{tk}_diff'] += sum(((ta - tb) + (tb - ta)).values())
        for key in ('PostProcessing',):
            if freeze(ca.get(key)) != freeze(cb.get(key)):
                st[f'{key}_diff'] += 1
        ka, kb = set(ca) - {'LastUpdate', 'InhabitedTime'}, set(cb) - {'LastUpdate', 'InhabitedTime'}
        for k in ka ^ kb:
            st[f'chunk_key_only_{"A" if k in ka else "B"}:{k}'] += 1

    # entities
    EA, EB = region(f'{a_dir}/entities/{name}'), region(f'{b_dir}/entities/{name}')
    for k, (cx, cz) in full.items():
        la = nbt(EA[k]).get('Entities', []) if k in EA else []
        lb = nbt(EB[k]).get('Entities', []) if k in EB else []
        st['entities_A'] += len(la)
        st['entities_B'] += len(lb)
        ia = collections.Counter(e.get('id') for e in la)
        ib = collections.Counter(e.get('id') for e in lb)
        for eid in set(ia) | set(ib):
            if ia[eid] != ib[eid]:
                ent_ids[(eid, 'count')] += abs(ia[eid] - ib[eid])
                example('entity_count', {'chunk': (cx, cz), 'id': eid, 'A': ia[eid], 'B': ib[eid]})
        # same id and count: compare the stable data, matched by sorted order
        for eid in ia:
            if ia[eid] != ib[eid]:
                continue
            ga = sorted((e for e in la if e.get('id') == eid), key=lambda e: tuple(e.get('Pos', [0, 0, 0])))
            gb = sorted((e for e in lb if e.get('id') == eid), key=lambda e: tuple(e.get('Pos', [0, 0, 0])))
            for x, y in zip(ga, gb):
                st['entities_compared'] += 1
                living = 'Health' in x
                if not living and [round(v, 2) for v in x.get('Pos', [])] != [round(v, 2) for v in y.get('Pos', [])]:
                    ent_ids[(eid, 'Pos')] += 1
                if living and [math.floor(v) for v in x.get('Pos', [])] != [math.floor(v) for v in y.get('Pos', [])]:
                    st['living_entity_moved'] += 1
                sx = {q: v for q, v in x.items() if q not in ENTITY_VOLATILE}
                sy = {q: v for q, v in y.items() if q not in ENTITY_VOLATILE}
                if sx != sy:
                    paths = dict_diff(sx, sy)
                    for path in paths:
                        ent_ids[(eid, path)] += 1
                    example('entity_diff', {'chunk': (cx, cz), 'id': eid, 'paths': paths[:6],
                                            'A': {q.strip('/'): repr(_get(sx, q))[:160] for q in paths[:3]},
                                            'B': {q.strip('/'): repr(_get(sy, q))[:160] for q in paths[:3]}})
    # POI
    PA, PB = region(f'{a_dir}/poi/{name}'), region(f'{b_dir}/poi/{name}')
    for k, (cx, cz) in full.items():
        def pois(P):
            if k not in P:
                return collections.Counter()
            secs = nbt(P[k]).get('Sections', {})
            return collections.Counter((r['type'], tuple(r['pos'][1].hex() if isinstance(r['pos'], tuple) else r['pos']))
                                       for s in secs.values() for r in s.get('Records', []))
        pa, pb = pois(PA), pois(PB)
        st['poi_A'] += sum(pa.values())
        st['poi_B'] += sum(pb.values())
        for (t, _), n in ((pa - pb) + (pb - pa)).items():
            poi_types[t] += n
    return dict(stats=st, pairs=pairs, be_paths=be_paths, ent=ent_ids, poi=poi_types, ex=ex)


def _get(d, path):
    for part in path.strip('/').split('/'):
        part = part.replace(' (only A)', '').replace(' (only B)', '').replace('[]', '')
        if isinstance(d, list):
            d = d[0] if d else None
        if isinstance(d, dict):
            d = d.get(part)
    if isinstance(d, tuple):
        return f'<{d[0]}-array {len(d[1])} bytes>'
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('out')
    ap.add_argument('--dims', default='overworld,the_nether,the_end')
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    ap.add_argument('--radius', type=int, help='only chunks inside the generated square')
    o = ap.parse_args()
    lim = None if o.radius is None else ((-o.radius) >> 4, o.radius >> 4)
    result = {'A': o.a, 'B': o.b, 'dims': {}}
    for dim in o.dims.split(','):
        da, db = (f'{w}/dimensions/minecraft/{dim}' for w in (o.a, o.b))
        regs = sorted({tuple(map(int, f.split('.')[1:3])) for d in (da, db)
                       for f in os.listdir(f'{d}/region') if f.endswith('.mca')})
        tot = dict(stats=collections.Counter(), pairs=collections.Counter(), be_paths=collections.Counter(),
                   ent=collections.Counter(), poi=collections.Counter(), ex=collections.defaultdict(list))
        with Pool(o.jobs) as pool:
            for i, r in enumerate(pool.imap_unordered(compare_region, [(da, db, x, z, lim) for x, z in regs])):
                for k in ('stats', 'pairs', 'be_paths', 'ent', 'poi'):
                    tot[k].update(r[k])
                for k, v in r['ex'].items():
                    tot['ex'][k] += v[:max(0, EXAMPLES - len(tot['ex'][k]))]
                print(f'\r{dim} {i + 1}/{len(regs)} regions', end='', file=sys.stderr, flush=True)
        print(file=sys.stderr)
        result['dims'][dim] = {
            'stats': dict(sorted(tot['stats'].items())),
            'top_block_pairs': [[t, a, b, n] for (t, a, b), n in tot['pairs'].most_common(80)],
            'block_entity_paths': [[i, p, n] for (i, p), n in tot['be_paths'].most_common(80)],
            'entity_diffs': [[i, p, n] for (i, p), n in tot['ent'].most_common(80)],
            'poi_diffs': dict(tot['poi'].most_common(40)),
            'examples': tot['ex'],
        }
    json.dump(result, open(o.out, 'w'), indent=1, default=str)
    for dim, d in result['dims'].items():
        print(dim, json.dumps(d['stats']))


if __name__ == '__main__':
    main()
