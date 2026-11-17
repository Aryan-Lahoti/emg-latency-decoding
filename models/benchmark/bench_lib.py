"""Shared loading, features and evaluation for the benchmark effort.

Protocol (same as literature): per-subject models, train on sessions 1-2, test on session 3, 5 DoAs, horizon 0.
Model selection uses validation: fit on reps 1-8 of sessions 1-2, score on reps 9-10.
All features are causal.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..','..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
MODELS = os.path.join(ROOT, 'models')

from pathlib import Path
import numpy as np
from scipy.signal import lfilter

DATA = Path(DATA_DIR)
A_T = np.zeros((18, 5))
A_T[[0, 1, 3, 16], 0] = [0.639, 0.383, -0.639, -0.19]
A_T[2, 1] = 1.0
A_T[[4, 5], 2] = [0.4, 0.6]
A_T[[6, 7], 3] = [0.4, 0.6]
A_T[[9, 10, 12, 13], 4] = [0.1667, 0.3333, 0.1667, 0.3333]
DOA = ["thumb_rot", "thumb_flex", "index", "middle", "ring_little"]
WARM = 300  # frames (3 s) dropped at the start of each session so every filter has warmed up


def load(subj, sess):
    d = np.load(DATA / f"S{subj}_E1_A{sess}.npz")
    rep = d["rerep"].astype(int).copy(); last = 1
    for i in range(len(rep)):
        if rep[i] > 0: last = rep[i]
        else: rep[i] = last
    Y = d["glove"].astype(np.float64) @ A_T
    v = np.zeros(len(Y)); v[4:-4] = np.abs(Y[8:] - Y[:-8]).max(1) / 0.08
    ph = np.where(v > 20, 2, np.where(d["restim"] == 0, 0, 1))
    s = dict(Y=Y, rep=rep, ph=ph, valid=d["valid"])
    for k in d.files:
        if k[:3] in ("rms", "mav"): s[k] = d[k].astype(np.float64)
    return s


def ema(x, tau_s, dt=0.01):
    a = 1 - np.exp(-dt / tau_s)
    return lfilter([a], [1, -(1 - a)], x, axis=0, zi=np.ones((1, x.shape[1])) * x[:1] * (1 - a))[0]


def integrator_features(s, valid, base="rms_50", taus=(0.05, 0.15, 0.5, 1.5), log=False):
    e = s[base][:, valid]
    if log: e = np.log(e + 1e-7)
    return np.concatenate([e] + [ema(e, t) for t in taus], 1)


def lag_features(s, valid, w=100, lags=(0, 5, 10, 20, 30, 50, 75, 100, 150)):
    b = np.concatenate([s[f"rms_{w}"][:, valid], s[f"mav_{w}"][:, valid]], 1)
    return np.concatenate([np.roll(b, l, 0) for l in lags], 1)


def ridge_path(X, Y, lams):
    mu, sd = X.mean(0), X.std(0) + 1e-12; Z = (X - mu) / sd; ym = Y.mean(0)
    ev, V = np.linalg.eigh(Z.T @ Z); B = V.T @ (Z.T @ (Y - ym)); n = len(Z)
    return [(mu, sd, ym, V @ (B / (ev + l * n)[:, None])) for l in lams]


def ridge_pred(m, X):
    mu, sd, ym, W = m
    return ((X - mu) / sd) @ W + ym


def metrics(Y, P):
    err = P - Y
    mae = np.abs(err).mean(0)
    r2 = 1 - (err ** 2).sum(0) / ((Y - Y.mean(0)) ** 2).sum(0)
    return mae, r2


def splits(S, feat_fn, h=0):
    """Return train(reps1-8)/val(reps9-10)/full-train(s1-2)/test(s3) arrays for a feature function."""
    out = {}
    for k in (1, 2, 3):
        X = feat_fn(S[k]); Y = S[k]["Y"]; n = len(Y) - h
        keep = np.arange(n) >= WARM
        out[k] = (X[:n][keep], Y[h:h + n][keep], S[k]["rep"][:n][keep], S[k]["ph"][h:h + n][keep])
    X12 = np.concatenate([out[1][0], out[2][0]]); Y12 = np.concatenate([out[1][1], out[2][1]])
    r12 = np.concatenate([out[1][2], out[2][2]]); p12 = np.concatenate([out[1][3], out[2][3]])
    v = np.isin(r12, [9, 10])
    return dict(Xtr=X12[~v], Ytr=Y12[~v], Xva=X12[v], Yva=Y12[v], pva=p12[v],
                X12=X12, Y12=Y12, Xte=out[3][0], Yte=out[3][1], pte=out[3][3])
