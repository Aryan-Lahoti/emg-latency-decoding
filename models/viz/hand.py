import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
import mujoco, numpy as np
MEN=os.path.join(os.environ.get('MENAGERIE', os.path.join(ROOT,'mujoco_menagerie')),'shadow_hand','')
def build():
    spec=mujoco.MjSpec.from_file(MEN+'scene_right.xml')
    ghost=mujoco.MjSpec.from_file(MEN+'right_hand.xml')
    fr=spec.worldbody.add_frame()
    spec.attach(ghost,prefix='g_',frame=fr)
    spec.visual.global_.offwidth=1280; spec.visual.global_.offheight=720
    m=spec.compile()
    for g in range(m.ngeom):
        b=m.body(m.geom_bodyid[g]).name
        m.geom_contype[g]=0; m.geom_conaffinity[g]=0
        finger=any(t in b for t in ('ff','mf','rf','lf','th')) and 'forearm' not in b
        if b.startswith('g_'):
            m.geom_matid[g]=-1; m.geom_rgba[g]=[0.1,0.5,1.0,0.3] if finger else [0,0,0,0]
        elif b.startswith('rh_'):
            m.geom_matid[g]=-1; m.geom_rgba[g]=[0.93,0.52,0.2,1] if finger else [0.33,0.33,0.36,1]
        elif b!='world':
            m.geom_rgba[g]=[0,0,0,0]
    return m
FING={'index':'FF','middle':'MF'}
def qpos_from_u(m,u,prefix):
    """u: dict of 5 normalised DoAs (0 = rest, 1 = full). Illustrative mapping to Shadow Hand joints."""
    q={}
    for doa,f in (('index','FF'),('middle','MF'),('ring_little','RF'),('ring_little','LF')):
        v=np.clip(u[doa],-0.1,1.15)
        q[f'{f}J3']=0.12+1.25*v; q[f'{f}J2']=0.12+1.25*v; q[f'{f}J1']=0.08+0.8*v
    t=np.clip(u['thumb_rot'],-0.1,1.15); q['THJ4']=0.15+1.0*t; q['THJ5']=0.5*t
    t=np.clip(u['thumb_flex'],-0.1,1.15); q['THJ2']=0.55*t; q['THJ1']=0.1+1.1*t
    out={}
    for k,v in q.items():
        j=m.joint(f'{prefix}rh_{k}'); lo,hi=j.range; out[j.qposadr[0]]=float(np.clip(v,lo,hi))
    return out
