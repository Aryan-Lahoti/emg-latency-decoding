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
print("subj | rest-vs-hold (level) | still-vs-moving (level) | still-vs-moving (change)")
for subj in range(1,13):
    s=load(subj,3); v=s['valid']
    e=s['rms_100'][:,v].mean(1)
    ch=np.zeros_like(e); ch[10:]=np.abs(s['rms_100'][10:,v]-s['rms_100'][:-10,v]).mean(1)
    ph=s['phase']; still=ph!='moving'; mov=ph=='moving'
    print(f"{subj:4d} | {auc(e[ph=='rest'],e[ph=='hold']):.2f} | {auc(e[still],e[mov]):.2f} | {auc(ch[still],ch[mov]):.2f}")
