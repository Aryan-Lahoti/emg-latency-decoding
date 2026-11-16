"""Post-selection analysis on session 3 (chosen model: MLP+GBM, causal calibration).
 - context ablation: integrator timescales capped at 1.5 s (horizon 0)
 - horizon sweep: full timescales, horizons 50/100/150 ms"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')

sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,'s2b_cross_session_selection.py')).read().split('rows=[];t0=time.time()')[0].replace("SUBJ=[int(x) for x in sys.argv[1].split(',')]; tag=sys.argv[2]",""))
SUBJ=[int(x) for x in sys.argv[1].split(',')]; tag=sys.argv[2]
CFG=[('cap1.5s',(0.05,0.15,0.5,1.5),0),('full',TAUS,5),('full',TAUS,10),('full',TAUS,15)]
rows=[]; t0=time.time()
for subj in SUBJ:
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    C={k:calibrate(S[k],valid,True) for k in (1,2,3)}
    for name,taus,h in CFG:
        fe=lambda s: np.concatenate([integrator_features(s,valid,taus=taus),integrator_features(s,valid,taus=taus,log=True)],1)
        def pair(k):
            X=fe(C[k]); Y=S[k]['Y']; n=len(Y)-h
            return X[WARM:n], Y[WARM+h:n+h], S[k]['ph'][WARM+h:n+h]
        a,b,c=pair(1),pair(2),pair(3)
        pred=fit_models(np.concatenate([a[0],b[0]]),np.concatenate([a[1],b[1]]))
        for m,P in pred(c[0]).items():
            mae,r2=metrics(c[1],P); err=np.abs(P-c[1])
            rows.append(dict(subject=subj,cfg=name,horizon_ms=h*10,model=m,mae=mae.mean(),r2=r2.mean(),
                **{f'mae_{p}':err[c[2]==q].mean() for p,q in (('rest',0),('hold',1),('moving',2))}))
        print(subj,name,h,round(time.time()-t0),flush=True)
pd.DataFrame(rows).to_csv(os.path.join(ROOT,'results','benchmark',f's4_{tag}.csv'),index=False)
