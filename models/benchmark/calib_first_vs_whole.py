import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.path.insert(0, HERE)
from bench_lib import *
TAUS=(0.05,0.15,0.5,1.5,4.0)
def calibrated(s,valid,mode,n_cal=6000):
    e=s['rms_50'][:,valid]
    if mode=='none': g=np.ones(e.shape[1])
    else:
        ref=e[:n_cal] if mode=='first60s' else e
        g=np.median(ref,0)                     # per-electrode gain from unlabelled data
    s2=dict(s); s2['rms_50']=s['rms_50'].copy(); s2['rms_50'][:,valid]=e/g
    return s2
def feat(s,valid): return np.concatenate([integrator_features(s,valid,taus=TAUS),integrator_features(s,valid,taus=TAUS,log=True)],1)
res={}
for subj in range(1,13):
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    for mode in ('none','first60s','whole'):
        for a,b in ((1,2),(2,1)):
            A=calibrated(S[a],valid,mode); B=calibrated(S[b],valid,mode)
            X1=feat(A,valid)[WARM:]; Y1=S[a]['Y'][WARM:]; X2=feat(B,valid)[WARM:]; Y2=S[b]['Y'][WARM:]
            m=ridge_path(X1,Y1,[1e-3])[0]; e=ridge_pred(m,X2)-Y2
            res.setdefault((subj,mode),[]).append(np.abs(e).mean())
import pandas as pd
r=pd.DataFrame([dict(subject=k[0],mode=k[1],mae=np.mean(v)) for k,v in res.items()])
print(r.pivot(index='subject',columns='mode',values='mae').round(2).to_string()); print(r.groupby('mode').mae.mean().round(2))
