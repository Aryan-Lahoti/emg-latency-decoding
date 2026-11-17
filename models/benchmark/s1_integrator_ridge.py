import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.path.insert(0, HERE)
from bench_lib import *
import pandas as pd, time
LAMS=np.logspace(-5,1,13)
cfgs={
 'lags_rms+mav100 (old)': lambda s,v: lag_features(s,v),
 'integ rms50 taus .05-.5': lambda s,v: integrator_features(s,v,taus=(0.05,0.15,0.5)),
 'integ rms50 taus .05-1.5': lambda s,v: integrator_features(s,v),
 'integ rms50 taus .05-4': lambda s,v: integrator_features(s,v,taus=(0.05,0.15,0.5,1.5,4.0)),
 'integ rms50 log .05-1.5': lambda s,v: integrator_features(s,v,log=True),
 'integ rms50 raw+log .05-1.5': lambda s,v: np.concatenate([integrator_features(s,v),integrator_features(s,v,log=True)],1),
}
rows=[]; t0=time.time()
for subj in range(1,13):
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    for name,fn in cfgs.items():
        d=splits(S,lambda s: fn(s,valid))
        best=min(((metrics(d['Yva'],ridge_pred(m,d['Xva'])),l) for m,l in zip(ridge_path(d['Xtr'],d['Ytr'],LAMS),LAMS)),key=lambda z:z[0][0].mean())
        (mae,r2),lam=best
        rows.append(dict(subject=subj,cfg=name,val_mae=mae.mean(),val_r2=r2.mean(),lam=lam,nfeat=d['Xtr'].shape[1]))
    print(subj,round(time.time()-t0),flush=True)
r=pd.DataFrame(rows); r.to_csv(os.path.join(ROOT,'results','benchmark','s1_val.csv'),index=False)
a=r[r.subject<=10]
print(a.groupby('cfg')[['val_mae','val_r2','nfeat']].mean().sort_values('val_mae').round(3).to_string())
print(r[r.subject>10].groupby('cfg')[['val_mae','val_r2']].mean().round(3).to_string())
