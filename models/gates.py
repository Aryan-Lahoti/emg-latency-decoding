"""Model comparison with validation-based selection.

Settings: RMS only, window W, history H, horizons 0/50/100/150 ms.
Fit protocol:
  - validation scores: fit on sessions 1-2 minus reps 9-10, score on reps 9-10
  - test scores:       refit on all of sessions 1-2, score on session 3 (used once)
Models:
  ridge_emg            EMG history -> angle at t+D
  ridge_state          EMG history + current angle -> angle at t+D
  state_deadband_rest  ridge_state with per-finger soft deadband, tau = 95th pct of |correction| on training still frames
  state_deadband_val   same, tau tuned on validation reps (validation score is optimistic: it is the tuning set)
  state_gate_tree      current + P(moving now) * correction; P from gradient-boosted trees on EMG history
  emg_holdfreeze       ridge_emg, softly frozen during detected holds: out_t = P(hold)*out_{t-1} + (1-P(hold))*ridge_t
  persistence          angle at t+D = angle at t
Usage: python models.py DATA OUT WINDOW HISTORY_MS SUBJECTS
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
W, HM = int(sys.argv[3]), int(sys.argv[4]); SUBJECTS = [int(s) for s in sys.argv[5].split(",")]

A_T = np.zeros((18, 5))
A_T[[0, 1, 3, 16], 0] = [0.639, 0.383, -0.639, -0.19]
A_T[2, 1] = 1.0
A_T[[4, 5], 2] = [0.4, 0.6]
A_T[[6, 7], 3] = [0.4, 0.6]
A_T[[9, 10, 12, 13], 4] = [0.1667, 0.3333, 0.1667, 0.3333]
DOA = ["thumb_rot", "thumb_flex", "index", "middle", "ring_little"]
HORIZONS = [0, 50, 100, 150]
LAMBDAS = np.logspace(-4, 2, 13)
VAL = [9, 10]
HIST = {0: [0], 300: [0, 5, 10, 20, 30], 750: [0, 5, 10, 20, 30, 50, 75],
        1500: [0, 5, 10, 20, 30, 50, 75, 100, 150]}
LAGS = HIST[HM]; ML = max(LAGS)
CODE = {"rest": 0, "hold": 1, "moving": 2}


def load(subj, sess):
    d = np.load(DATA / f"S{subj}_E1_A{sess}.npz")
    rep = d["rerep"].astype(int).copy(); last = 1
    for i in range(len(rep)):
        if rep[i] > 0: last = rep[i]
        else: rep[i] = last
    Y = d["glove"].astype(np.float64) @ A_T
    v = np.zeros(len(Y)); v[4:-4] = np.abs(Y[8:] - Y[:-8]).max(1) / 0.08
    ph = np.where(v > 20, 2, np.where(d["restim"] == 0, 0, 1))
    return dict(Y=Y, rep=rep, ph=ph, valid=d["valid"], env=d[f"rms_{W}"].astype(np.float64))


def frames(s, h, valid):
    E = np.concatenate([np.roll(s["env"][:, valid], l, 0) for l in LAGS], 1)
    n = len(E) - h; k = np.arange(n) >= ML
    return dict(E=E[:n][k], now=s["Y"][:n][k], fut=s["Y"][h:h + n][k], rep=s["rep"][:n][k],
                ph_now=s["ph"][:n][k], ph_fut=s["ph"][h:h + n][k])


def cat(a, b): return {k: np.concatenate([a[k], b[k]]) for k in a}
def sub(a, m): return {k: v[m] for k, v in a.items()}


def ridge_path(X, Y, lams):
    mu, sd = X.mean(0), X.std(0) + 1e-12; Z = (X - mu) / sd; ym = Y.mean(0)
    ev, V = np.linalg.eigh(Z.T @ Z); B = V.T @ (Z.T @ (Y - ym)); n = len(Z)
    return [(mu, sd, ym, V @ (B / (ev + l * n)[:, None])) for l in lams]


def pr(m, X): mu, sd, ym, Wt = m; return ((X - mu) / sd) @ Wt + ym


def tune_ridge(Xtr, Ytr, Xv, Yv):
    ms = ridge_path(Xtr, Ytr, LAMBDAS)
    i = int(np.argmin([np.abs(pr(m, Xv) - Yv).mean() for m in ms]))
    return ms[i], LAMBDAS[i]


def deadband(c, tau): return np.sign(c) * np.maximum(np.abs(c) - tau, 0)


def freeze(r, phold):
    out = np.empty_like(r); out[0] = r[0]
    for t in range(1, len(r)):
        out[t] = phold[t] * out[t - 1] + (1 - phold[t]) * r[t]
    return out


def detector(E, ph):
    clf = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.1, max_leaf_nodes=31,
                                         l2_regularization=1.0, random_state=0)
    return clf.fit(E[::3], ph[::3])           # every 3rd frame: neighbours are near-duplicates


def score(rows, P, F, **meta):
    err = P - F["fut"]
    r2 = 1 - (err ** 2).sum(0) / ((F["fut"] - F["fut"].mean(0)) ** 2).sum(0)
    for j, name in enumerate(DOA):
        row = dict(meta, doa=name, mae=np.abs(err[:, j]).mean(), r2=r2[j])
        for ph, c in CODE.items():
            m = F["ph_fut"] == c
            row[f"mae_{ph}"] = np.abs(err[m, j]).mean() if m.any() else np.nan
        rows.append(row)


def run_split(F_fit, F_eval, h, tune_set, rows, meta):
    """Fit everything on F_fit; tune penalty/tau on tune_set (a subset of F_fit's source data); score on F_eval."""
    Ft, Fv = tune_set
    # ridge models (penalty chosen on the tuning reps, then refit on F_fit)
    _, lam_e = tune_ridge(Ft["E"], Ft["fut"], Fv["E"], Fv["fut"])
    Xs = lambda F: np.concatenate([F["E"], F["now"]], 1)
    _, lam_s = tune_ridge(Xs(Ft), Ft["fut"], Xs(Fv), Fv["fut"])
    m_e = ridge_path(F_fit["E"], F_fit["fut"], [lam_e])[0]
    m_s = ridge_path(Xs(F_fit), F_fit["fut"], [lam_s])[0]
    # detector of current state, trained on F_fit
    det = detector(F_fit["E"], F_fit["ph_now"])
    # thresholds
    c_fit = pr(m_s, Xs(F_fit)) - F_fit["now"]
    still = F_fit["ph_fut"] != 2
    tau_rest = np.percentile(np.abs(c_fit[still]), 95, axis=0)
    m_s_t = ridge_path(Xs(Ft), Ft["fut"], [lam_s])[0]           # tuning-fold model for tau search
    c_v = pr(m_s_t, Xs(Fv)) - Fv["now"]
    grid = np.linspace(0, 1, 21)[:, None] * np.percentile(np.abs(c_v), 99, axis=0)[None]
    tau_val = np.array([grid[np.argmin([np.abs(Fv["now"][:, j] + deadband(c_v[:, j], g) - Fv["fut"][:, j]).mean()
                                        for g in grid[:, j]]), j] for j in range(5)])
    # predictions on F_eval
    corr = pr(m_s, Xs(F_eval)) - F_eval["now"]
    proba = det.predict_proba(F_eval["E"]); cls = list(det.classes_)
    p_mov = proba[:, cls.index(2)] if 2 in cls else np.zeros(len(proba))
    p_hold = proba[:, cls.index(1)] if 1 in cls else np.zeros(len(proba))
    r_e = pr(m_e, F_eval["E"])
    preds = {
        "ridge_emg": r_e,
        "ridge_state": F_eval["now"] + corr,
        "state_deadband_rest": F_eval["now"] + deadband(corr, tau_rest),
        "state_deadband_val": F_eval["now"] + deadband(corr, tau_val),
        "state_gate_tree": F_eval["now"] + p_mov[:, None] * corr,
        "emg_holdfreeze": freeze(r_e, p_hold),
        "persistence": F_eval["now"],
    }
    for name, P in preds.items():
        score(rows, P, F_eval, **meta, model=name)
    acc = (det.predict(F_eval["E"]) == F_eval["ph_now"]).mean()
    return dict(lam_emg=lam_e, lam_state=lam_s, det_acc=acc,
                **{f"tau_rest_{d}": t for d, t in zip(DOA, tau_rest)},
                **{f"tau_val_{d}": t for d, t in zip(DOA, tau_val)})


rows, info = [], []
t0 = time.time()
for subj in SUBJECTS:
    S = {k: load(subj, k) for k in (1, 2, 3)}
    valid = S[1]["valid"] & S[2]["valid"] & S[3]["valid"]
    for h_ms in HORIZONS:
        h = h_ms // 10
        F12 = cat(frames(S[1], h, valid), frames(S[2], h, valid)); F3 = frames(S[3], h, valid)
        v = np.isin(F12["rep"], VAL)
        Ft, Fv = sub(F12, ~v), sub(F12, v)
        meta = dict(subject=subj, amputee=subj in (11, 12), window_ms=W, history_ms=HM, horizon_ms=h_ms)
        # validation scores: fit on Ft, tune on an inner split of Ft (reps 7-8), score on Fv
        iv = np.isin(Ft["rep"], [7, 8])
        i_val = run_split(Ft, Fv, h, (sub(Ft, ~iv), sub(Ft, iv)), rows, dict(meta, split="val"))
        # test scores: fit on all of sessions 1-2, tune on reps 9-10, score on session 3
        i_test = run_split(F12, F3, h, (Ft, Fv), rows, dict(meta, split="test"))
        info.append(dict(meta, **{f"val_{k}": x for k, x in i_val.items()}, **{f"test_{k}": x for k, x in i_test.items()}))
    print(f"W{W} H{HM} subject {subj} done {time.time() - t0:.0f}s", flush=True)

tag = f"W{W}_H{HM}_S{'-'.join(map(str, SUBJECTS))}"
pd.DataFrame(rows).to_csv(OUT / f"models_{tag}.csv", index=False)
pd.DataFrame(info).to_csv(OUT / f"models_info_{tag}.csv", index=False)
