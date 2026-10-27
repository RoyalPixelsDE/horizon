"""Pre-generate a square of all three dimensions on vanilla, Paper or Horizon and record time, CPU and RAM.

vanilla and horizon: forceload in 16x16-chunk batches over the console (same driver for both).
paper: Chunky.
Horizon only ticks a dimension with a player in it: for the Nether and End, a player who is online
(--player NAME) is teleported there.
"""
import argparse, json, os, queue, re, shutil, subprocess, threading, time

DL = os.path.expanduser('~/worldgen-cmp/dl')
JAVA = f'{DL}/jdk/bin/java'
HZ = os.environ.get('HZ_DIR', f'{DL}/hz/horizon-server-linux-x86_64')
HZ_RESOURCES = os.environ.get('HZ_RESOURCES', '')
DIMS = ['minecraft:overworld', 'minecraft:the_nether', 'minecraft:the_end']
RULES = {'random_tick_speed': 0, 'spawn_mobs': 'false', 'spawn_monsters': 'false', 'spawn_patrols': 'false',
         'spawn_phantoms': 'false', 'spawn_wandering_traders': 'false', 'spawn_wardens': 'false',
         'advance_time': 'false', 'advance_weather': 'false', 'mob_griefing': 'false',
         'spawner_blocks_work': 'false', 'spread_vines': 'false', 'fire_spread_radius_around_player': 0,
         'raids': 'false'}

ap = argparse.ArgumentParser()
ap.add_argument('platform', choices=['vanilla', 'paper', 'horizon'])
ap.add_argument('seed')
ap.add_argument('radius', type=int)
ap.add_argument('dir')
ap.add_argument('--port', type=int, default=25611)
ap.add_argument('--player')
ap.add_argument('--dims', default='0,1,2')
ap.add_argument('--boxes', help='sites JSON from sites.py: generate these chunk boxes instead of the square')
ap.add_argument('--inflight', type=int, default=32)
ap.add_argument('--pregen', action='store_true', help="horizon: its own /pregen instead of /forceload batches")
a = ap.parse_args()
a.dir = os.path.abspath(a.dir)



def setup():
    os.makedirs(a.dir, exist_ok=True)
    props = {'level-seed': a.seed, 'online-mode': 'false', 'server-port': a.port, 'view-distance': 4,
             'simulation-distance': 4, 'spawn-protection': 0, 'max-tick-time': -1, 'motd': 'worldgen-cmp'}
    if a.platform == 'horizon':
        if not os.path.exists(f'{a.dir}/server.toml'):
            subprocess.run([f'{HZ}/horizon-server', '--dir', a.dir, 'init', '--eula', '--world', 'world', '--seed',
                            a.seed, '--port', str(a.port), '--no-whitelist', '--offline', '--yes'], check=True)
            t = open(f'{a.dir}/server.toml').read()
            t = (t.replace('every = "6h"', 'every = "0"').replace('bind = "127.0.0.1:8130"', 'bind = ""')
                 .replace('restart_on_crash = true', 'restart_on_crash = false')
                 .replace('view_distance = 10', 'view_distance = 4')
                 .replace('simulation_distance = 10', 'simulation_distance = 4')
                 .replace('[properties]', '[properties]\nspawn-protection = 0'
                          + ('\nhorizon-pregen = true' if a.pregen else '')))
            if HZ_RESOURCES:
                t = t.replace('resources = ""', f'resources = "{HZ_RESOURCES}"')
            open(f'{a.dir}/server.toml', 'w').write(t)
        return [f'{HZ}/horizon-server', '--dir', a.dir, 'run']
    open(f'{a.dir}/eula.txt', 'w').write('eula=true\n')
    open(f'{a.dir}/server.properties', 'w').write(''.join(f'{k}={v}\n' for k, v in props.items()))
    jar = f'{DL}/mc/server-26.3.jar'
    if a.platform == 'paper':
        os.makedirs(f'{a.dir}/plugins', exist_ok=True)
        shutil.copy(f'{DL}/Chunky-Bukkit-1.5.3.jar', f'{a.dir}/plugins/')
        jar = f'{DL}/paper-26.3-223.jar'
    return [JAVA, '-Xms8G', '-Xmx8G', '-jar', jar, 'nogui']


lines = queue.Queue()
log = open(f'{a.dir}/driver.log' if os.path.isdir(a.dir) else '/dev/null', 'a')


def reader(p):
    for raw in p.stdout:
        s = raw.decode(errors='replace').rstrip()
        log.write(s + '\n')
        lines.put(s)
    lines.put(None)


def expect(pattern, timeout=600):
    end = time.time() + timeout
    while time.time() < end:
        try:
            s = lines.get(timeout=1)
        except queue.Empty:
            continue
        if s is None:
            raise SystemExit('server exited')
        if m := re.search(pattern, s):
            return m
    raise SystemExit(f'timeout waiting for {pattern}')


def tree_pids(root):
    pids, todo = [], [root]
    while todo:
        p = todo.pop()
        pids.append(p)
        try:
            todo += [int(c) for t in os.listdir(f'/proc/{p}/task')
                     for c in open(f'/proc/{p}/task/{t}/children').read().split()]
        except OSError:
            pass
    return pids


def sample(root):
    cpu = rss = 0
    for p in tree_pids(root):
        try:
            st = open(f'/proc/{p}/stat').read().rsplit(')', 1)[1].split()
            cpu += (int(st[11]) + int(st[12])) / os.sysconf('SC_CLK_TCK')
            rss += int(st[21]) * os.sysconf('SC_PAGE_SIZE')
        except OSError:
            pass
    return cpu, rss


cmd = setup()
log = open(f'{a.dir}/driver.log', 'a')
p = subprocess.Popen(cmd, cwd=a.dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
threading.Thread(target=reader, args=(p,), daemon=True).start()
peak = [0]


def watch():
    while p.poll() is None:
        peak[0] = max(peak[0], sample(p.pid)[1])
        time.sleep(1)


threading.Thread(target=watch, daemon=True).start()


def send(s):
    p.stdin.write((s + '\n').encode())
    p.stdin.flush()


t0 = time.time()
expect(r'Done \(')
stats = {'platform': a.platform, 'seed': a.seed, 'radius': a.radius, 'startup_s': round(time.time() - t0, 1),
         'dims': {}}
# Paper keeps game rules per dimension; vanilla and Horizon share one set, where this repeats harmlessly.
# GEN_SPAWN_MOBS keeps vanilla's default, so chunk generation places its animals (NaturalSpawner.spawnMobsForChunkGeneration).
rules = {k: v for k, v in RULES.items() if not (k == 'spawn_mobs' and os.environ.get('GEN_SPAWN_MOBS'))}
for k, v in rules.items():
    for dim in DIMS:
        send(f'execute in {dim} run gamerule {k} {v}')
# A seed generator ships chunks as generated (Chunky never ticks them): freeze, so no platform runs block, fluid
# and entity ticks that another, slower one would not have reached yet.
if not os.environ.get('GEN_TICKING'):
    send('tick freeze')

lo, hi = (-a.radius) >> 4, a.radius >> 4
square = [(lo, lo, hi, hi)]
boxes = {d: square for d in DIMS}
if a.boxes:
    boxes = {d: [] for d in DIMS}
    for site in json.load(open(a.boxes)).values():
        if site:
            boxes['minecraft:' + site['dim']].append(tuple(site['box']))
batches = {d: [(x, z, min(x + 15, b[2]), min(z + 15, b[3])) for b in bs
               for x in range(b[0], b[2] + 1, 16) for z in range(b[1], b[3] + 1, 16)] for d, bs in boxes.items()}


def forceload(dim):
    todo, inflight, done = list(batches[dim]), {}, 0
    while todo or inflight:
        while todo and len(inflight) < a.inflight:
            b = todo.pop(0)
            send(f'execute in {dim} run forceload add {b[0] * 16} {b[1] * 16} {b[2] * 16} {b[3] * 16}')
            inflight[b] = {(x, z) for x in range(b[0], b[2] + 1) for z in range(b[1], b[3] + 1)}
        time.sleep(0.5)
        asked = [(b, c) for b, cs in inflight.items() for c in sorted(cs)]
        for _, (x, z) in asked:
            send(f'execute in {dim} if loaded {x * 16} 0 {z * 16}')
        for b, c in asked:
            if expect(r'Test (passed|failed)', 300).group(1) == 'passed':
                inflight[b].discard(c)
        for b in [b for b, cs in inflight.items() if not cs]:
            send(f'execute in {dim} run forceload remove {b[0] * 16} {b[1] * 16} {b[2] * 16} {b[3] * 16}')
            del inflight[b]
            done += 1
        print(f'\r{dim} {done}/{len(batches[dim])} batches', end='', flush=True)
    print()


def pregen(dim):
    send(f'execute in {dim} run pregen start {a.radius} square 0 0')
    expect(rf'Pregenerating {dim}: (\d+) of \1 chunks', 7 * 86400)


def chunky(dim):
    world = {'minecraft:overworld': 'world', 'minecraft:the_nether': 'world_nether',
             'minecraft:the_end': 'world_the_end'}[dim]
    for c in [f'chunky world {world}', 'chunky shape square', 'chunky center 0 0', f'chunky radius {a.radius}',
              'chunky start']:
        send(c)
    expect(r'Task finished for ' + world, 7 * 86400)


for i in map(int, a.dims.split(',')):
    dim = DIMS[i]
    if a.platform == 'horizon' and i > 0 and a.player:
        send(f'gamemode spectator {a.player}')
        send(f'execute in {dim} run tp {a.player} 0 128 0')
        time.sleep(5)
    c0, w0 = sample(p.pid)[0], time.time()
    (chunky if a.platform == 'paper' else pregen if a.pregen else forceload)(dim)
    send('save-all flush')
    expect(r'Saved the game|ThreadedAnvilChunkStorage: All dimensions are saved|All dimensions are saved', 3600)
    stats['dims'][dim] = {'wall_s': round(time.time() - w0, 1), 'cpu_s': round(sample(p.pid)[0] - c0, 1),
                          'chunks': sum((b[2] - b[0] + 1) * (b[3] - b[1] + 1) for b in batches[dim])}
    print(stats['dims'][dim], flush=True)

send('stop')
p.wait(timeout=1800)
stats['peak_rss_gb'] = round(peak[0] / 2 ** 30, 2)
stats['total_wall_s'] = round(time.time() - t0, 1)
json.dump(stats, open(f'{a.dir}/stats.json', 'w'), indent=1)
print(json.dumps(stats))
