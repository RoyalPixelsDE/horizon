"""Parse the canonical NBT text the start oracle prints into (type, value) trees."""


def parse(s):
    v, i = _value(s, 0)
    assert i == len(s), (i, s[i:i + 40])
    return v


def _value(s, i):
    c = s[i]
    if c == '{':
        out, i = {}, i + 1
        while s[i] != '}':
            j = s.index(':', i)
            k = s[i:j]
            out[k], i = _value(s, j + 1)
            if s[i] == ',':
                i += 1
        return ('compound', out), i + 1
    if s.startswith('[I;', i) or s.startswith('[L;', i) or s.startswith('[B;', i):
        j = s.index(']', i)
        body = s[i + 3:j]
        return ('array' + s[i + 1], [int(x) for x in body.split(',')] if body else []), j + 1
    if c == '[':
        out, i = [], i + 1
        while s[i] != ']':
            v, i = _value(s, i)
            out.append(v)
            if s[i] == ',':
                i += 1
        return ('list', out), i + 1
    if c == '"':
        j, buf = i + 1, []
        while s[j] != '"':
            if s[j] == '\\':
                j += 1
            buf.append(s[j])
            j += 1
        return ('string', ''.join(buf)), j + 1
    j = i
    while j < len(s) and s[j] not in ',}]':
        j += 1
    tok = s[i:j]
    suffix = {'b': 'byte', 's': 'short', 'L': 'long', 'f': 'float', 'd': 'double'}.get(tok[-1])
    return ((suffix, int(tok[:-1])) if suffix else ('int', int(tok))), j


def plain(v):
    t, x = v
    if t == 'compound':
        return {k: plain(y) for k, y in x.items()}
    if t == 'list':
        return [plain(y) for y in x]
    return x
