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
def calibrate(s,valid,on):
    if not on: return s
    e=s['rms_50'][:,valid]; le=np.log(e+1e-7)
    c=np.cumsum(le,0)/np.arange(1,len(le)+1)[:,None]; c[:3000]=c[3000]
    s2=dict(s); s2['rms_50']=s['rms_50'].copy(); s2['rms_50'][:,valid]=e/np.exp(c); return s2
def feat(s,valid): return np.concatenate([integrator_features(s,valid,taus=TAUS),integrator_features(s,valid,taus=TAUS,log=True)],1)
def fit_models(X,Y):
    mu,sd=X.mean(0),X.std(0)+1e-12; Z=(X[::4]-mu)/sd; Yz=Y[::4]; ym,ys=Yz.mean(0),Yz.std(0)
    rid=ridge_path(X,Y,[1e-3])[0]
    gbm=[HistGradientBoostingRegressor(max_iter=400,learning_rate=0.05,max_leaf_nodes=63,l2_regularization=1.0,
         early_stopping=True,validation_fraction=0.1,random_state=0).fit(Z,Yz[:,j]) for j in range(5)]
    mlp=MLPRegressor(hidden_layer_sizes=(256,128),alpha=1e-3,batch_size=256,max_iter=60,early_stopping=True,
         validation_fraction=0.1,n_iter_no_change=6,random_state=0).fit(Z,(Yz-ym)/ys)
    def predict(Xn):
        Zn=(Xn-mu)/sd
        pg=np.column_stack([g.predict(Zn) for g in gbm]); pm=mlp.predict(Zn)*ys+ym
        return {'ridge':ridge_pred(rid,Xn),'gbm':pg,'mlp':pm,'mlp+gbm':(pg+pm)/2}
    return predict
rows=[];t0=time.time()
for subj in SUBJ:
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    for cal in (False,True):
        for a,b in ((1,2),(2,1)):
            A=calibrate(S[a],valid,cal); B=calibrate(S[b],valid,cal)
            pred=fit_models(feat(A,valid)[WARM:],S[a]['Y'][WARM:])
            Yb=S[b]['Y'][WARM:]
            for name,P in pred(feat(B,valid)[WARM:]).items():
                mae,r2=metrics(Yb,P); rows.append(dict(subject=subj,calib=cal,train=a,test=b,model=name,mae=mae.mean(),r2=r2.mean()))
    print(subj,round(time.time()-t0),flush=True)
pd.DataFrame(rows).to_csv(os.path.join(ROOT,'results','benchmark',f's2b_xsess_{tag}.csv'),index=False)
