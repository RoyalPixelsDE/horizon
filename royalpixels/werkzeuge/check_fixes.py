"""Report the save-format criteria the Horizon fixes target, for one world.

Usage: check_fixes.py WORLD
"""
import collections, glob, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import compare as c

world = sys.argv[1]
MIN_SECTION = {'overworld': -4, 'the_nether': 0, 'the_end': 0}
out = {}
for dim, lo in MIN_SECTION.items():
    st = collections.Counter()
    tops = []
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/region/*.mca'):
        for b in c.region(f).values():
            ch = c.nbt(b)
            full = c.is_full(ch)
            st['chunks_full' if full else 'chunks_proto'] += 1
            st[f'yPos={ch.get("yPos")}'] += 1
            ys = [s['Y'] for s in ch.get('sections', [])]
            if ys and (min(ys) < lo or max(ys) >= lo + (24 if dim == 'overworld' else 16)):
                st['sections_outside_level'] += 1
            for e in ch.get('block_entities', []):
                if 'id' not in e:
                    st['block_entity_without_id'] += 1
                    continue
                if e['id'] == 'minecraft:trial_spawner':
                    sd = e.get('spawn_data')
                    st['trial_spawner_' + ('no_spawn_data' if sd is None else
                                           'with_mob' if 'id' in sd.get('entity', {}) else 'EMPTY_spawn_data')] += 1
                if 'LootTable' in e:
                    st['container_loot_table'] += 1
                elif e.get('Items') and e['id'] in ('minecraft:chest', 'minecraft:barrel', 'minecraft:dispenser',
                                                     'minecraft:trapped_chest'):
                    st['container_prerolled_items'] += 1
            if full:
                s = ch.get('structures', {})
                st['structure_starts'] += sum(1 for v in s.get('starts', {}).values() if v.get('id', 'INVALID') != 'INVALID')
                st['chunks_with_references'] += bool(s.get('References'))
                hm = ch.get('Heightmaps', {}).get('WORLD_SURFACE')
                if hm is not None:
                    a = np.frombuffer(hm[1], '>u8').astype(np.uint64)
                    vals = np.stack([(a >> np.uint64(j * 9)) & np.uint64(511) for j in range(7)], 1).reshape(-1)[:256]
                    tops.append(int(vals.max()) + lo * 16 - 1)
    for f in glob.glob(f'{world}/dimensions/minecraft/{dim}/entities/*.mca'):
        for b in c.region(f).values():
            for e in c.nbt(b).get('Entities', []):
                if e.get('id') == 'minecraft:chest_minecart':
                    st['minecart_' + ('loot_table' if 'LootTable' in e else 'prerolled')] += 1
    st['poi_region_files'] = len(glob.glob(f'{world}/dimensions/minecraft/{dim}/poi/*.mca'))
    if tops:
        st['highest_surface_y'] = max(tops)
    out[dim] = dict(sorted(st.items()))
    print(dim, json.dumps(out[dim]))
