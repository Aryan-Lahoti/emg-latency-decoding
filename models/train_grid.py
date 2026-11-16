"""Step 1: raw-label grid. Persistence + ridge on EMG envelope features.

Train: sessions 1-2 (A1, A2). Test: session 3 (A3), used once.
Ridge penalty tuned on held-out repetitions 9-10 of sessions 1-2.
Everything causal; no frame-level random splits; train-only normalisation.
"""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(sys.argv[1])
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

# 18 glove sensors -> 5 DoAs (copied from src/emgproc.py, Krasoulis et al. 2019)
A_T = np.zeros((18, 5))
A_T[[0, 1, 3, 16], 0] = [0.639, 0.383, -0.639, -0.19]
A_T[2, 1] = 1.0
A_T[[4, 5], 2] = [0.4, 0.6]
A_T[[6, 7], 3] = [0.4, 0.6]
A_T[[9, 10, 12, 13], 4] = [0.1667, 0.3333, 0.1667, 0.3333]
DOA = ["thumb_rot", "thumb_flex", "index", "middle", "ring_little"]

WINDOWS = [50, 100, 200]          # ms
HORIZONS = [0, 50, 100, 150]      # ms
LAGS = [0, 5, 10, 20, 30, 50, 75, 100, 150]  # frames: up to 1.5 s of past envelope (chosen on validation)
VAL_REPS = {9, 10}
LAMBDAS = np.logspace(-3, 3, 13)  # relative to n (penalty = lam * n)


def load(subj, sess):
    d = np.load(DATA / f"S{subj}_E1_A{sess}.npz")
    rep = d["rerep"].astype(int).copy()
    # rest frames (rep 0) inherit the repetition of the preceding movement
    last = 1
    for i in range(len(rep)):
        if rep[i] > 0: last = rep[i]
        else: rep[i] = last
    return dict(glove=d["glove"].astype(np.float64), restim=d["restim"], rep=rep,
                valid=d["valid"], **{k: d[k].astype(np.float64) for k in d.files if k[:3] in ("rms", "mav")})


def features(s, w, valid):
    base = np.concatenate([s[f"rms_{w}"][:, valid], s[f"mav_{w}"][:, valid]], 1)  # raw envelopes beat log on validation
    T = len(base); maxlag = max(LAGS)
    X = np.concatenate([np.roll(base, l, axis=0) for l in LAGS], 1)
    ok = np.zeros(T, bool); ok[maxlag:] = True        # drop frames without full history
    return X, ok


def build(s, w, h, valid):
    """Pair features at frame i with DoA at frame i+h (within one session)."""
    X, ok = features(s, w, valid)
    Y = s["glove"] @ A_T
    n = len(Y) - h
    Xi, Yf, Yn = X[:n], Y[h:h + n], Y[:n]             # future target, current (for persistence)
    keep = ok[:n]
    return Xi[keep], Yf[keep], Yn[keep], s["rep"][:n][keep], s["restim"][:n][keep]


def ridge_path(X, Y, lams):
    """Fit ridge for every penalty at once: one Gram matrix + one eigendecomposition."""
    mu, sd = X.mean(0), X.std(0) + 1e-12
    Z = (X - mu) / sd
    ym = Y.mean(0)
    G = Z.T @ Z
    ev, V = np.linalg.eigh(G)
    B = V.T @ (Z.T @ (Y - ym))
    n = len(Z)
    return [(mu, sd, ym, V @ (B / (ev + lam * n)[:, None])) for lam in lams]


def ridge_fit(X, Y, lam):
    return ridge_path(X, Y, [lam])[0]


def ridge_pred(m, X):
    mu, sd, ym, W = m
    return ((X - mu) / sd) @ W + ym


def metrics(Y, P):
    err = P - Y
    mae = np.abs(err).mean(0)
    rmse = np.sqrt((err ** 2).mean(0))
    r2 = 1 - (err ** 2).sum(0) / ((Y - Y.mean(0)) ** 2).sum(0)
    return mae, rmse, r2


rows, lam_rows = [], []
t0 = time.time()
for subj in range(1, 13):
    S = {k: load(subj, k) for k in (1, 2, 3)}
    valid = S[1]["valid"] & S[2]["valid"] & S[3]["valid"]
    for w in WINDOWS:
        for h_ms in HORIZONS:
            h = h_ms // 10
            parts = {k: build(S[k], w, h, valid) for k in (1, 2, 3)}
            Xtr = np.concatenate([parts[1][0], parts[2][0]]); Ytr = np.concatenate([parts[1][1], parts[2][1]])
            reps = np.concatenate([parts[1][3], parts[2][3]])
            vmask = np.isin(reps, list(VAL_REPS))
            # tune penalty on held-out reps of sessions 1-2
            best = None
            for lam, m in zip(LAMBDAS, ridge_path(Xtr[~vmask], Ytr[~vmask], LAMBDAS)):
                mae = np.abs(ridge_pred(m, Xtr[vmask]) - Ytr[vmask]).mean()
                if best is None or mae < best[1]: best = (lam, mae)
            lam = best[0]
            lam_rows.append(dict(subject=subj, window_ms=w, horizon_ms=h_ms, lam=lam, val_mae=best[1]))
            m = ridge_fit(Xtr, Ytr, lam)                       # refit on all of sessions 1-2
            Xte, Yte, Ynow, _, _ = parts[3]
            preds = {"ridge": ridge_pred(m, Xte), "persistence": Ynow}
            for model, P in preds.items():
                if model == "persistence" and w != WINDOWS[0]:
                    continue                                   # persistence doesn't depend on window
                mae, rmse, r2 = metrics(Yte, P)
                for j, name in enumerate(DOA):
                    rows.append(dict(subject=subj, amputee=subj in (11, 12), model=model,
                                     window_ms=w if model == "ridge" else np.nan, horizon_ms=h_ms,
                                     doa=name, mae=mae[j], rmse=rmse[j], r2=r2[j]))
    print(f"subject {subj} done, {time.time() - t0:.0f}s", flush=True)

res = pd.DataFrame(rows)
res.to_csv(OUT / "grid_raw.csv", index=False)
pd.DataFrame(lam_rows).to_csv(OUT / "grid_raw_lambdas.csv", index=False)
print("saved", len(res), "rows")
