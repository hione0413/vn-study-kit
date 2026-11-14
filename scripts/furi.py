# -*- coding: utf-8 -*-
"""planetarian Snow Globe: add furigana (ruby) to every kanji in the Japanese script.
usage: furi.py <orig.pak> stats <out.tsv>
       furi.py <orig.pak> build <out.pak> [chapters e.g. 1,2,3]
       furi.py <orig.pak> vocab <out.json>
"""
import struct, sys, re, json, collections
import fugashi

sys.stdout and sys.stdout.reconfigure(encoding='utf-8')
NFILES_OFF = 4
tagger = fugashi.Tagger()

KANJI = r'一-鿿々〆ヶ'
RE_KANJI = re.compile('[' + KANJI + ']')
RE_MARK = re.compile(r'(\$\[.*?\$\]|\$lang\([a-z]+\).*|\$[A-Za-z][0-9]*|\n)', re.S)

# phrase-level fixes (names / readings the analyzer gets wrong). value: list of (base, reading) pieces
OVR = {}
def ovr(surface, *pieces):
    OVR[surface] = pieces
import importlib.util, os
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'overrides.py')
if os.path.exists(_p):
    spec = importlib.util.spec_from_file_location('overrides', _p)
    m = importlib.util.module_from_spec(spec); m.ovr = ovr; spec.loader.exec_module(m)
RE_OVR = re.compile('(' + '|'.join(sorted(map(re.escape, OVR), key=len, reverse=True)) + ')') if OVR else None


def hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def ruby(base, rd):
    return '$[' + base + '$/' + rd + '$]'


def align(surface, reading):
    """split surface into [(text, reading or None)] so only kanji runs carry ruby"""
    parts = re.findall('[' + KANJI + ']+|[^' + KANJI + ']+', surface)
    pat = ''
    for p in parts:
        if RE_KANJI.match(p):
            pat += '(.+?)'
        else:
            pat += re.escape(hira(p))
    m = re.fullmatch(pat, reading)
    if not m:
        return [(surface, reading)]
    out = []; gi = 1
    for p in parts:
        if RE_KANJI.match(p):
            out.append((p, m.group(gi))); gi += 1
        else:
            out.append((p, None))
    return out


def tokens(seg):
    """yield (surface, reading_hira or None, word)"""
    for w in tagger(seg):
        s = w.surface
        # fugashi drops whitespace; restore handled by caller via white_space
        rd = None
        if RE_KANJI.search(s):
            k = getattr(w.feature, 'kana', None)
            if k and k != '*':
                rd = hira(k)
                if s[0] == '言' and rd.startswith('ゆ'):
                    rd = 'い' + rd[1:]
        yield s, rd, w


def annotate_plain(seg, stats=None):
    out = ''
    pos = 0
    for s, rd, w in tokens(seg):
        i = seg.find(s, pos)
        if i < 0:
            raise RuntimeError('token lost: %r in %r' % (s, seg))
        out += seg[pos:i]; pos = i + len(s)
        if rd is None:
            if RE_KANJI.search(s) and stats is not None:
                stats[(s, '??')] += 1
            out += s
            continue
        if stats is not None:
            stats[(s, rd)] += 1
        for t, r in align(s, rd):
            out += ruby(t, r) if r else t
    out += seg[pos:]
    return out


def annotate(text, stats=None):
    res = ''
    for part in RE_MARK.split(text):
        if not part:
            continue
        if RE_MARK.fullmatch(part):
            res += part; continue
        subs = RE_OVR.split(part) if RE_OVR else [part]
        for sub in subs:
            if not sub:
                continue
            if sub in OVR:
                for t, r in OVR[sub]:
                    res += ruby(t, r) if r else t
            else:
                res += annotate_plain(sub, stats)
    return res


class Pak:
    def __init__(self, path):
        d = open(path, 'rb').read()
        self.hs, self.n, _, self.bs = struct.unpack('<4I', d[:16])
        self.head = bytearray(d[:self.hs])
        self.ent_off = 0x2c
        self.files = []
        for i in range(self.n):
            o, s = struct.unpack('<2I', d[self.ent_off + i * 8:self.ent_off + i * 8 + 8])
            self.files.append(d[o * self.bs:o * self.bs + s])

    def save(self, path):
        body = bytearray(); pos = self.hs
        assert pos % self.bs == 0
        for i, f in enumerate(self.files):
            struct.pack_into('<2I', self.head, self.ent_off + i * 8, pos // self.bs, len(f))
            body += f
            pad = (-len(f)) % self.bs
            body += b'\0' * pad
            pos += len(f) + pad
        open(path, 'wb').write(bytes(self.head) + bytes(body))


def walk(b):
    p = 0
    while p + 4 <= len(b):
        L, op, fl = struct.unpack('<HBB', b[p:p + 4])
        yield p, L, op, fl
        p += L + (L & 1)
    assert p == len(b), (p, len(b))


def messages(b):
    for p, L, op, fl in walk(b):
        if op == 0x24:
            a, z, v, sl = struct.unpack('<4H', b[p + 4:p + 12])
            yield p, L, z, v, b[p + 12:p + 12 + sl * 2].decode('utf-16-le')


def rebuild(b, fn):
    out = bytearray()
    for p, L, op, fl in walk(b):
        raw = b[p:p + L]
        if op == 0x24:
            sl = struct.unpack('<H', raw[10:12])[0]
            old = raw[12:12 + sl * 2].decode('utf-16-le')
            new = fn(old)
            if new != old:
                enc = new.encode('utf-16-le')
                raw = raw[:10] + struct.pack('<H', len(new)) + enc + raw[12 + sl * 2:]
                assert len(raw) < 65536
                raw = struct.pack('<H', len(raw)) + raw[2:]
        out += raw
        if len(raw) & 1:
            out += b'\0'
    return bytes(out)


def kind(t):
    t = t.lstrip('　 ')
    return 'D' if t[:1] in '「『' else 'T' if t[:1] in '（(' else 'N'


if __name__ == '__main__':
    pak = Pak(sys.argv[1]); mode = sys.argv[2]
    if mode == 'stats':
        st = collections.Counter()
        for ch in range(1, 8):
            for p, L, z, v, t in messages(pak.files[ch]):
                annotate(t, st)
        with open(sys.argv[3], 'w', encoding='utf-8') as f:
            for (s, r), n in sorted(st.items(), key=lambda x: -x[1]):
                f.write('%s\t%s\t%d\n' % (s, r, n))
        print(len(st), sum(st.values()))
    elif mode == 'build':
        chs = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else range(1, 8)
        for ch in chs:
            old = pak.files[ch]
            pak.files[ch] = rebuild(old, annotate)
            # sanity: same instruction count, same non-message bytes
            a = [(op, fl) for _, _, op, fl in walk(old)]; b2 = [(op, fl) for _, _, op, fl in walk(pak.files[ch])]
            assert a == b2
            print('chapter', ch, len(old), '->', len(pak.files[ch]))
        pak.save(sys.argv[3])
    elif mode == 'vocab':
        res = []
        for ch in range(1, 8):
            for p, L, z, v, t in messages(pak.files[ch]):
                plain = re.sub(r'\$\[(.*?)\$/.*?\$\]', lambda m: re.sub(r'\$[A-Za-z][0-9]*', '', m.group(1)), t)
                plain = re.sub(r'\$lang\([a-z]+\).*', '', plain).replace('\n', '')
                for w in tagger(plain):
                    f = w.feature
                    res.append((ch, w.surface, f.lemma, f.pos1, f.pos2, getattr(f, 'kanaBase', None) or getattr(f, 'kana', None), getattr(f, 'orthBase', None)))
        json.dump(res, open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False)
        print(len(res))
