"""RAM of a server running a finished vanilla world: idle, then with a player-sized area force-loaded.

Usage: ram_idle.py vanilla|paper|horizon OUT_DIR
Copies the server folder of runs/r3-<platform>-12345 and puts a copy of the vanilla-made world in it.
"""
import os, re, shutil, subprocess, sys, threading, time

H = os.path.expanduser('~/worldgen-cmp')
plat, out = sys.argv[1], os.path.abspath(sys.argv[2])
src = {'vanilla': 'r3-vanilla-12345', 'paper': 'r3-paper-12345', 'horizon': 'r3-hznew-12345'}[plat]
shutil.rmtree(out, ignore_errors=True)
shutil.copytree(f'{H}/runs/{src}', out, ignore=shutil.ignore_patterns('world', 'logs', 'cache'))
shutil.copytree(f'{H}/runs/r3-vanilla-12345/world', f'{out}/world')
java = f'{H}/dl/jdk/bin/java'
cmd = {
    'vanilla': [java, '-Xmx4G', '-jar', f'{H}/dl/mc/server-26.3.jar', 'nogui'],
    'paper': [java, '-Xmx4G', '-jar', f'{H}/dl/paper-26.3-223.jar', 'nogui'],
    'horizon': [f'{H}/dl/hz-next/bin/horizon-server', '--dir', out, 'run'],
}[plat]
p = subprocess.Popen(cmd, cwd=out, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
lines = []
threading.Thread(target=lambda: [lines.append(l.decode(errors='replace')) for l in p.stdout], daemon=True).start()


def rss():
    total, todo = 0, [p.pid]
    while todo:
        pid = todo.pop()
        try:
            total += int(re.search(r'VmRSS:\s+(\d+)', open(f'/proc/{pid}/status').read()).group(1))
            todo += [int(c) for c in open(f'/proc/{pid}/task/{pid}/children').read().split()]
        except (OSError, AttributeError):
            pass
    return total / 2 ** 20


def send(s):
    p.stdin.write((s + '\n').encode()); p.stdin.flush()


def sample(seconds):
    vals = []
    for _ in range(seconds // 2):
        vals.append(rss()); time.sleep(2)
    return vals[-1], max(vals)


t0 = time.time()
while not any('Done (' in l for l in lines):
    if time.time() - t0 > 300 or p.poll() is not None:
        sys.exit(f'{plat}: no Done\n' + ''.join(lines[-20:]))
    time.sleep(1)
idle = sample(60)
send('forceload add -128 -128 127 127')
loaded = sample(90)
send('stop')
p.wait(120)
print(f'{plat}: idle {idle[0]:.2f} GB (peak {idle[1]:.2f}), 16x16 chunks loaded {loaded[0]:.2f} GB (peak {loaded[1]:.2f})')
