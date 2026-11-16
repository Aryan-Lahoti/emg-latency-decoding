"""Figure for run 3: results/bias_variance_ridge.png from the arrays bv.py saves (subject 3)."""
import os
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
g = np.load(os.path.join(ROOT, 'results', 'followups', 'geo_out.npz')); b = np.load(os.path.join(ROOT, 'results', 'followups', 'bv_out.npz'))
nv = int(g['nv']); idx = np.where(np.load(os.path.join(DATA_DIR, 'S3_E1_A1.npz'))['valid'])[0]
nm = lambda k: (f"RMS, electrode {idx[k]+1}" if k < nv else f"MAV, electrode {idx[k-nv]+1}")
i, j = int(g['i']), int(g['j']); g2, b2, ols, path, yy = g['g2'], g['b2'], g['ols'], g['path'], float(g['yy'])
wt = np.linalg.solve(g2 + 0.01 * np.eye(2), b2); r = np.linalg.norm(wt)
fig, ax = plt.subplots(1, 3, figsize=(16, 5)); a = ax[0]; lim = 22
w1, w2 = np.meshgrid(np.linspace(-lim, lim, 400), np.linspace(-lim, lim, 400)); W = np.stack([w1, w2], -1)
L = yy - 2 * (W @ b2) + np.einsum('...i,ij,...j->...', W, g2, W); Lmin = yy - b2 @ ols
a.contour(w1, w2, L, levels=Lmin + np.array([0.5, 2, 5, 10, 20, 40, 80, 160]), colors='#378ADD', linewidths=0.8)
t = np.linspace(0, 2 * np.pi, 300)
for rr in (r, 2 * r, 4 * r): a.plot(rr * np.cos(t), rr * np.sin(t), color='#888780', lw=0.8, ls='--')
a.plot(path[:, 0], path[:, 1], color='#D85A30', lw=2, label='ridge path (penalty large→small)')
a.plot(*ols, 'o', color='#185FA5', ms=8, label=f'no penalty (OLS): ({ols[0]:.0f}, {ols[1]:.0f})')
a.plot(*wt, 'o', color='#D85A30', ms=8, label=f'tuned penalty: ({wt[0]:.1f}, {wt[1]:.1f})'); a.plot(0, 0, 'k+', ms=10)
a.set_xlim(-lim, lim); a.set_ylim(-lim, lim); a.set_aspect('equal'); a.set_xlabel(f'weight on {nm(i)}'); a.set_ylabel(f'weight on {nm(j)}')
a.set_title(f'1. Two near-identical inputs (corr {float(g["corr"]):.3f})\nblue = error contours, grey = weight-size circles', fontsize=10); a.legend(fontsize=8, loc='lower left')
L_ = b['LAMS']; best = L_[int(np.argmin(b['tot']))]; a = ax[1]
a.loglog(L_, b['bias2'], color='#D85A30', label='bias² (+ irreducible noise)'); a.loglog(L_, b['var'], color='#378ADD', label='variance'); a.loglog(L_, b['tot'], 'k--', label='total error')
a.axvline(best, color='#888780', lw=0.8); a.set_xlabel('penalty strength λ  (left: little shrinkage, right: heavy)')
a.set_ylabel('squared error (deg²) on held-out reps'); a.set_title('2. Bias–variance, bootstrap over 16 training repetitions', fontsize=10); a.legend(fontsize=8)
a = ax[2]; a.semilogx(L_, np.sqrt(b['tr']), color='#1D9E75', label='training RMSE'); a.semilogx(L_, np.sqrt(b['va']), color='#D85A30', label='validation RMSE')
a.axvline(best, color='#888780', lw=0.8); a.set_xlabel('penalty strength λ'); a.set_ylabel('RMSE (degrees)')
a2 = a.twinx(); a2.semilogx(L_, b['norms'], color='#888780', ls=':', label='size of weight vector'); a2.set_ylabel('‖w‖ (size of weights)', color='#5F5E5A')
a.set_title('3. Training vs validation error, and weight size', fontsize=10)
h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels(); a.legend(h1 + h2, l1 + l2, fontsize=8, loc='center left')
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'results', 'bias_variance_ridge.png'), dpi=130)
