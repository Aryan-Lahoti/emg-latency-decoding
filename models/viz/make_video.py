import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')
sys.path.insert(0, HERE)
from hand import *
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, imageio.v2 as iio, glob
SUBJ=int(sys.argv[1]); T0=float(sys.argv[2]); DUR=float(sys.argv[3]); OUT=sys.argv[4]; STILL=len(sys.argv)>5
DOA=["thumb_rot","thumb_flex","index","middle","ring_little"]; NICE=["Thumb rotation","Thumb flexion","Index","Middle","Ring + little"]
MOVE={0:"Rest",1:"Thumb flexion/extension",2:"Thumb abduction/adduction",3:"Index flexion",4:"Middle flexion",5:"Ring + little flexion",6:"Index pointer",7:"Cylindrical grip",8:"Lateral grip",9:"Tripod grip"}
WARM=300
for f in glob.glob(os.path.join(ROOT,'results','benchmark','s3_preds_*.npz')):
    z=np.load(f)
    if f'P{SUBJ}' in z.files: P,Y=z[f'P{SUBJ}'],z[f'Y{SUBJ}']
d0=np.load(os.path.join(DATA_DIR,f'S{SUBJ}_E1_A3.npz'))
env=d0['rms_50'][WARM:][:, d0['valid']]*1e6; restim=d0['restim'][WARM:]; assert len(env)==len(P)
# normalise each DoA: 0 = resting posture, 1 = far end of its travel (same scaling for truth and model)
rest=np.median(Y[restim==0],0); lo,hi=np.percentile(Y,[1,99],axis=0)
ext=np.where(hi-rest>rest-lo,hi,lo); U=lambda A:(A-rest)/(ext-rest)
Ut,Up=U(Y),U(P)
i0=int(T0*100); idx=np.arange(i0,i0+int(DUR*100),4)          # 25 fps, real time
m=build(); d=mujoco.MjData(m); r=mujoco.Renderer(m,720,640)
cam=mujoco.MjvCamera(); cam.lookat[:]=[0.325,0.0,0.03]; cam.distance=0.47; cam.azimuth=200; cam.elevation=-52
# right-hand panel
fig=plt.figure(figsize=(6.4,7.2),dpi=100); gs=fig.add_gridspec(7,1,height_ratios=[0.75,2.8,1,1,1,1,1],hspace=0.5,left=0.09,right=0.97,top=0.97,bottom=0.06)
axt=fig.add_subplot(gs[0]); axt.axis('off'); title=axt.text(0,0.75,'',fontsize=13,weight='bold',va='center'); info=axt.text(1,0.75,'',fontsize=9,ha='right',va='center')
axe=fig.add_subplot(gs[1]); HW=4.0; n_e=env.shape[1]; sc=np.percentile(env,99.5,axis=0); tt=np.arange(-int(HW*100),1)/100
el=[axe.plot(tt,tt*0,lw=0.8,color=plt.cm.viridis(k/n_e))[0] for k in range(n_e)]
axe.set_xlim(-HW,0); axe.set_ylim(-0.6,n_e-0.2); axe.set_yticks([0,n_e-1]); axe.set_yticklabels(['1',str(n_e)]); axe.set_ylabel('electrode'); axe.set_xticks([])
axe.set_title(f'Forearm EMG envelope (50 ms RMS), one row per electrode\neach row scaled to its own peak ({sc.min():.0f}–{sc.max():.0f} µV)',fontsize=9)
ad=[];tl=[];pl=[]
for j in range(5):
    a=fig.add_subplot(gs[2+j]); a.set_xlim(-HW,0); a.set_ylim(min(lo[j],P[:,j].min())-3,max(hi[j],P[:,j].max())+3)
    tl.append(a.plot(tt,tt*0,color='#1a8cff',lw=2.2,alpha=0.75)[0]); pl.append(a.plot(tt,tt*0,color='#e8742a',lw=1.6)[0])
    a.text(0.01,0.86,NICE[j]+' (°)',transform=a.transAxes,fontsize=8,weight='bold',va='top'); a.tick_params(labelsize=7)
    if j<4: a.set_xticks([])
    else: a.set_xlabel('seconds before now')
    ad.append(a)
ad[0].legend([tl[0],pl[0]],['glove (measured)','model (from EMG)'],fontsize=8,ncol=2,loc='lower right',bbox_to_anchor=(1,0.98),frameon=False)
def panel(i):
    w=np.arange(i-int(HW*100),i+1); ok=w>=0; wv=np.clip(w,0,None)
    for k in range(n_e): el[k].set_ydata(np.where(ok,k+np.clip(env[wv,k]/sc[k],0,1.3)*0.9,np.nan))
    for j in range(5):
        tl[j].set_ydata(np.where(ok,Y[wv,j],np.nan)); pl[j].set_ydata(np.where(ok,P[wv,j],np.nan))
    title.set_text(f'Cue: {MOVE[int(restim[i])]}'); info.set_text(f'Subject {SUBJ}, test session   t = {i/100:6.1f} s\nerror now: {np.abs(P[i]-Y[i]).mean():4.1f}°')
    fig.canvas.draw(); return np.asarray(fig.canvas.buffer_rgba())[...,:3]
def hand(i):
    for a,v in {**qpos_from_u(m,dict(zip(DOA,Up[i])),''),**qpos_from_u(m,dict(zip(DOA,Ut[i])),'g_')}.items(): d.qpos[a]=v
    mujoco.mj_forward(m,d); r.update_scene(d,cam); return r.render()
from PIL import Image, ImageDraw, ImageFont
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
def frame(i):
    h=Image.fromarray(hand(i)); dr=ImageDraw.Draw(h)
    dr.rectangle([12,12,30,30],fill=(237,133,51)); dr.text((38,11),'model output (decoded from EMG)',fill='white',font=font)
    dr.rectangle([12,40,30,58],fill=(60,150,255)); dr.text((38,39),'measured glove (ghost)',fill='white',font=font)
    dr.text((12,690),'Finger pose is an illustrative mapping of the 5 decoded angles',fill=(200,200,200),font=font)
    return np.concatenate([np.asarray(h),panel(i)],1)
if STILL:
    iio.imwrite(OUT,frame(idx[len(idx)//2])); sys.exit()
w=iio.get_writer(OUT,fps=25,codec='libx264',quality=7,macro_block_size=None)
for n,i in enumerate(idx):
    w.append_data(frame(i))
    if n%250==0: print(n,len(idx),flush=True)
w.close()
