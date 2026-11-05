import numpy as np, scipy.io as sio
from scipy.signal import butter, sosfilt

AA = butter(4, 450, btype="lowpass",  fs=2000, output="sos")   # anti-aliasing, before 2000 -> 1000 Hz
HP = butter(2, 20,  btype="highpass", fs=1000, output="sos")   # gentle drift removal

def load(path):
    """Load only what we need (the full file is ~1.6 GB in memory with the IMU)."""
    d = sio.loadmat(path, variable_names=["emg", "glove", "restimulus", "rerepetition"])
    return (d["emg"].astype(np.float64), d["glove"].astype(np.float64),
            d["restimulus"].ravel(), d["rerepetition"].ravel())

def clean(emg):
    """Causal anti-aliasing + downsample to 1000 Hz + causal high-pass."""
    return sosfilt(HP, sosfilt(AA, emg, axis=0)[::2], axis=0)

def moving_rms(x, win_ms, fs=1000, step_ms=10):
    """Causal moving RMS over the last win_ms, one value every step_ms."""
    N, step = int(win_ms * fs / 1000), int(step_ms * fs / 1000)
    cs = np.concatenate([np.zeros((1, x.shape[1])), np.cumsum(x**2, axis=0)])
    ends = np.arange(N, len(x) + 1, step)
    return np.sqrt((cs[ends] - cs[ends - N]) / N), ends

def onset_leads(x, glove, restim, rerep, win_ms=50):
    """Per repetition: glove onset minus EMG onset in ms (positive = EMG first)."""
    env, ends = moving_rms(x, win_ms)
    k = 2 * (ends - 1)
    g, rs, rr = glove[k], restim[k], rerep[k]
    act = env.sum(axis=1)
    out = []
    for mov in range(1, 10):
        for rep in np.unique(rr[rs == mov]):
            start = np.where((rs == mov) & (rr == rep))[0][0]
            if start < 120: continue
            pre, win = slice(start - 120, start - 60), slice(start - 60, start + 150)
            mu, sd = act[pre].mean(), act[pre].std()
            e_on = np.argmax(act[win] > mu + 5 * sd)
            dist = np.linalg.norm(g[win] - g[pre].mean(axis=0), axis=1)
            g_on = np.argmax(dist > 5)
            if act[win][e_on] <= mu + 5 * sd or dist[g_on] <= 5: continue
            out.append((mov, int(rep), (g_on - e_on) * 10 + win_ms / 2))
    return out

def window_feats(x, win_ms, ends, fs=1000):
    """Causal RMS and MAV over the last win_ms, at the given frame ends."""
    N = int(win_ms * fs / 1000)
    z = np.zeros((1, x.shape[1]))
    c2 = np.concatenate([z, np.cumsum(x**2, axis=0)])
    c1 = np.concatenate([z, np.cumsum(np.abs(x), axis=0)])
    rms = np.sqrt((c2[ends] - c2[ends - N]) / N)
    mav = (c1[ends] - c1[ends - N]) / N
    return rms.astype(np.float32), mav.astype(np.float32)

def build_file(path, out_path, windows=(50, 100, 200)):
    """One raw .mat file -> one model-ready .npz file at 100 Hz."""
    emg, glove, rs, rr = load(path)
    valid = ~np.all(emg == 0, axis=0)                 # False = electrode not recorded
    x = clean(emg)
    ends = np.arange(max(windows), len(x) + 1, 10)    # one frame every 10 ms, same for every window
    k = 2 * (ends - 1)                                # matching index in the raw 2 kHz data
    out = dict(t=(ends / 1000).astype(np.float32),
               glove=glove[k].astype(np.float32),     # all 18 sensors; the 5-DoA matrix is applied later
               restim=rs[k], rerep=rr[k], valid=valid)
    for W in windows:
        out[f"rms_{W}"], out[f"mav_{W}"] = window_feats(x, W, ends)
    np.savez_compressed(out_path, **out)
    return int(valid.sum()), len(ends)



# 18 glove sensors -> 5 DoA (Krasoulis et al. 2019; as printed in KinEMbed, Eq. 6)
DOA_NAMES = ["thumb rotation", "thumb flexion", "index flexion", "middle flexion", "ring/little flexion"]
A_T = np.zeros((18, 5))
A_T[[0, 1, 3, 16], 0] = [0.639, 0.383, -0.639, -0.19]       # thumb rotation: sensors 1, 2, 4, 17
A_T[2, 1] = 1.0                                              # thumb flexion: sensor 3
A_T[[4, 5], 2] = [0.4, 0.6]                                  # index: sensors 5, 6
A_T[[6, 7], 3] = [0.4, 0.6]                                  # middle: sensors 7, 8
A_T[[9, 10, 12, 13], 4] = [0.1667, 0.3333, 0.1667, 0.3333]   # ring/little: sensors 10, 11, 13, 14

def to_doa(glove):
    """(T, 18) glove angles -> (T, 5) finger DoAs."""
    return glove @ A_T