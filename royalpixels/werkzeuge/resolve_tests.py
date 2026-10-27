"""Resolve a conflict where both sides added #[test] fns at the same place: keep HEAD's, then THEIRS' new ones.

Usage (in the repo, during a merge or rebase): resolve_tests.py FILE THEIRS_REF
"""
import re, subprocess, sys
p, theirs_ref = sys.argv[1:3]
s = open(p).read()
ms = list(re.finditer(r'<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n', s, re.S))
start = s.index('    #[test]\n<<<<<<< ')
end = ms[-1].end()
assert s[end:].startswith('    }\n'), 'unknown conflict'
end += len('    }\n')
show = lambda ref: subprocess.run(['git', 'show', f'{ref}:{p}'], capture_output=True, text=True).stdout
head, theirs = show('HEAD'), show(theirs_ref)
names = lambda src: re.findall(r'    #\[test\]\n    fn (\w+)\(\)', src)
def fn_text(src, name):
    i = src.index(f'    #[test]\n    fn {name}()'); j = src.index('\n    }\n', i) + len('\n    }\n'); return src[i:j]
region = s[start:end]
keep = [(head, n) for n in names(head) if f'fn {n}()' in region]
keep += [(theirs, n) for n in names(theirs) if f'fn {n}()' in region and n not in names(head)]
s = s[:start] + '\n'.join(fn_text(src, n) for src, n in keep) + s[end:]
open(p, 'w').write(s)
print('kept', [n for _, n in keep])
