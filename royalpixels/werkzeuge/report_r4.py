"""The 3-seed report after the third round of fixes: report/report-r4.html and worldgen-comparison-3seeds-v3.pdf.

All numbers come from results/r3b (this run) and results/r3 (the first run, before the second round of fixes).
"""
import collections, glob, json, os, subprocess

HOME = os.path.expanduser('~/worldgen-cmp')
R, R1 = f'{HOME}/results/r3b', f'{HOME}/results/r3'
SEEDS = ['12345', '1', '8675309']
CHROME = sorted(glob.glob(os.path.expanduser('~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell')))[-1]


def total(res, plat, dim, key):
    n = 0
    for s in SEEDS:
        p = f'{res}/{s}-v-{plat}.json'
        if os.path.exists(p):
            n += json.load(open(p))['dims'][dim]['stats'].get(key, 0)
    return n


def loot(res, plat):
    st = collections.Counter()
    for s in SEEDS:
        p = f'{res}/{s}-loot-{plat}.json'
        if os.path.exists(p):
            for d in json.load(open(p)).values():
                for k, v in d['stats'].items():
                    if not k.startswith('chest_minecart'):
                        st[k.split(' ', 1)[1]] += v
    same = st['other_kept_table_same'] + st['rolled_equal']
    return 100 * same / st['vanilla_loot_table'] if st['vanilla_loot_table'] else 0


def wall(plat):
    w = c = r = 0
    for s in SEEDS:
        f = f'{HOME}/runs/r3-{plat}-{s}/stats.json'
        if os.path.exists(f):
            d = json.load(open(f))
            w += sum(x['wall_s'] for x in d['dims'].values())
            c += sum(x['cpu_s'] for x in d['dims'].values())
            r = max(r, d.get('peak_rss_gb', 0))
    return w / 60, c / 60, r


def pct(res, plat, dim, h):
    ch = total(res, plat, dim, 'chunks')
    return 100 * total(res, plat, dim, 'block_diff') / (ch * 256 * h) if ch else 0


def starts(res, plat):
    eq = sum(total(res, plat, d, 'structure_starts_equal') for d in ('overworld', 'the_nether'))
    all_ = eq + sum(total(res, plat, d, k) for d in ('overworld', 'the_nether')
                    for k in ('structure_starts_diff', 'structure_starts_only_A'))
    return f'{eq} of {all_}'


subprocess.run(['python3', '-I', f'{HOME}/scripts/r3b_table.py'], check=True, capture_output=True)
tables = open(f'{R}/tables.html').read().split('</style>', 1)[1]

cols = [('vanilla2', 'Vanilla (2nd run)'), ('paper', 'Paper + Chunky'), ('hz069', 'Horizon 0.2.69'),
        ('hznew', 'Horizon with our fixes')]
rows = [
    ('Blocks different, Overworld', lambda p: f'{pct(R, p, "overworld", 384):.2f} %'),
    ('Blocks different, Nether', lambda p: f'{pct(R, p, "the_nether", 256):.2f} %'),
    ('Blocks different, End', lambda p: f'{total(R, p, "the_end", "block_diff"):,}'),
    ('Structure starts equal (Overworld + Nether)', lambda p: starts(R, p)),
    ('Same loot as vanilla', lambda p: '-' if p == 'vanilla2' else f'{loot(R, p):.1f} %'),
    ('Points of interest (vanilla: {})'.format(total(R, 'paper', 'overworld', 'poi_A')),
     lambda p: f'{total(R, p, "overworld", "poi_B"):,}'),
    ('End entities (vanilla: {})'.format(total(R, 'paper', 'the_end', 'entities_A')),
     lambda p: f'{total(R, p, "the_end", "entities_B")}'),
    ('Nether heightmap columns different', lambda p: f'{total(R, p, "the_nether", "heightmap_WORLD_SURFACE_diff"):,}'),
    ('Generation time / CPU / peak memory', lambda p: '{:.1f} min / {:.1f} min / {:.1f} GB'.format(*wall(p))),
]
summary = '<table><tr><th></th>' + ''.join(f'<th>{l}</th>' for _, l in cols) + '</tr>'
for name, f in rows:
    summary += f'<tr><td>{name}</td>' + ''.join(f'<td>{f(p)}</td>' for p, _ in cols) + '</tr>'
summary += '</table>'

before_after = [
    ('Blocks different, Overworld', f'{pct(R1, "hzrp", "overworld", 384):.2f} %', f'{pct(R, "hznew", "overworld", 384):.2f} %'),
    ('Blocks different, Nether', f'{pct(R1, "hzrp", "the_nether", 256):.2f} %', f'{pct(R, "hznew", "the_nether", 256):.2f} %'),
    ('Blocks different, End', f'{total(R1, "hzrp", "the_end", "block_diff"):,}', f'{total(R, "hznew", "the_end", "block_diff"):,}'),
    ('Same loot as vanilla', f'{loot(R1, "hzrp"):.1f} %', f'{loot(R, "hznew"):.1f} %'),
    ('Structure starts equal', starts(R1, 'hzrp'), starts(R, 'hznew')),
    ('Block entities missing, Overworld', f'{total(R1, "hzrp", "overworld", "be_only_A"):,}',
     f'{total(R, "hznew", "overworld", "be_only_A"):,}'),
]
ba = '<table><tr><th></th><th>RoyalPixels build of 26 Oct (first report)</th><th>With this round of fixes</th></tr>'
ba += ''.join(f'<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in before_after) + '</table>'

css = """<meta charset="utf-8"><title>Worldgen comparison: Vanilla, Paper, Horizon (3 seeds, third round)</title><style>
body{font:13px/1.45 system-ui,sans-serif;color:#1d1d1f;max-width:1000px;margin:28px auto;padding:0 20px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px}h3{font-size:14px;margin:20px 0 6px}
table{border-collapse:collapse;margin:6px 0 16px;width:100%}td,th{border:1px solid #ccc;padding:4px 8px;text-align:right}
td:first-child,th:first-child{text-align:left}th{background:#f0f0f2}.sub{color:#666}ul{padding-left:20px}
@media print{body{margin:0;max-width:none}h2{page-break-after:avoid}table{page-break-inside:avoid}}
</style>"""

# Animals with mob spawning on: same position / totals, against vanilla, and a second vanilla run.
def animal_stats(b):
    import importlib.util
    spec = importlib.util.spec_from_file_location('animals', f'{HOME}/scripts/animals.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    out = []
    for s in SEEDS:
        a = m.by_chunk(f'{HOME}/runs/mobs/vanilla-{s}/world', 15)
        bb = m.by_chunk(f'{HOME}/runs/mobs/{b}-{s}/world', 15)
        same = sum(len({x[:4] for x in a.get(c, [])} & {x[:4] for x in bb.get(c, [])}) for c in a)
        other = sum(1 for c in a.keys() | bb.keys()
                    if collections.Counter(x[0] for x in a.get(c, [])) != collections.Counter(x[0] for x in bb.get(c, [])))
        out.append((s, same, sum(map(len, a.values())), sum(map(len, bb.values())), other))
    return out
hz, v2 = animal_stats('horizon'), animal_stats('vanilla2')
animals = '<table><tr><th>Seed</th><th>Vanilla animals</th><th>Horizon: same position / total</th><th>Second vanilla run: same position / total</th><th>Chunks with other animals: Horizon / second vanilla run</th></tr>'
for (s, same, va, hb, o), (_, same2, _, vb, o2) in zip(hz, v2):
    animals += f'<tr><td>{s}</td><td>{va}</td><td>{same} / {hb}</td><td>{same2} / {vb}</td><td>{o} / {o2}</td></tr>'
animals += '</table>'

def gen_stats(path):
    d = json.load(open(path))['dims']
    return {k.split(':')[1]: (v['wall_s'], v['cpu_s']) for k, v in d.items()}
speed = '<table><tr><th>Seed</th><th>Paper + Chunky: wall / CPU seconds</th><th>Horizon /pregen: wall / CPU seconds</th></tr>'
tp = th = 0
for s in SEEDS:
    p = gen_stats(f'{HOME}/runs/r3-paper-{s}/stats.json')
    h = gen_stats(f'{HOME}/runs/perf/pregen-{s}/stats.json')
    pw, pc = sum(x[0] for x in p.values()), sum(x[1] for x in p.values())
    hw, hc = sum(x[0] for x in h.values()), sum(x[1] for x in h.values())
    tp, th = tp + pw, th + hw
    speed += f'<tr><td>{s}</td><td>{pw:.0f} / {pc:.0f}</td><td>{hw:.0f} / {hc:.0f}</td></tr>'
speed += f'<tr><td>Total</td><td>{tp:.0f} s</td><td>{th:.0f} s ({tp / th:.1f}x faster)</td></tr></table>'

body = open(f'{HOME}/scripts/report_r4_text.html').read()
html = css + (body.replace('{SUMMARY}', summary).replace('{BEFORE_AFTER}', ba)
              .replace('{ANIMALS}', animals).replace('{SPEED}', speed)) + '<h2>All numbers</h2>' + tables
open(f'{HOME}/report/report-r4.html', 'w').write(html)
subprocess.run([CHROME, '--no-sandbox', f'--print-to-pdf={HOME}/report/worldgen-comparison-3seeds-v3.pdf',
                '--no-pdf-header-footer', f'file://{HOME}/report/report-r4.html'], check=True, capture_output=True)
print(f'{HOME}/report/worldgen-comparison-3seeds-v3.pdf')
