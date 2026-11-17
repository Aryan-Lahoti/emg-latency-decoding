import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.argv=['x',DATA_DIR,__import__('tempfile').gettempdir(),'stateful','1']
src=open(os.path.join(MODELS,'experiments.py')).read().split('if EXP == "window_only"')[0]
exec(compile(src,'e','exec'))
import numpy as np, pandas as pd
rng=np.random.default_rng(0)
rows=[]
for subj in range(1,13):
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    for k in (1,2,3):  # RMS only, like the latest models
        S[k]={**S[k], 'mav_100':S[k]['rms_100'][:,:0] if False else S[k]['mav_100']}
    Y3=S[3]['Y']; ph3=S[3]['phase']; rs=load(subj,3)
    # --- label-noise floors on session 3 itself (no model) ---
    T=len(Y3); idx=np.arange(200,T-200)
    for sig in (50,100,200):
        d=np.clip(np.round(rng.normal(0,sig/10,len(idx))).astype(int),-150,150)
        rows.append(dict(subject=subj,what=f'floor_timing_jitter_{sig}ms',mae=np.abs(Y3[idx+d]-Y3[idx]).mean()))
    restm=ph3=='rest'; rows.append(dict(subject=subj,what='floor_rest_posture_spread',mae=np.abs(Y3[restm]-np.median(Y3[restm],0)).mean()))
    # --- forecasting at 100 ms ---
    h=10
    parts={k:build(S[k],100,HIST[1500],h,valid,True) for k in (1,2,3)}
    m,_=fit_tuned(parts)
    X,Yf,Yn,_,ph=parts[3]
    corr=pred(m,X)-Yn
    # velocity from glove (updates every 40 ms) -> use 40 ms difference, causal
    full=build(S[3],100,HIST[1500],h,valid,False)  # same frames
    n=len(Y3)-h; keep=np.arange(n)>=150
    Yall=Y3[:n]; prev=np.roll(Y3,4,0)[:n]
    vel=(Yall-prev)[keep]/4.0  # deg per frame
    cv=Yn+vel*h
    for nm,P,mask in [('persistence',Yn,None),('const_velocity',cv,None),('const_velocity_half',Yn+0.5*vel*h,None),
                      ('ridge_state',Yn+corr,None),('oracle_gate',Yn+corr*(ph=='moving')[:,None],None)]:
        e=np.abs(P-Yf)
        rows.append(dict(subject=subj,what=nm,mae=e.mean(),mae_moving=e[ph=='moving'].mean(),mae_hold=e[ph=='hold'].mean(),mae_rest=e[ph=='rest'].mean()))
    # DoA ranges for physical meaning
    rows.append(dict(subject=subj,what='range_5_95', **{d:np.ptp(np.percentile(Y3[:,j],[5,95])) for j,d in enumerate(DOA)}))
    print(subj,flush=True)
pd.DataFrame(rows).to_csv(os.path.join(ROOT,'results','velocity_baselines.csv'),index=False)
