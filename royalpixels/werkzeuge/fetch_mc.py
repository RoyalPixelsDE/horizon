"""Lay out a launcher-style game dir (versions/, libraries/, assets/) for one version, sha1-checked."""
import concurrent.futures as cf, hashlib, json, os, sys, urllib.request

ver, url, root = sys.argv[1], sys.argv[2], sys.argv[3]


def get(u, dest, sha1=None):
    if os.path.exists(dest) and (sha1 is None or hashlib.sha1(open(dest, 'rb').read()).hexdigest() == sha1):
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    data = urllib.request.urlopen(u).read()
    if sha1 and hashlib.sha1(data).hexdigest() != sha1:
        raise SystemExit(f'sha1 mismatch {u}')
    open(dest, 'wb').write(data)


vdir = f'{root}/versions/{ver}'
get(url, f'{vdir}/{ver}.json')
v = json.load(open(f'{vdir}/{ver}.json'))
jobs = [(v['downloads']['client']['url'], f'{vdir}/{ver}.jar', v['downloads']['client']['sha1']),
        (v['downloads']['server']['url'], f'{root}/server-{ver}.jar', v['downloads']['server']['sha1'])]
for lib in v['libraries']:
    a = lib.get('downloads', {}).get('artifact')
    if a:
        jobs.append((a['url'], f"{root}/libraries/{a['path']}", a['sha1']))
ai = v['assetIndex']
get(ai['url'], f"{root}/assets/indexes/{ai['id']}.json", ai['sha1'])
for o in json.load(open(f"{root}/assets/indexes/{ai['id']}.json"))['objects'].values():
    h = o['hash']
    jobs.append((f'https://resources.download.minecraft.net/{h[:2]}/{h}', f'{root}/assets/objects/{h[:2]}/{h}', h))
with cf.ThreadPoolExecutor(32) as ex:
    list(ex.map(lambda j: get(*j), jobs))
print('ok', len(jobs))
