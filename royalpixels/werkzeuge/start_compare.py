"""Compare Horizon's saved structure starts (world_probe structure_start_nbt) with the vanilla oracle's.

Usage: start_compare.py VANILLA_STARTS.txt SEED [--only REGEX]
"""
import collections, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
import canon_nbt as cn

PROBE = os.path.expanduser('~/.cache/horizon-build/target/release/examples/world_probe')
RES = os.path.expanduser('~/projects/royalpixels/horizon/.local/horizon-client/26.3')
vanilla_file, seed = sys.argv[1], sys.argv[2]
only = re.compile(sys.argv[sys.argv.index('--only') + 1]) if '--only' in sys.argv else None

sites, cur = [], None
for line in open(vanilla_file):
    line = line.rstrip('\n')
    if line.startswith('== '):
        _, name, dim = line.split()
        cur = {'name': name, 'dim': dim, 'nbt': {}}
        sites.append(cur)
    elif line.startswith('nbt '):
        _, cx, cz, tag = line.split(' ', 3)
        cur['nbt'][(int(cx), int(cz))] = tag


def diff(a, b, path=''):
    ta, va = a
    tb, vb = b
    if ta != tb:
        return [f'{path}: type {ta} vs {tb}']
    if ta == 'compound':
        out = []
        for k in sorted(set(va) | set(vb)):
            if k not in va or k not in vb:
                out.append(f'{path}/{k}: only {"vanilla" if k in va else "horizon"}')
            else:
                out += diff(va[k], vb[k], f'{path}/{k}')
        return out
    if ta == 'list':
        if len(va) != len(vb):
            return [f'{path}: {len(va)} vs {len(vb)} entries']
        out = []
        for i, (x, y) in enumerate(zip(va, vb)):
            out += diff(x, y, f'{path}[{i}]')
        return out
    return [] if va == vb else [f'{path}: {cn.plain(a)} vs {cn.plain(b)}']


totals = collections.Counter()
for s in sites:
    if only and not only.search(s['name']):
        continue
    chunks = [f'{x},{z}' for x, z in s['nbt']]
    out = subprocess.run([PROBE, 'structure_start_nbt', RES, seed, s['dim'], *chunks], capture_output=True,
                         text=True).stdout.splitlines()
    got, unsaved = {}, []
    for line in out:
        kind, cx, cz, rest = line.split(' ', 3)
        if kind == 'nbt':
            got[(int(cx), int(cz))] = rest
        else:
            unsaved.append(rest)
    for chunk, tag in s['nbt'].items():
        v = cn.parse(tag)
        sid = cn.plain(v)['id']
        if chunk not in got:
            status = f'unsaved ({",".join(unsaved)})' if unsaved else 'missing'
            totals['unsaved' if unsaved else 'missing'] += 1
            print(f'{s["name"]:24} {sid:32} {status}')
            continue
        d = diff(v, cn.parse(got[chunk]))
        totals['equal' if not d else 'different'] += 1
        print(f'{s["name"]:24} {sid:32} {"EQUAL" if not d else f"{len(d)} diffs"}')
        for line in d[:8]:
            print('      ', line[:220])
print(dict(totals))
