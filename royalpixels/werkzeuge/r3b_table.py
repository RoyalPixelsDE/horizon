"""Tables for the 3-seed run: results/r3/*.json -> results/r3/tables.md and tables.html."""
import collections, glob, html, json, os, re

R = os.path.expanduser('~/worldgen-cmp/results/r3b')
RUNS = os.path.expanduser('~/worldgen-cmp/runs')
SEEDS = ['12345', '1', '8675309']
PLAT = [('vanilla2', 'Vanilla (2nd run)'), ('paper', 'Paper + Chunky'), ('hz069', 'Horizon 0.2.69'),
        ('hznew', 'Horizon with our fixes')]
DIMS = [('overworld', 'Overworld', 384), ('the_nether', 'Nether', 256), ('the_end', 'End', 256)]


def load(name):
    p = f'{R}/{name}'
    return json.load(open(p)) if os.path.exists(p) else None


def total(plat, dim, key):
    n = 0
    for s in SEEDS:
        d = load(f'{s}-v-{plat}.json')
        if d:
            n += d['dims'][dim]['stats'].get(key, 0)
    return n


def pct(a, b):
    return f'{100 * a / b:.2f} %' if b else '-'


tables = []
for dim, label, height in DIMS:
    rows = []
    chunks = {p: total(p, dim, 'chunks') for p, _ in PLAT}
    rows.append(('Blocks different', {p: f'{total(p, dim, "block_diff"):,} ({pct(total(p, dim, "block_diff"), chunks[p] * 256 * height)})' for p, _ in PLAT}))
    rows.append(('Chunks with a block difference', {p: f'{total(p, dim, "chunks_with_block_diff"):,} of {chunks[p]:,}' for p, _ in PLAT}))
    rows.append(('Biome cells different', {p: f'{total(p, dim, "biome_diff"):,}' for p, _ in PLAT}))
    rows.append(('Structure starts equal', {p: f'{total(p, dim, "structure_starts_equal")} of {total(p, dim, "structure_starts_equal") + total(p, dim, "structure_starts_diff") + total(p, dim, "structure_starts_only_A")}' for p, _ in PLAT}))
    rows.append(('Structure references different', {p: f'{total(p, dim, "structure_References_diff"):,}' for p, _ in PLAT}))
    rows.append(('Block entities different / missing / extra', {p: f'{total(p, dim, "be_diff"):,} / {total(p, dim, "be_only_A"):,} / {total(p, dim, "be_only_B"):,}' for p, _ in PLAT}))
    rows.append(('Entities (vanilla / this)', {p: f'{total(p, dim, "entities_A"):,} / {total(p, dim, "entities_B"):,}' for p, _ in PLAT}))
    rows.append(('Points of interest (vanilla / this)', {p: f'{total(p, dim, "poi_A"):,} / {total(p, dim, "poi_B"):,}' for p, _ in PLAT}))
    rows.append(('Surface heightmap columns different', {p: f'{total(p, dim, "heightmap_WORLD_SURFACE_diff"):,}' for p, _ in PLAT}))
    tables.append((label, rows))

loot_rows = []
for dim, label, _ in DIMS:
    for p, _ in PLAT:
        pass
lt = {}
for p, _ in PLAT[1:]:
    st = collections.Counter()
    for s in SEEDS:
        d = load(f'{s}-loot-{p}.json')
        if d:
            for dim in d:
                for k, v in d[dim]['stats'].items():
                    if not k.startswith('chest_minecart'):
                        st[k.split(' ', 1)[1]] += v
    lt[p] = st
same = lambda st: st['other_kept_table_same'] + st['rolled_equal']
loot = [('Containers with a vanilla loot table', {p: f'{lt[p]["vanilla_loot_table"]:,}' for p in lt}),
        ('Same loot as vanilla', {p: f'{same(lt[p]):,} ({pct(same(lt[p]), lt[p]["vanilla_loot_table"])})' for p in lt}),
        ('Different loot', {p: f'{lt[p]["rolled_different"] + lt[p]["other_kept_table_different"]:,}' for p in lt}),
        ('Container missing', {p: f'{lt[p]["missing_in_other"]:,}' for p in lt}),
        ('Chest minecarts same / different / missing', {p: f'{lt[p]["other_kept_table_same"] - 0:,}' for p in lt})]
cart = {}
for p, _ in PLAT[1:]:
    st = collections.Counter()
    for s in SEEDS:
        d = load(f'{s}-loot-{p}.json')
        for dim in (d or {}):
            for k, v in d[dim]['stats'].items():
                if k.startswith('chest_minecart'):
                    st[k.split(' ', 1)[1]] += v
    cart[p] = st
loot[-1] = ('Chest minecarts same / different / missing', {p: f'{cart[p]["other_kept_table_same"] + cart[p]["rolled_equal"]} / {cart[p]["other_kept_table_different"] + cart[p]["rolled_different"]} / {cart[p]["missing_in_other(pos)"]}' for p in cart})

perf = []
names = [('vanilla', 'Vanilla')] + PLAT
st = {}
for p, _ in names:
    w = c = r = 0
    for s in SEEDS:
        f = f'{RUNS}/r3-{p}-{s}/stats.json'
        if os.path.exists(f):
            d = json.load(open(f))
            w += sum(x['wall_s'] for x in d['dims'].values())
            c += sum(x['cpu_s'] for x in d['dims'].values())
            r = max(r, d.get('peak_rss_gb', 0))
    st[p] = (w, c, r)
perf = [('Generation time, 3 seeds x 3 dimensions', {p: f'{st[p][0] / 60:.1f} min' for p, _ in names}),
        ('CPU time', {p: f'{st[p][1] / 60:.1f} min' for p, _ in names}),
        ('Peak memory (RSS)', {p: f'{st[p][2]:.1f} GB' for p, _ in names})]

fx = {}
for p, _ in names:
    agg = collections.Counter()
    for s in SEEDS:
        f = f'{R}/{s}-{p}-fixes.txt'
        if not os.path.exists(f):
            continue
        for line in open(f):
            dim, _, js = line.partition(' ')
            try:
                for k, v in json.loads(js).items():
                    if isinstance(v, int) and not k.startswith('highest'):
                        agg[f'{dim} {k}'] += v
            except ValueError:
                pass
    fx[p] = agg
fixrows = [
    ('Nether/End chunks with the vanilla yPos 0', lambda a: f'{a["the_nether yPos=0"] + a["the_end yPos=0"]:,} of {sum(v for k, v in a.items() if k.split()[0] in ("the_nether", "the_end") and k.split()[1].startswith("yPos"))}'),
    ('Structure starts saved (Overworld + Nether)', lambda a: f'{a["overworld structure_starts"] + a["the_nether structure_starts"]}'),
    ('Containers saved with their loot table', lambda a: f'{a["overworld container_loot_table"] + a["the_nether container_loot_table"]:,}'),
    ('Containers saved with pre-rolled items', lambda a: f'{a["overworld container_prerolled_items"] + a["the_nether container_prerolled_items"]:,}'),
    ('Trial spawners with an empty spawn_data', lambda a: f'{a["overworld trial_spawner_EMPTY_spawn_data"]}'),
    ('Block entities without an id', lambda a: f'{sum(v for k, v in a.items() if k.endswith("block_entity_without_id"))}'),
    ('POI region files', lambda a: f'{a["overworld poi_region_files"]}'),
]
fixes = [(n, {p: f(fx[p]) for p, _ in names}) for n, f in fixrows]


def md(title, cols, rows):
    out = [f'### {title}', '', '| | ' + ' | '.join(l for _, l in cols) + ' |', '|---' * (len(cols) + 1) + '|']
    out += ['| ' + n + ' | ' + ' | '.join(v.get(p, '') for p, _ in cols) + ' |' for n, v in rows]
    return '\n'.join(out) + '\n'


def ht(title, cols, rows):
    h = f'<h3>{html.escape(title)}</h3><table><tr><th></th>' + ''.join(f'<th>{html.escape(l)}</th>' for _, l in cols) + '</tr>'
    for n, v in rows:
        h += f'<tr><td>{html.escape(n)}</td>' + ''.join(f'<td>{html.escape(v.get(p, ""))}</td>' for p, _ in cols) + '</tr>'
    return h + '</table>'


sections = [(f'{l}: compared with vanilla', PLAT, rows) for l, rows in tables]
sections += [('Loot: what a player finds when opening each container', PLAT[1:], loot),
             ('Save format checks', names, fixes), ('Speed and load', names, perf)]
open(f'{R}/tables.md', 'w').write('\n'.join(md(*s) for s in sections))
open(f'{R}/tables.html', 'w').write('<meta charset="utf-8"><style>body{font:14px system-ui;background:#111;color:#ddd;margin:24px}'
    'table{border-collapse:collapse;margin-bottom:24px}td,th{border:1px solid #444;padding:4px 10px;text-align:right}'
    'td:first-child{text-align:left}th{background:#222}</style>' + ''.join(ht(*s) for s in sections))
print(open(f'{R}/tables.md').read())
