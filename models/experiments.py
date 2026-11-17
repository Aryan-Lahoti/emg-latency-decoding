"""Follow-up experiments on raw labels (train sessions 1-2, test session 3 once).

A  window_only : windows 50/100/200 ms, current snapshot only (no history)
B  history     : 100 ms window, history 0 / 300 / 750 / 1500 ms
C  stateful    : 100 ms window, 1500 ms history, EMG-only ridge vs ridge + current angle vs persistence

Every run also reports MAE split by phase of the target frame:
  moving = finger speed > 20 deg/s (any DoA); rest = still and restim==0; hold = still and restim>0.
Usage: python experiments.py DATA_DIR OUT_DIR EXPERIMENT SUBJECTS(comma-separated)
"""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

DATA, OUT, EXP = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
SUBJECTS = [int(s) for s in sys.argv[4].split(",")]
OUT.mkdir(parents=True, exist_ok=True)

A_T = np.zeros((18, 5))
A_T[[0, 1, 3, 16], 0] = [0.639, 0.383, -0.639, -0.19]
A_T[2, 1] = 1.0
A_T[[4, 5], 2] = [0.4, 0.6]
A_T[[6, 7], 3] = [0.4, 0.6]
A_T[[9, 10, 12, 13], 4] = [0.1667, 0.3333, 0.1667, 0.3333]
DOA = ["thumb_rot", "thumb_flex", "index", "middle", "ring_little"]
HORIZONS = [0, 50, 100, 150]
LAMBDAS = np.logspace(-3, 3, 13)
VAL_REPS = [9, 10]
HIST = {0: [0], 300: [0, 5, 10, 20, 30], 750: [0, 5, 10, 20, 30, 50, 75],
        1500: [0, 5, 10, 20, 30, 50, 75, 100, 150]}
SPEED_THR = 20.0  # deg/s


def load(subj, sess):
    d = np.load(DATA / f"S{subj}_E1_A{sess}.npz")
    rep = d["rerep"].astype(int).copy(); last = 1
    for i in range(len(rep)):
        if rep[i] > 0: last = rep[i]
        else: rep[i] = last
    Y = d["glove"].astype(np.float64) @ A_T
    v = np.zeros(len(Y)); v[4:-4] = np.abs(Y[8:] - Y[:-8]).max(1) / 0.08
    phase = np.where(v > SPEED_THR, "moving", np.where(d["restim"] == 0, "rest", "hold"))
    s = dict(Y=Y, rep=rep, phase=phase, valid=d["valid"])
    for k in d.files:
        if k[:3] in ("rms", "mav"): s[k] = d[k].astype(np.float64)
    return s


def build(s, w, lags, h, valid, with_angle):
    base = np.concatenate([s[f"rms_{w}"][:, valid], s[f"mav_{w}"][:, valid]], 1)
    X = np.concatenate([np.roll(base, l, 0) for l in lags], 1)
    if with_angle: X = np.concatenate([X, s["Y"]], 1)        # current angle at frame i
    n = len(X) - h; keep = np.arange(n) >= max(lags)
    return X[:n][keep], s["Y"][h:h + n][keep], s["Y"][:n][keep], s["rep"][:n][keep], s["phase"][h:h + n][keep]


def ridge_path(X, Y, lams):
    mu, sd = X.mean(0), X.std(0) + 1e-12
    Z = (X - mu) / sd; ym = Y.mean(0)
    ev, V = np.linalg.eigh(Z.T @ Z); B = V.T @ (Z.T @ (Y - ym)); n = len(Z)
    return [(mu, sd, ym, V @ (B / (ev + lam * n)[:, None])) for lam in lams]


def pred(m, X):
    mu, sd, ym, W = m
    return ((X - mu) / sd) @ W + ym


def fit_tuned(parts):
    X = np.concatenate([parts[1][0], parts[2][0]]); Y = np.concatenate([parts[1][1], parts[2][1]])
    v = np.isin(np.concatenate([parts[1][3], parts[2][3]]), VAL_REPS)
    errs = [np.abs(pred(m, X[v]) - Y[v]).mean() for m in ridge_path(X[~v], Y[~v], LAMBDAS)]
    lam = LAMBDAS[int(np.argmin(errs))]
    return ridge_path(X, Y, [lam])[0], lam


def score(rows, P, Y, phase, **meta):
    err = P - Y
    r2 = 1 - (err ** 2).sum(0) / ((Y - Y.mean(0)) ** 2).sum(0)
    for j, name in enumerate(DOA):
        row = dict(meta, doa=name, mae=np.abs(err[:, j]).mean(), rmse=np.sqrt((err[:, j] ** 2).mean()), r2=r2[j])
        for ph in ("rest", "hold", "moving"):
            m = phase == ph
            row[f"mae_{ph}"] = np.abs(err[m, j]).mean() if m.any() else np.nan
            row[f"frac_{ph}"] = m.mean()
        rows.append(row)


if EXP == "window_only":
    configs = [(w, 0, False) for w in (50, 100, 200)]
elif EXP == "history":
    configs = [(100, hm, False) for hm in (0, 300, 750, 1500)]
elif EXP == "stateful":
    configs = [(100, 1500, False), (100, 1500, True)]
else:
    raise SystemExit("unknown experiment")

rows = []; t0 = time.time()
for subj in SUBJECTS:
    S = {k: load(subj, k) for k in (1, 2, 3)}
    valid = S[1]["valid"] & S[2]["valid"] & S[3]["valid"]
    for h_ms in HORIZONS:
        h = h_ms // 10
        meta0 = dict(experiment=EXP, subject=subj, amputee=subj in (11, 12), horizon_ms=h_ms)
        for w, hm, ang in configs:
            parts = {k: build(S[k], w, HIST[hm], h, valid, ang) for k in (1, 2, 3)}
            m, lam = fit_tuned(parts)
            Xte, Yte, Ynow, _, ph = parts[3]
            score(rows, pred(m, Xte), Yte, ph, **meta0, model="ridge+angle" if ang else "ridge",
                  window_ms=w, history_ms=hm, lam=lam)
        if EXP == "stateful":   # persistence on the same test frames as the 1500 ms-history models
            _, Yte, Ynow, _, ph = build(S[3], 100, HIST[1500], h, valid, False)
            score(rows, Ynow, Yte, ph, **meta0, model="persistence", window_ms=np.nan, history_ms=np.nan, lam=np.nan)
    print(f"{EXP} subject {subj} done {time.time() - t0:.0f}s", flush=True)

pd.DataFrame(rows).to_csv(OUT / f"{EXP}_S{'-'.join(map(str, SUBJECTS))}.csv", index=False)
