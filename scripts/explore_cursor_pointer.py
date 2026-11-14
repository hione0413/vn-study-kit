import sys,re,time,collections,struct,bisect
import numpy as np
D=sys.argv[1]; sys.path.insert(0,D)
sys.argv=['x']
import wordwin,memscan,furi
sys.stdout.reconfigure(encoding='utf-8')
pak=furi.Pak(wordwin.CUR)
p=memscan.Proc(memscan.find_pid())
t0=time.time()
regs=[(b,s,pr,t) for b,s,pr,t in p.regions()]
# 1) locate loaded chapter scripts
heads={ch:pak.files[ch][:48] for ch in range(1,8)}
blobs=[]
for b,s,pr,t in regs:
    if t!=0x20000: continue
    data=p.read(b,s)
    for ch,h in heads.items():
        k=data.find(h)
        while k>=0:
            full=p.read(b+k,len(pak.files[ch]))
            blobs.append((b+k,ch,full==pak.files[ch])); k=data.find(h,k+1)
print('blobs',[('%x'%a,ch,ok) for a,ch,ok in blobs],'%.1fs'%(time.time()-t0))
# 2) pointers into blobs
t0=time.time(); cands=[]
for b,s,pr,t in regs:
    if not (pr&0xCC): continue      # writable only
    data=p.read(b,s)
    if len(data)<8: continue
    a=np.frombuffer(data[:len(data)//8*8],dtype='<u8')
    for base,ch,ok in blobs:
        L=len(pak.files[ch])
        idx=np.nonzero((a>base)&(a<base+L))[0]
        for i in idx[:2000]:
            cands.append((b+int(i)*8,int(a[i])-base,base,ch))
print('pointer candidates',len(cands),'%.1fs'%(time.time()-t0))
for base,ch,ok in blobs:
    starts=[]; msgs=[]
    for q,L,op,fl in furi.walk(pak.files[ch]):
        starts.append(q)
        if op==0x24: msgs.append(q)
    S=set(starts)
    cs=[c for c in cands if c[2]==base]
    onb=[c for c in cs if c[1] in S]
    print('blob %x ch%d: %d ptrs, %d on instruction boundary'%(base,ch,len(cs),len(onb)))
    cnt=collections.Counter(c[1] for c in onb)
    for off,n in sorted(cnt.items())[:40]:
        mi=bisect.bisect_right(msgs,off)-1
        print('   off %d x%d  -> after msg #%d (msg at %s) addrs %s'%(off,n,mi,msgs[mi] if mi>=0 else None,' '.join('%x'%c[0] for c in onb if c[1]==off)[:120]))
