import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.argv=['x',DATA_DIR,__import__('tempfile').gettempdir(),'stateful','1']
src=open(os.path.join(MODELS,'experiments.py')).read().split('if EXP == "window_only"')[0]
exec(compile(src,'e','exec'))
import numpy as np
def auc(a,b):
    x=np.concatenate([a,b]); r=x.argsort().argsort()+1
    return (r[len(a):].sum()-len(b)*(len(b)+1)/2)/(len(a)*len(b))
out=[]
for subj in [1,3,5,8]:
    S={k:load(subj,k) for k in (1,2,3)}; valid=S[1]['valid']&S[2]['valid']&S[3]['valid']
    rest_post=np.concatenate([S[k]['Y'][S[k]['phase']=='rest'] for k in (1,2)]).mean(0)
    # EMG-only, h=0
    P={k:build(S[k],100,HIST[1500],0,valid,False) for k in (1,2,3)}; m,_=fit_tuned(P)
    X,Y,_,_,ph=P[3]; pr=pred(m,X); hold=ph=='hold'
    dev_t=Y[hold]-rest_post; dev_p=pr[hold]-rest_post; big=np.abs(dev_t)>10
    frac=np.median((dev_p/dev_t)[big])
    # stateful, h=10
    Q={k:build(S[k],100,HIST[1500],10,valid,True) for k in (1,2,3)}; m2,_=fit_tuned(Q)
    X2,Y2,Yn,_,ph2=Q[3]; c=pred(m2,X2)-Yn; h2=ph2=='hold'
    toward=(np.sign(c[h2])==np.sign(rest_post-Yn[h2])); sel=np.abs(Yn[h2]-rest_post)>10
    # separability of rest vs hold by total EMG level (current snapshot)
    s=S[3]; e=s['rms_100'][:,valid].mean(1); a=auc(e[s['phase']=='rest'],e[s['phase']=='hold'])
    out.append((subj,frac,toward[sel].mean(),a))
    print(f"S{subj}: EMG-only hold keeps {frac*100:.0f}% of the held deviation | stateful corrections during hold point back toward rest {toward[sel].mean()*100:.0f}% of the time | rest-vs-hold separability from EMG level (AUC) {a:.2f}")
