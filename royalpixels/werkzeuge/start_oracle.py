"""Run Horizon's VanillaStructureStartOracle with HORIZON_START_NBT for every site in a sites JSON.

Usage: start_oracle.py SITES.json SEED OUT.txt   (run from the Horizon checkout, JDK 25 on PATH)
"""
import json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, 'tools')
import lab, oracle_harness as oh, test_rust_parity as base, test_model_baking_parity as baking

sites, seed, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]).resolve()
lock, jars, _ = base.verify_artifacts()
build = lab.LOCAL / 'start-oracle'
build.mkdir(exist_ok=True)
classes, deps, _ = oh.compile_oracle(build, 'VanillaStructureStartOracle', jars, baking.client_libraries(),
                                     lock['minecraft']['java_major'])
lines = []
for name, s in json.load(open(sites)).items():
    if not s:
        continue
    cx, cz = s['x'] >> 4, s['z'] >> 4
    part = build / f'{name}.txt'
    env = dict(os.environ, HORIZON_START_NBT='1', HORIZON_DIMENSION=s['dim'])
    subprocess.run(['java', '-Xmx2g', '-cp', f'{classes}{os.pathsep}{deps}', 'dev.horizonlab.parity.VanillaStructureStartOracle',
                    str(part), seed, str(cx - 1), str(cz - 1), str(cx + 1), str(cz + 1)], check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    got = [l for l in part.read_text().splitlines() if l.startswith(('start ', 'nbt '))]
    lines += [f'== {name} {s["dim"]}'] + got
    print(name, sum(l.startswith('nbt') for l in got), flush=True)
out.write_text('\n'.join(lines) + '\n')
