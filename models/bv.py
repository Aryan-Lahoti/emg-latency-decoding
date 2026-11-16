import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.argv=['x',DATA_DIR,__import__('tempfile').gettempdir(),'stateful','3']
src=open(os.path.join(MODELS,'experiments.py')).read().split('if EXP == "window_only"')[0]
exec(compile(src,'e','exec'))
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
rng=np.random.default_rng(0)
S={k:load(3,k) for k in (1,2)}; valid=S[1]['valid']&S[2]['valid']
P={k:build(S[k],100,HIST[1500],0,valid,False) for k in (1,2)}
X=np.concatenate([P[1][0],P[2][0]]); Y=np.concatenate([P[1][1],P[2][1]])
rep=np.concatenate([P[1][3],P[2][3]]); sess=np.concatenate([np.full(len(P[1][3]),1),np.full(len(P[2][3]),2)])
v=np.isin(rep,[9,10]); tr=~v
mu,sd=X[tr].mean(0),X[tr].std(0)+1e-12; Z=(X-mu)/sd; ym=Y[tr].mean(0); Yc=Y-ym
# blocks = (session, repetition) among training reps
blocks=[(s,r) for s in (1,2) for r in range(1,9)]
G={b:None for b in blocks}
for b in blocks:
    m=tr&(sess==b[0])&(rep==b[1]); G[b]=(Z[m].T@Z[m], Z[m].T@Yc[m], m.sum())
LAMS=np.logspace(-6,2,25); Zv=Z[v]; Yv=Y[v]; ntr=tr.sum()
def fit(gram,xy,n,lam): return np.linalg.solve(gram+lam*n*np.eye(gram.shape[0]),xy)
# train / validation error on full training set
full_g=sum(G[b][0] for b in blocks); full_xy=sum(G[b][1] for b in blocks)
tr_err=[];va_err=[];norms=[]
for lam in LAMS:
    W=fit(full_g,full_xy,ntr,lam)
    tr_err.append(np.mean((Z[tr]@W+ym-Y[tr])**2)); va_err.append(np.mean((Zv@W+ym-Yv)**2)); norms.append(np.linalg.norm(W))
# bootstrap over repetitions -> bias^2 / variance on validation frames
B=30; preds=np.zeros((B,len(LAMS))+Yv.shape,dtype=np.float32)
for i in range(B):
    pick=[blocks[j] for j in rng.integers(0,len(blocks),len(blocks))]
    g=sum(G[b][0] for b in pick); xy=sum(G[b][1] for b in pick); n=sum(G[b][2] for b in pick)
    for k,lam in enumerate(LAMS): preds[i,k]=Zv@fit(g,xy,n,lam)+ym
mean_p=preds.mean(0)
var=preds.var(0).mean(axis=(1,2)); bias2=((mean_p-Yv)**2).mean(axis=(1,2)); tot=((preds-Yv)**2).mean(axis=(0,2,3))
np.savez(os.path.join(ROOT,'results','followups','bv_out.npz'),LAMS=LAMS,var=var,bias2=bias2,tot=tot,tr=tr_err,va=va_err,norms=norms)
# --- 2-feature geometry: two most correlated envelope features (current snapshot only), index finger
nv=valid.sum(); cur=Z[tr][:, :2*nv]
C=np.corrcoef(cur.T); np.fill_diagonal(C,0); i,j=np.unravel_index(np.argmax(np.abs(C)),C.shape)
x2=cur[:,[i,j]]; y=Yc[tr][:,2]
g2=x2.T@x2/len(x2); b2=x2.T@y/len(x2)
ols=np.linalg.solve(g2,b2)
path=np.array([np.linalg.solve(g2+l*np.eye(2),b2) for l in np.logspace(-4,2,200)])
np.savez(os.path.join(ROOT,'results','followups','geo_out.npz'),g2=g2,b2=b2,ols=ols,path=path,corr=C[i,j],yy=np.mean(y**2),i=i,j=j,nv=nv)
print('corr',round(C[i,j],3),'ols',ols.round(2),'eig',np.linalg.eigvalsh(g2).round(3))
k=int(np.argmin(tot)); print('best lam (bootstrap total)',LAMS[k],'val best',LAMS[int(np.argmin(va_err))])
print('var range',var.min().round(2),var.max().round(2),'bias2 range',bias2.min().round(1),bias2.max().round(1))
