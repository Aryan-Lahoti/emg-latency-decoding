import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.path.insert(0, HERE)
from bench_lib import *
import pandas as pd, time
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
SUBJ=[int(x) for x in sys.argv[1].split(',')]; tag=sys.argv[2]
TAUS=(0.05,0.15,0.5,1.5,4.0)
feat=lambda s,v: np.concatenate([integrator_features(s,v,taus=TAUS),integrator_features(s,v,taus=TAUS,log=True)],1)
rows=[];t0=time.time()
for subj in SUBJ:
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    d=splits(S,lambda s: feat(s,valid))
    mu,sd=d['Xtr'].mean(0),d['Xtr'].std(0)+1e-12
    Xtr=(d['Xtr'][::4]-mu)/sd; Ytr=d['Ytr'][::4]; Xva=(d['Xva']-mu)/sd
    # ridge reference
    best=min((np.abs(ridge_pred(m,d['Xva'])-d['Yva']).mean(),i) for i,m in enumerate(ridge_path(d['Xtr'],d['Ytr'],np.logspace(-5,1,13))))
    rows.append(dict(subject=subj,model='ridge',val_mae=best[0]))
    for lr,leaves in [(0.05,31),(0.05,63)]:
        P=np.column_stack([HistGradientBoostingRegressor(max_iter=400,learning_rate=lr,max_leaf_nodes=leaves,l2_regularization=1.0,
             early_stopping=True,validation_fraction=0.1,random_state=0).fit(Xtr,Ytr[:,j]).predict(Xva) for j in range(5)])
        mae,r2=metrics(d['Yva'],P); rows.append(dict(subject=subj,model=f'gbm lr{lr} leaves{leaves}',val_mae=mae.mean(),val_r2=r2.mean()))
    for hid,alpha in [((256,128),1e-3),((256,128),1e-2)]:
        ym,ys=Ytr.mean(0),Ytr.std(0)
        mlp=MLPRegressor(hidden_layer_sizes=hid,alpha=alpha,learning_rate_init=1e-3,batch_size=256,max_iter=60,
                         early_stopping=True,validation_fraction=0.1,n_iter_no_change=6,random_state=0).fit(Xtr,(Ytr-ym)/ys)
        P=mlp.predict(Xva)*ys+ym; mae,r2=metrics(d['Yva'],P)
        rows.append(dict(subject=subj,model=f'mlp {hid} a{alpha}',val_mae=mae.mean(),val_r2=r2.mean()))
    print(subj,round(time.time()-t0),flush=True)
pd.DataFrame(rows).to_csv(os.path.join(ROOT,'results','benchmark',f's2_val_{tag}.csv'),index=False)
