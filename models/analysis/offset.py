import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.path.insert(0, os.path.join(MODELS,'benchmark'))
from bench_lib import *
TAUS=(0.05,0.15,0.5,1.5,4.0)
feat=lambda s,v: np.concatenate([integrator_features(s,v,taus=TAUS),integrator_features(s,v,taus=TAUS,log=True)],1)
for subj in [1,3,5,8,11]:
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    # train on session 1 only, look at session 2 (cross-session, no test data used)
    X1=feat(S[1],valid)[WARM:]; Y1=S[1]['Y'][WARM:]; X2=feat(S[2],valid)[WARM:]; Y2=S[2]['Y'][WARM:]
    m=ridge_path(X1,Y1,[1e-3])[0]; P=ridge_pred(m,X2); e=P-Y2
    rest2=S[2]['ph'][WARM:]==0
    print(subj,'s1->s2 MAE',np.abs(e).mean().round(2),'| mean offset per DoA',e.mean(0).round(1),
          '| MAE after removing offset',np.abs(e-e.mean(0)).mean().round(2),
          '| rest posture s1 vs s2',(S[1]['Y'][S[1]['ph']==0].mean(0)-S[2]['Y'][S[2]['ph']==0].mean(0)).round(1))
