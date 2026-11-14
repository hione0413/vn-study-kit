import sys,re,time,collections
D=sys.argv[1]; sys.path.insert(0,D)
sys.argv=['x']
import wordwin,memscan
sys.stdout.reconfigure(encoding='utf-8')
L=wordwin.build_lines()
p=memscan.Proc(memscan.find_pid())
# one kana fragment (>=5 chars) from each of the first 25 lines of chapter 1
frags=[]
for i,l in enumerate(L[:25]):
    m=re.search(r'[\u3041-\u3096\u30a1-\u30fa\u30fc]{5,}',l['plain'])
    if m: frags.append((i,m.group(0)[:7]))
print('fragments for lines',[i for i,_ in frags])
t0=time.time(); res=collections.defaultdict(list); nreg=0; nbytes=0
encs=('utf-16-le','utf-8','shift_jis','utf-32-le')
pats=[(i,e,f.encode(e)) for i,f in frags for e in encs]
for base,size,prot,typ in p.regions():
    data=p.read(base,size)
    if not data: continue
    nreg+=1; nbytes+=len(data)
    for i,e,b in pats:
        k=data.find(b)
        while k>=0:
            res[(e,i)].append((base+k,base,size,typ,prot)); k=data.find(b,k+1)
print('scanned regions',nreg,'MB',nbytes>>20,'%.1fs'%(time.time()-t0))
for e in encs:
    ks=sorted(i for (ee,i) in res if ee==e)
    print('==',e,'lines found',ks)
    for i in ks:
        print('   line',i,' '.join('%x(r%x,sz%x,t%x,p%x)'%h for h in res[(e,i)][:6]))
