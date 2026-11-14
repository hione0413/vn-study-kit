import json,sys,html,os
sys.stdout.reconfigure(encoding='utf-8')
out=sys.argv[1]; os.makedirs(out,exist_ok=True)
ko={}
for f in ('ko.tsv',):
    for l in open(f,encoding='utf-8'):
        l=l.rstrip('\n')
        if '\t' in l: w,m=l.split('\t',1); ko[w]=m
fix={'悶着':'もんちゃく','紅':'べに','額':'ひたい','紅葉':'もみじ','手々':'てて'}
words=json.load(open('vocab_words.json',encoding='utf-8'))
rows={};miss=[]
for ch in sorted(words,key=int):
    rows[ch]=[]
    for w,rd,p,c in words[ch]:
        if w not in ko: miss.append(w); continue
        rows[ch].append((w,fix.get(w,rd),ko[w],c))
print('missing(dropped):',len(miss),' '.join(miss)); print({ch:len(v) for ch,v in rows.items()}, sum(len(v) for v in rows.values()))
with open(os.path.join(out,'anki.tsv'),'w',encoding='utf-8') as f:
    for ch,v in rows.items():
        for w,rd,m,c in v: f.write('%s\t%s\t%s\tsnowglobe ch%s\n'%(w,rd,m,ch))
sec=''
for ch,v in rows.items():
    tr=''.join('<tr><td class="w" lang="ja">%s</td><td class="r" lang="ja">%s</td><td class="m">%s</td><td class="c">%s</td></tr>'%(html.escape(w),html.escape(rd),html.escape(m),c) for w,rd,m,c in v)
    sec+='<section id="ch%s"><h2>제%s장 <small>%d단어</small></h2><table><thead><tr><th>단어</th><th>읽기</th><th>뜻</th><th>횟수</th></tr></thead><tbody>%s</tbody></table></section>'%(ch,ch,len(v),tr)
nav='<div class="tabs" role="tablist">'+''.join('<button type="button" role="tab" data-ch="ch%s">%s장 <small>%d</small></button>'%(ch,ch,len(rows[ch])) for ch in rows)+'</div>'
page='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Snow Globe 단어장</title><style>
:root{--bg:#fbfaf7;--fg:#1f2328;--mut:#6b7280;--line:#e5e2da;--acc:#2f5d8a;--hide:#ece9e1}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--fg:#e6e6e6;--mut:#9aa0a6;--line:#2c3036;--acc:#8ab4e8;--hide:#262a30}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 "Malgun Gothic","Noto Sans KR",sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;z-index:2}
header .in,main{max-width:860px;margin:0 auto}h1{font-size:18px;margin:0 0 8px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.tabs{display:flex;flex-wrap:wrap;gap:6px;width:100%}.tabs button{font:inherit;color:var(--fg);background:transparent;border:1px solid var(--line);border-radius:6px;padding:4px 12px;cursor:pointer}
.tabs button small{color:var(--mut)}.tabs button[aria-selected=true]{background:var(--acc);border-color:var(--acc);color:var(--bg)}.tabs button[aria-selected=true] small{color:inherit}
section{display:none}section.show{display:block}
input[type=search]{flex:1;min-width:140px;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:transparent;color:inherit;font:inherit}
label{color:var(--mut);font-size:14px;white-space:nowrap}main{padding:8px 16px 60px}
h2{font-size:17px;margin:20px 0 8px}h2 small{color:var(--mut);font-weight:400}
table{width:100%;border-collapse:collapse}th{text-align:left;font-size:13px;color:var(--mut);font-weight:400;border-bottom:1px solid var(--line);padding:4px 8px}
td{padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}.w{font:20px "Yu Mincho","MS Mincho",serif;white-space:nowrap}
.r{font-family:"Yu Gothic","Meiryo",sans-serif;color:var(--acc);white-space:nowrap}.c{color:var(--mut);text-align:right;font-variant-numeric:tabular-nums}
body.hr .r,body.hm .m{color:transparent;background:var(--hide);border-radius:4px;cursor:pointer}body.hr .r.on,body.hm .m.on{color:inherit;background:none}
p.note{color:var(--mut);font-size:14px}
</style></head><body><header><div class="in"><h1>planetarian Snow Globe 단어장</h1><div class="bar">NAV<input type="search" id="q" placeholder="검색 (단어·읽기·뜻)"><label><input type="checkbox" id="hr"> 읽기 가리기</label><label><input type="checkbox" id="hm"> 뜻 가리기</label></div></div></header>
<main><p class="note">각 장에서 처음 나오는 N4 초과 한자어 TOTAL개입니다. 횟수는 작품 전체 등장 횟수입니다. 가린 칸은 누르면 보입니다. 검색하면 모든 장에서 찾습니다. 읽기와 뜻은 자동 분석을 바탕으로 한 사전적 풀이라 문맥에 따라 다를 수 있습니다.</p>SEC</main>
<script>
const q=document.getElementById('q'),tabs=[...document.querySelectorAll('.tabs button')],secs=[...document.querySelectorAll('section')];
let cur='ch1';try{cur=localStorage.getItem('sg-tab')||cur}catch(e){}
function render(){const k=q.value.trim().toLowerCase();
secs.forEach(s=>{let n=0;s.querySelectorAll('tbody tr').forEach(r=>{const ok=!k||r.textContent.toLowerCase().includes(k);r.style.display=ok?'':'none';if(ok)n++});
s.classList.toggle('show',k?n>0:s.id===cur)});
tabs.forEach(b=>b.setAttribute('aria-selected',!k&&b.dataset.ch===cur))}
tabs.forEach(b=>b.onclick=()=>{cur=b.dataset.ch;q.value='';try{localStorage.setItem('sg-tab',cur)}catch(e){}render();scrollTo(0,0)});
q.oninput=render;render();
for(const id of ['hr','hm'])document.getElementById(id).onchange=e=>{document.body.classList.toggle(id,e.target.checked);document.querySelectorAll('.on').forEach(x=>x.classList.remove('on'))};
document.querySelector('main').onclick=e=>{const t=e.target;if(t.matches('.r,.m'))t.classList.toggle('on')};
</script></body></html>'''.replace('NAV',nav).replace('SEC',sec).replace('TOTAL',str(sum(len(v) for v in rows.values())))
open(os.path.join(out,'단어장.html'),'w',encoding='utf-8').write(page)
