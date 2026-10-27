"""What a fresh world saves around one force-loaded chunk: the status, light and entity count of chunks -4..4.

Usage: forced_rings.py vanilla|horizon SEED DIR [PORT]
Runs a dedicated server with no player, `forceload add 0 0`, waits until 0,0 is loaded and 200 more ticks, saves, stops,
and prints the saved chunks as a 9x9 grid of status letters (F full, L light, I initialize_light, S spawn, f features,
t terrain, b biomes, s structure_starts/references, . not saved), plus isLightOn of the full ones.
"""
import os, re, shutil, subprocess, sys, threading, time

sys.path.insert(0, os.path.expanduser('~/worldgen-cmp/scripts'))
import compare as c

H = os.path.expanduser('~/worldgen-cmp')
plat, seed, d = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3])
port = sys.argv[4] if len(sys.argv) > 4 else '25640'
shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
if plat == 'horizon':
    hz = f'{H}/dl/hz-next/bin'
    subprocess.run([f'{hz}/horizon-server', '--dir', d, 'init', '--eula', '--world', 'world', '--seed', seed, '--port', port,
                    '--no-whitelist', '--offline', '--yes'], check=True, capture_output=True)
    t = open(f'{d}/server.toml').read().replace('every = "6h"', 'every = "0"').replace('bind = "127.0.0.1:8130"', 'bind = ""')
    res = os.path.expanduser('~/projects/royalpixels/horizon/.local/horizon-client/26.3')
    open(f'{d}/server.toml', 'w').write(t.replace('resources = ""', f'resources = "{res}"'))
    cmd = [f'{hz}/horizon-server', '--dir', d, 'run']
else:
    open(f'{d}/eula.txt', 'w').write('eula=true\n')
    open(f'{d}/server.properties', 'w').write(f'level-seed={seed}\nonline-mode=false\nserver-port={port}\n')
    cmd = [f'{H}/dl/jdk/bin/java', '-Xmx3G', '-jar', f'{H}/dl/mc/server-26.3.jar', 'nogui']
p = subprocess.Popen(cmd, cwd=d, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
lines = []
threading.Thread(target=lambda: [lines.append(l) for l in p.stdout], daemon=True).start()


def send(s):
    p.stdin.write(s + '\n'); p.stdin.flush()


def wait(pat, after=0, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        for l in lines[after:]:
            if re.search(pat, l):
                return l
        time.sleep(0.5)
    sys.exit(f'timeout waiting for {pat}\n' + ''.join(lines[-15:]))


wait(r'Done \(')
send('forceload add 0 0')
for i in range(600):
    n = len(lines)
    send('execute if loaded 0 0 0')
    if 'passed' in wait(r'Test (passed|failed)', n):
        break
    time.sleep(1)
def gametime():
    n = len(lines); send('time query gametime')
    return int(re.search(r'time is (\d+)', wait(r'time is \d+', n)).group(1))


g0 = gametime()
while gametime() < g0 + 200:
    time.sleep(1)
send('save-all flush'); time.sleep(5); send('stop'); p.wait(120)

letter = {'full': 'F', 'light': 'L', 'initialize_light': 'I', 'spawn': 'S', 'features': 'f', 'carvers': 'c', 'surface': 'u',
          'noise': 'n', 'biomes': 'b', 'structure_references': 's', 'structure_starts': 's', 'empty': 'e'}
chunks = c.region(f'{d}/world/dimensions/minecraft/overworld/region/r.0.0.mca')
chunks.update({(x - 32, z): v for (x, z), v in c.region(f'{d}/world/dimensions/minecraft/overworld/region/r.-1.0.mca').items()})
chunks.update({(x, z - 32): v for (x, z), v in c.region(f'{d}/world/dimensions/minecraft/overworld/region/r.0.-1.mca').items()})
chunks.update({(x - 32, z - 32): v for (x, z), v in c.region(f'{d}/world/dimensions/minecraft/overworld/region/r.-1.-1.mca').items()})
print(f'{plat} seed {seed}: z down, x right, chunks -4..4 (letter, then * if full but isLightOn 0)')
for z in range(-4, 5):
    row = []
    for x in range(-4, 5):
        raw = chunks.get((x, z))
        if raw is None:
            row.append(' .'); continue
        ch = c.nbt(raw)
        st = ch.get('Status', '').split(':')[-1]
        row.append(letter.get(st, '?') + ('*' if st == 'full' and ch.get('isLightOn') != 1 else ' '))
    print(''.join(row))
