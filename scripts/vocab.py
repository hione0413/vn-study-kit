import json,csv,sys,re,collections
sys.stdout.reconfigure(encoding='utf-8')
known=set()
for n in (5,4):
    for r in csv.DictReader(open('dl/n%d.csv'%n,encoding='utf-8')):
        known.add(r['expression']); known.add(r['reading'])
def hira(s): return ''.join(chr(ord(c)-0x60) if '\u30a1'<=c<='\u30f6' else c for c in s)
raw=json.load(open('vocab_raw.json',encoding='utf-8'))
POS={'名詞','動詞','形容詞','形状詞','副詞','連体詞','接続詞'}
seen={};cnt=collections.Counter()
for ch,surf,lemma,p1,p2,kana,orth in raw:
    if p1 not in POS or p2 in ('数詞','非自立可能') and p1!='動詞': 
        if not(p1=='名詞' and p2=='普通名詞'): continue
    w=orth or lemma
    if not w or w=='*' : continue
    if not re.search('[\u4e00-\u9fff]',w): continue   # kanji words only (kana words are readable)
    rd=hira(kana or '')
    if w in known or rd in known or lemma.split('-')[0] in known: continue
    if p2=='固有名詞': continue
    cnt[w]+=1
    seen.setdefault(w,(ch,rd,p1))
by=collections.defaultdict(list)
for w,(ch,rd,p1) in seen.items(): by[ch].append((w,rd,p1,cnt[w]))
print({ch:len(v) for ch,v in sorted(by.items())}, len(seen))
json.dump({str(ch):v for ch,v in by.items()},open('vocab_words.json','w',encoding='utf-8'),ensure_ascii=False)
for ch in sorted(by): open('words_ch%d.txt'%ch,'w',encoding='utf-8').write('\n'.join('%s\t%s'%(w,rd) for w,rd,_,_ in by[ch]))
