"""Summon mobs on two running servers (FIFO consoles from serve_new.sh / serve_hz.sh) and compare counts.

Usage: summon_check.py RUN_DIR_A RUN_DIR_B
Each check summons N mobs at the same spot and counts how many have a property, with `execute if entity`.
"""
import os, re, sys, time

runs = sys.argv[1:3]
SPOT = '8 90 8'
CHECKS = [
    # (label, entity, N, selector filter counted)
    ('pig sound variant other than classic', 'pig', 40, 'nbt=!{sound_variant:"minecraft:classic"}'),
    ('cow sound variant other than classic', 'cow', 40, 'nbt=!{sound_variant:"minecraft:classic"}'),
    ('cat sound variant other than classic', 'cat', 40, 'nbt=!{sound_variant:"minecraft:classic"}'),
    ('parrot variant other than red', 'parrot', 40, 'nbt=!{Variant:0}'),
    ('panda gene other than normal', 'panda', 40, 'nbt=!{MainGene:"normal"}'),
    ('goat screaming or missing a horn', 'goat', 100, 'nbt=!{IsScreamingGoat:0b,HasLeftHorn:1b,HasRightHorn:1b}'),
    ('creeper with the random spawn bonus', 'creeper', 20,
     'nbt={attributes:[{id:"minecraft:follow_range",modifiers:[{id:"minecraft:random_spawn_bonus"}]}]}'),
    ('skeleton left-handed', 'skeleton', 200, 'nbt={LeftHanded:1b}'),
    ('zombie PersistenceRequired', 'zombie', 20, 'nbt={PersistenceRequired:1b}'),
    ('piglin baby', 'piglin', 100, 'nbt={IsBaby:1b}'),
    ('zombified piglin baby', 'zombified_piglin', 200, 'nbt={IsBaby:1b}'),
    ('hoglin baby', 'hoglin', 100, 'nbt={Age:-24000}'),
    ('drowned with a nautilus shell', 'drowned', 300, 'nbt={equipment:{offhand:{id:"minecraft:nautilus_shell"}}}'),
    ('spider with an effect (Hard)', 'spider', 300, 'nbt={active_effects:[{}]}'),
    ('spider with a rider', 'spider', 0, 'nbt={Passengers:[{}]}'),
]


def log(run):
    return open(f'{run}/server.log', errors='replace').read().splitlines()


def send(run, *cmds):
    with open(f'{run}/console', 'w') as f:
        for c in cmds:
            f.write(c + '\n')


def ask(run, cmd, pat, timeout=60):
    n = len(log(run))
    send(run, cmd)
    t0 = time.time()
    while time.time() - t0 < timeout:
        for l in log(run)[n:]:
            m = re.search(pat, l)
            if m:
                return m
        time.sleep(0.3)
    return None


for run in runs:
    send(run, 'difficulty hard', 'time set midnight', 'gamerule spawn_mobs false', 'forceload add 0 0 15 15')
    while not (m := ask(run, 'execute if loaded 8 90 8', r'Test (passed|failed)')) or m.group(1) != 'passed':
        time.sleep(1)
    send(run, 'kill @e[type=!minecraft:player]')
    time.sleep(2)

print(f'{"check":42} ' + '  '.join(f'{os.path.basename(r):>14}' for r in runs))
for label, kind, n, flt in CHECKS:
    counts = []
    for run in runs:
        if n:
            send(run, 'kill @e[type=!minecraft:player]')
            time.sleep(1)
            send(run, *[f'summon minecraft:{kind} {SPOT}'] * n)
            time.sleep(3 + n / 100)
        total = ask(run, f'execute if entity @e[type=minecraft:{kind}]', r'Test passed[.,] [Cc]ount: (\d+)|Test failed')
        hit = ask(run, f'execute if entity @e[type=minecraft:{kind},{flt}]', r'Test passed[.,] [Cc]ount: (\d+)|Test failed')
        t = int(total.group(1)) if total and total.group(1) else 0
        h = int(hit.group(1)) if hit and hit.group(1) else 0
        counts.append(f'{h:>5} of {t:<5}')
    print(f'{label:42} ' + '  '.join(f'{c:>14}' for c in counts))
damage = []
for run in runs:
    send(run, 'kill @e[type=!minecraft:player]', 'summon minecraft:wither_skeleton 8 90 8')
    time.sleep(2)
    m = ask(run, 'attribute @e[type=minecraft:wither_skeleton,limit=1] minecraft:attack_damage base get', r'is ([\d.]+)')
    damage.append(m.group(1) if m else '?')
print(f'{"wither skeleton attack damage base":42} ' + '  '.join(f'{d:>14}' for d in damage))
