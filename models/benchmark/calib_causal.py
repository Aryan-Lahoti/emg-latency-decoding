import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.path.insert(0, HERE)
from bench_lib import *
from scipy.signal import lfilter
TAUS=(0.05,0.15,0.5,1.5,4.0)
def calibrated(s,valid,mode):
    e=s['rms_50'][:,valid]; le=np.log(e+1e-7)
    if mode=='none': return s
    if mode=='whole': g=np.exp(np.median(le,0))[None]
    if mode=='expanding':   # causal: running mean of log-envelope since sleeve-on (first 30 s use 30 s estimate)
        c=np.cumsum(le,0)/np.arange(1,len(le)+1)[:,None]; c[:3000]=c[3000]; g=np.exp(c)
    if mode=='slow_ema':    # causal: very slow EMA of log envelope, tau 120 s
        a=1-np.exp(-0.01/120); c=lfilter([a],[1,-(1-a)],le,axis=0,zi=le[:1]*(1-a))[0]; c[:3000]=c[3000]; g=np.exp(c)
    s2=dict(s); s2['rms_50']=s['rms_50'].copy(); s2['rms_50'][:,valid]=e/g; return s2
def feat(s,valid): return np.concatenate([integrator_features(s,valid,taus=TAUS),integrator_features(s,valid,taus=TAUS,log=True)],1)
res={}
for subj in range(1,13):
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    for mode in ('none','whole','expanding','slow_ema'):
        for a,b in ((1,2),(2,1)):
            A=calibrated(S[a],valid,mode); B=calibrated(S[b],valid,mode)
            m=ridge_path(feat(A,valid)[WARM:],S[a]['Y'][WARM:],[1e-3])[0]; e=ridge_pred(m,feat(B,valid)[WARM:])-S[b]['Y'][WARM:]
            res.setdefault((subj,mode),[]).append(np.abs(e).mean())
import pandas as pd
r=pd.DataFrame([dict(subject=k[0],mode=k[1],mae=np.mean(v)) for k,v in res.items()])
print(r.pivot(index='subject',columns='mode',values='mae').round(2).to_string()); print(r.groupby('mode').mae.mean().round(2))
