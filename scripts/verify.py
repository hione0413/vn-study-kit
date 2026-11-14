import sys,re
orig,new=sys.argv[1],sys.argv[2]
sys.argv=['x']
import furi
a=furi.Pak(orig); b=furi.Pak(new)
strip=lambda t: re.sub(r'\$\[(.*?)\$/.*?\$\]', r'\1', t)
bad=0;n=0;mx=0
for ch in range(1,8):
    for m,o in zip(furi.messages(b.files[ch]),furi.messages(a.files[ch])):
        n+=1; mx=max(mx,len(m[4]))
        if strip(m[4])!=strip(o[4]) or m[2:4]!=o[2:4]: bad+=1; print(repr(o[4][:40]),repr(m[4][:60]))
        # leftover bare kanji?
        if re.search('[\u4e00-\u9fff]', re.sub(r'\$\[.*?\$\]','',m[4])): print('bare', re.sub(r'\$\[.*?\$\]','',m[4])[:30])
print('lines',n,'mismatch',bad,'maxlen',mx, 'others same', all(a.files[i]==b.files[i] for i in (0,8,9,10,11,12,13,14,15,16,17)))
