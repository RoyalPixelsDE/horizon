"""Locate the nearest site of every structure kind on a fresh world and write chunk boxes around them.

Usage: sites.py vanilla|horizon SEED OUT.json
"""
import json, os, re, subprocess, sys, tempfile, time

DL = os.path.expanduser('~/worldgen-cmp/dl')
HZ = f'{DL}/hz/horizon-server-linux-x86_64'
platform, seed, out = sys.argv[1:4]
OVER = ['village_plains', 'village_desert', 'village_savanna', 'village_snowy', 'village_taiga', 'pillager_outpost',
        'mansion', 'monument', 'desert_pyramid', 'jungle_pyramid', 'swamp_hut', 'igloo', 'shipwreck',
        'shipwreck_beached', 'buried_treasure', 'ocean_ruin_cold', 'ocean_ruin_warm', 'ruined_portal',
        'ruined_portal_desert', 'ruined_portal_ocean', 'stronghold', 'ancient_city', 'trail_ruins', 'trial_chambers',
        'mineshaft', 'mineshaft_mesa', 'abandoned_camp_forest', 'abandoned_camp_taiga', 'abandoned_camp_savanna']
NETHER = ['fortress', 'bastion_remnant', 'ruined_portal_nether', 'nether_fossil']
END = ['end_city']
# chunk radius of the box: big structures get more room
BIG = {'mansion': 5, 'ancient_city': 5, 'monument': 4, 'stronghold': 5, 'end_city': 5, 'fortress': 5,
       'bastion_remnant': 4, 'trial_chambers': 5, 'village_plains': 4, 'village_desert': 4, 'village_savanna': 4,
       'village_snowy': 4, 'village_taiga': 4}

d = tempfile.mkdtemp(prefix='sites-')
if platform == 'horizon':
    subprocess.run([f'{HZ}/horizon-server', '--dir', d, 'init', '--eula', '--world', 'world', '--seed', seed,
                    '--port', '25615', '--no-whitelist', '--offline', '--yes'], check=True, capture_output=True)
    t = open(f'{d}/server.toml').read().replace('every = "6h"', 'every = "0"').replace('bind = "127.0.0.1:8130"', 'bind = ""')
    open(f'{d}/server.toml', 'w').write(t)
    cmd = [f'{HZ}/horizon-server', '--dir', d, 'run']
else:
    open(f'{d}/eula.txt', 'w').write('eula=true\n')
    open(f'{d}/server.properties', 'w').write(f'level-seed={seed}\nonline-mode=false\nserver-port=25615\nmax-tick-time=-1\n')
    cmd = [f'{DL}/jdk/bin/java', '-Xmx3G', '-jar', f'{DL}/mc/server-26.3.jar', 'nogui']
p = subprocess.Popen(cmd, cwd=d, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def line_until(pat):
    for line in p.stdout:
        if m := re.search(pat, line):
            return m
    raise SystemExit('server exited')


line_until(r'Done \(')
res = {}
for dim, names in (('overworld', OVER), ('the_nether', NETHER), ('the_end', END)):
    for n in names:
        p.stdin.write(f'execute in minecraft:{dim} run locate structure minecraft:{n}\n')
        p.stdin.flush()
        m = line_until(r'nearest minecraft:\S+ is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find|There is no structure')
        if m.group(1) is None:
            res[n] = None
            continue
        x, z = int(m.group(1)), int(m.group(2))
        r = BIG.get(n, 3)
        res[n] = {'dim': dim, 'x': x, 'z': z, 'box': [(x >> 4) - r, (z >> 4) - r, (x >> 4) + r, (z >> 4) + r]}
        print(n, res[n], flush=True)
p.stdin.write('stop\n')
p.stdin.flush()
p.wait(120)
json.dump(res, open(out, 'w'), indent=1)
