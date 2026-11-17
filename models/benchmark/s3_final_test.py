"""Final one-time test on session 3. Chosen model (cross-session validation): MLP + GBM averaged, causal calibration.
Ablations reported (not used for selection): no calibration; ridge on integrator features."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')

sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,'s2b_cross_session_selection.py')).read().split('rows=[];t0=time.time()')[0].replace("SUBJ=[int(x) for x in sys.argv[1].split(',')]; tag=sys.argv[2]",""))
SUBJ=[int(x) for x in sys.argv[1].split(',')]; tag=sys.argv[2]
rows=[]; preds_out={}; t0=time.time()
for subj in SUBJ:
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    for cal in (True,False):
        F={k:feat(calibrate(S[k],valid,cal),valid)[WARM:] for k in (1,2,3)}
        X12=np.concatenate([F[1],F[2]]); Y12=np.concatenate([S[1]['Y'][WARM:],S[2]['Y'][WARM:]])
        pred=fit_models(X12,Y12); Y3=S[3]['Y'][WARM:]; ph=S[3]['ph'][WARM:]
        for name,P in pred(F[3]).items():
            mae,r2=metrics(Y3,P); err=np.abs(P-Y3)
            row=dict(subject=subj,calib=cal,model=name,mae=mae.mean(),r2=r2.mean(),
                     **{f'mae_{d}':mae[j] for j,d in enumerate(DOA)},**{f'r2_{d}':r2[j] for j,d in enumerate(DOA)},
                     **{f'mae_{p}':err[ph==c].mean() for p,c in (('rest',0),('hold',1),('moving',2))})
            rows.append(row)
            if cal and name=='mlp+gbm': preds_out[subj]=(P,Y3,ph)
    print(subj,round(time.time()-t0),flush=True)
pd.DataFrame(rows).to_csv(os.path.join(ROOT,'results','benchmark',f's3_test_{tag}.csv'),index=False)
np.savez(os.path.join(ROOT,'results','benchmark',f's3_preds_{tag}.npz'),**{f'P{k}':v[0] for k,v in preds_out.items()},**{f'Y{k}':v[1] for k,v in preds_out.items()},**{f'ph{k}':v[2] for k,v in preds_out.items()})
