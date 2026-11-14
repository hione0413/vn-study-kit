# -*- coding: utf-8 -*-
"""word window: shows reading and meaning of the words on the line the game is displaying.
run:  python wordwin.py          (window)
      python wordwin.py --probe  (look for script lines in game memory, diagnostics)
language and gloss files: see i18n.py
"""
import os, re, sys, struct, threading, time, collections, bisect

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_argv = sys.argv; sys.argv = ['wordwin']
import furi
sys.argv = _argv
import memscan
import i18n

FILES = os.path.join(os.path.dirname(HERE), 'files')
ORIG = os.path.join(FILES, 'SCRIPT.PAK.orig')
CUR = os.path.join(FILES, 'SCRIPT.PAK')
FIX = {'悶着': 'もんちゃく', '紅': 'べに', '額': 'ひたい', '紅葉': 'もみじ', '手々': 'てて', '私': 'わたし', '一日': 'いちにち'}
STRIP = re.compile(r'\$\[(.*?)\$/.*?\$\]', re.S)


def load_ko(name=None):
    ko = {}
    path = os.path.join(HERE, name or i18n.gloss_files(HERE)[0])
    if not os.path.exists(path):
        return ko
    for l in open(path, encoding='utf-8'):
        l = l.rstrip('\n')
        if '\t' in l:
            w, m = l.split('\t', 1); ko[w] = m
    return ko


def plain(t):
    t = STRIP.sub(lambda m: re.sub(r'\$[A-Za-z][0-9]*', '', m.group(1)), t)
    return re.sub(r'\$lang\([a-z]+\).*', '', t).replace('\n', '')


def build_lines():
    """one entry per message line, in play order. script text is kept in memory only (for matching)."""
    ko = load_ko(); basic = load_ko(i18n.gloss_files(HERE)[1])
    orig = furi.Pak(ORIG if os.path.exists(ORIG) else CUR)
    cur = furi.Pak(CUR)
    lines = []
    for ch in range(1, 8):
        om = list(furi.messages(orig.files[ch])); cm = list(furi.messages(cur.files[ch]))
        for n, (o, c) in enumerate(zip(om, cm)):
            words = []; seen = set()
            for w in furi.tagger(plain(o[4])):
                f = w.feature
                key = getattr(f, 'orthBase', None) or f.lemma
                if f.pos1 in ('助詞', '助動詞', '補助記号') or f.pos2 == '固有名詞':
                    continue
                if (key in ko or key in basic) and key not in seen:
                    seen.add(key)
                    rd = furi.hira(getattr(f, 'kanaBase', None) or getattr(f, 'kana', None) or '')
                    if rd == key:
                        rd = ''
                    words.append((key, FIX.get(key, rd), ko.get(key) or basic[key], key not in ko))
            lines.append({'ch': ch, 'n': n, 'total': len(om), 'z': o[2], 'voice': o[3], 'kind': furi.kind(o[4]),
                          'raw': c[4], 'raw0': o[4], 'plain': plain(o[4]), 'words': words})
    return lines


# ---------------------------------------------------------------- follow the running game
PC_RVA = 0x16a1ef8      # exe-relative address holding a pointer to the script instruction being shown


class Follower:
    """reads (never writes) the game's script cursor to learn which message line is on screen.
    the game keeps SCRIPT.PAK whole in memory; the cursor sits just past the instruction it last consumed,
    so the line on screen is the last message instruction that starts before the cursor."""

    def __init__(self, lines):
        self.lines = lines; self.proc = None; self.addr = None; self.base = None; self.last = None; self.next_try = 0
        self.raw = open(CUR, 'rb').read()
        pak = furi.Pak(CUR)
        self.files = []      # (pak offset, size, chapter, [message start offsets], first global line index)
        first = 0
        for i in range(pak.n):
            o, sz = struct.unpack('<2I', self.raw[pak.ent_off + i * 8:pak.ent_off + i * 8 + 8])
            spans = [(q, q + L) for q, L, op, fl in furi.walk(pak.files[i]) if op == 0x24] if 1 <= i <= 7 else []
            starts = [a for a, _ in spans]
            self.files.append((o * pak.bs, sz, i, starts, first, spans))
            if 1 <= i <= 7:
                first += len(starts)
        assert first == len(lines)

    def _attach(self):
        if time.time() < self.next_try:
            return False
        self.next_try = time.time() + 2
        pid = memscan.find_pid()
        if not pid:
            return False
        try:
            self.proc = memscan.Proc(pid)
            self.addr = memscan.module_base(self.proc) + PC_RVA
        except OSError:
            self.proc = None; return False
        self.base = None
        return True

    def _detach(self):
        if self.proc:
            self.proc.close()
        self.proc = None; self.base = None

    def _find_base(self, cur):
        # read backwards from the cursor (up to one PAK length) and look for the PAK header
        want = len(self.raw); chunk = self.proc.read(cur - want, want)
        if not chunk:      # part of that span is unreadable: take what is readable, 64KB at a time
            chunk = b''; step = 0x10000
            while len(chunk) < want:
                part = self.proc.read(cur - len(chunk) - step, step)
                if not part:
                    break
                chunk = part + chunk
        lo = cur - len(chunk)
        k = chunk.rfind(self.raw[:16])
        while k >= 0:
            if self.proc.read(lo + k, 256) == self.raw[:256]:
                return lo + k
            k = chunk.rfind(self.raw[:16], 0, k)
        return None

    def current(self):
        if not self.proc and not self._attach():
            return None, 'wait_game'
        raw = self.proc.read(self.addr, 8)
        if len(raw) < 8:
            self._detach(); return None, 'wait_game'
        cur = struct.unpack('<Q', raw)[0]
        if not cur:
            return self.last, 'wait_line'
        if self.base is None or not (self.base < cur <= self.base + len(self.raw)):
            self.base = self._find_base(cur)
            if self.base is None:
                return self.last, 'wait_hint'
        off = cur - self.base
        for o, sz, ch, starts, first, spans in self.files:
            if o <= off <= o + sz and starts:
                k = bisect.bisect_left(starts, off - o) - 1      # last message starting before the cursor
                # the game fetches the next message and then waits for the click, so a cursor that is still
                # inside (or exactly at the end of) message k means k is queued and k-1 is what is on screen
                if k >= 1 and off - o <= spans[k][1]:
                    k -= 1
                if k >= 0:
                    self.last = first + k
                elif self.last is None or self.lines[self.last]['ch'] != ch:
                    self.last = first
                return self.last, 'linked'
        return self.last, 'linked' if self.last is not None else 'wait_line'


# ---------------------------------------------------------------- probe
def probe(lines):
    pid = memscan.find_pid()
    if not pid:
        print('game not running'); return
    p = memscan.Proc(pid)
    for label, key in (('raw', 'raw'), ('plain', 'plain')):
        pref = collections.defaultdict(list)
        for i, l in enumerate(lines):
            t = l[key]
            if len(t) >= 6:
                pref[t[:10].encode('utf-16-le')].append(i)
        pat = re.compile(b'|'.join(re.escape(k) for k in sorted(pref, key=len, reverse=True)))
        t0 = time.time(); hits = collections.defaultdict(list); reg = collections.Counter(); regl = collections.defaultdict(set)
        for addr, m, base, size, typ in p.scan(pat):
            for i in pref[m.group(0)]:
                full = lines[i][key].encode('utf-16-le')
                if p.read(addr, len(full)) == full:
                    hits[i].append(addr); reg[(base, size, typ)] += 1; regl[(base, size, typ)].add(i)
        print('==', label, 'scan %.1fs' % (time.time() - t0), 'lines found', len(hits), 'of', len(lines))
        for (base, size, typ), c in sorted(reg.items()):
            ls = sorted(regl[(base, size, typ)])
            print('  region %x size %x type %x hits %d distinct %d lines %s..%s' % (base, size, typ, c, len(ls), ls[:6], ls[-6:]))
        cnt = collections.Counter({i: len(a) for i, a in hits.items()})
        print('  copies histogram', sorted(collections.Counter(cnt.values()).items()))
        top = [i for i, c in cnt.items() if c > min(cnt.values())] if cnt else []
        print('  lines with extra copies', sorted(top)[:40], '...' if len(top) > 40 else '')
        for i in sorted(top)[-5:]:
            print('   line', i, 'ch', lines[i]['ch'], 'n', lines[i]['n'], ['%x' % a for a in hits[i]])
    p.close()


if __name__ == '__main__':
    sys.stdout and sys.stdout.reconfigure(encoding='utf-8')
    L = build_lines()
    if '--probe' in sys.argv:
        probe(L)
    elif '--where' in sys.argv:
        f = Follower(L)
        for _ in range(int(sys.argv[sys.argv.index('--where') + 1]) if sys.argv[-1].isdigit() else 1):
            i, st = f.current()
            print(time.strftime('%H:%M:%S'), st, None if i is None else (L[i]['ch'], L[i]['n'] + 1, L[i]['kind'], len(L[i]['words'])))
            time.sleep(1)
    elif '--selftest' in sys.argv:
        print(len(L), sum(1 for l in L if l['words']), sum(len(l['words']) for l in L), sum(1 for l in L for w in l['words'] if w[3]))
        print(collections.Counter(len(l['words']) for l in L).most_common(8))
    else:
        import wordwin_ui
        wordwin_ui.run(L, Follower(L))
