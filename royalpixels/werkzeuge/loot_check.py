"""Roll vanilla's own LootTableSeed for every container and chest minecart, then compare with the items
the other world (Horizon) saved at the same place.

Usage: loot_check.py VANILLA_WORLD OTHER_WORLD RADIUS WORKDIR OUT.json
VANILLA_WORLD is copied to WORKDIR and opened with the vanilla 26.3 server; the original stays untouched.
"""
import collections, glob, json, os, queue, re, shutil, subprocess, sys, threading, time

sys.path.insert(0, os.path.dirname(__file__))
import compare as c

van, other, radius, work, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
DL = os.path.expanduser('~/worldgen-cmp/dl')
lo, hi = (-radius) >> 4, radius >> 4
DIMS = ['overworld', 'the_nether', 'the_end']


def containers(world, dim):
    res = {}
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/region/*.mca'):
        rx, rz = map(int, os.path.basename(f).split('.')[1:3])
        for (x, z), b in c.region(f).items():
            cx, cz = rx * 32 + x, rz * 32 + z
            ch = c.nbt(b)
            if not (lo <= cx <= hi and lo <= cz <= hi and c.is_full(ch)):
                continue
            for e in ch.get('block_entities', []):
                if 'LootTable' in e or e.get('Items'):
                    res[(e['x'], e['y'], e['z'])] = e
    return res


def minecarts(world, dim):
    res = {}
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/entities/*.mca'):
        for b in c.region(f).values():
            for e in c.nbt(b).get('Entities', []):
                if e.get('id') == 'minecraft:chest_minecart':
                    res[tuple(round(v, 1) for v in e['Pos'])] = e
    return res


def items(e):
    return sorted((i.get('Slot'), i['id'], i.get('count', 1), json.dumps(c.freeze(i.get('components')), default=str))
                  for i in e.get('Items', []))


before = {d: containers(van, d) for d in DIMS}
carts_before = {d: minecarts(van, d) for d in DIMS}
if os.path.abspath(f'{work}/world') != os.path.abspath(van):
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(van, f'{work}/world')
open(f'{work}/eula.txt', 'w').write('eula=true\n')
open(f'{work}/server.properties', 'w').write('online-mode=false\nserver-port=25619\nmax-tick-time=-1\n'
                                             'view-distance=4\nsimulation-distance=4\n')
p = subprocess.Popen([f'{DL}/jdk/bin/java', '-Xmx8G', '-jar', f'{DL}/mc/server-26.3.jar', 'nogui'], cwd=work,
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
q = queue.Queue()
threading.Thread(target=lambda: [q.put(l.decode(errors='replace')) for l in p.stdout], daemon=True).start()


def expect(pat, t=600):
    end = time.time() + t
    while time.time() < end:
        try:
            s = q.get(timeout=1)
        except queue.Empty:
            continue
        if m := re.search(pat, s):
            return m
    raise SystemExit('timeout ' + pat)


def send(s):
    p.stdin.write((s + '\n').encode())
    p.stdin.flush()


expect(r'Done \(')
send('gamerule random_tick_speed 0')
for d in DIMS:
    chunks = {(x >> 4, z >> 4) for x, _, z in before[d] if 'LootTable' in before[d][(x, _, z)]}
    chunks |= {(int(x) >> 4, int(z) >> 4) for x, _, z in carts_before[d]}
    for cx, cz in chunks:
        send(f'execute in minecraft:{d} run forceload add {cx * 16} {cz * 16}')
    for cx, cz in chunks:
        while True:
            send(f'execute in minecraft:{d} if loaded {cx * 16} 0 {cz * 16}')
            if expect(r'Test (passed|failed)').group(1) == 'passed':
                break
            time.sleep(0.2)
    time.sleep(2)
    for (x, y, z), e in before[d].items():
        if 'LootTable' in e:
            # reading a slot makes vanilla roll the chest's own LootTableSeed (RandomizableContainer.getItem)
            send(f'execute in minecraft:{d} run item replace block {x} {y} {z} container.0 from block {x} {y} {z} container.0')
    send(f'execute in minecraft:{d} as @e[type=chest_minecart] run item replace entity @s container.0 from entity @s container.0')
send('save-all flush')
expect(r'Saved the game')
send('stop')
p.wait(600)

res = {}
for d in DIMS:
    rolled, hz = containers(f'{work}/world', d), containers(other, d)
    st = collections.Counter()
    ex = []
    for pos, e in before[d].items():
        if 'LootTable' not in e:
            continue
        st[f'{e["id"]} vanilla_loot_table'] += 1
        h = hz.get(pos)
        if h is None:
            st[f'{e["id"]} missing_in_other'] += 1
            continue
        if 'LootTable' in h:
            same = h['LootTable'] == e['LootTable'] and h.get('LootTableSeed') == e.get('LootTableSeed')
            st[f'{e["id"]} other_kept_table_{"same" if same else "different"}'] += 1
            continue
        same = items(rolled.get(pos, {})) == items(h)
        st[f'{e["id"]} rolled_{"equal" if same else "different"}'] += 1
        if not same and len(ex) < 20:
            ex.append({'pos': pos, 'table': e['LootTable'], 'vanilla': items(rolled.get(pos, {})), 'other': items(h)})
    cr, ch = minecarts(f'{work}/world', d), minecarts(other, d)
    for pos, e in carts_before[d].items():
        h = ch.get(pos)
        if h is None:
            st['chest_minecart missing_in_other(pos)'] += 1
            continue
        if 'LootTable' in h:
            same = h['LootTable'] == e.get('LootTable') and h.get('LootTableSeed') == e.get('LootTableSeed')
            st[f'chest_minecart other_kept_table_{"same" if same else "different"}'] += 1
            continue
        same = items(cr.get(pos, {})) == items(h)
        st[f'chest_minecart rolled_{"equal" if same else "different"}'] += 1
        if not same and len(ex) < 40:
            ex.append({'pos': pos, 'table': e.get('LootTable'), 'vanilla': items(cr.get(pos, {})), 'other': items(h)})
    res[d] = {'stats': dict(sorted(st.items())), 'examples': ex}
    print(d, json.dumps(res[d]['stats']))
json.dump(res, open(out, 'w'), indent=1, default=str)
