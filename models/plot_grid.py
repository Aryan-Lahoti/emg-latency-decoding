"""Figure for run 1: results/grid_raw.png from results/grid_raw.csv (able-bodied subjects)."""
import os
import pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
r = pd.read_csv(os.path.join(ROOT, 'results', 'grid_raw.csv')); r = r[~r.amputee]
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for w, c in zip([50, 100, 200], ['#378ADD', '#1D9E75', '#D85A30']):
    s = r[(r.model == 'ridge') & (r.window_ms == w)].groupby(['subject', 'horizon_ms']).mae.mean().groupby('horizon_ms')
    ax[0].errorbar(s.mean().index, s.mean().values, yerr=s.std().values, marker='o', capsize=3, color=c, label=f'ridge, {w} ms window')
p = r[r.model == 'persistence'].groupby(['subject', 'horizon_ms']).mae.mean().groupby('horizon_ms').mean()
ax[0].plot(p.index, p.values, 'k--o', label='persistence (knows current angle)')
ax[0].set_xlabel('prediction horizon (ms)'); ax[0].set_ylabel('MAE (degrees), mean over 5 DoAs'); ax[0].set_title('Able-bodied subjects (n=10), test session'); ax[0].legend(fontsize=8)
for w, c in zip([50, 100, 200], ['#378ADD', '#1D9E75', '#D85A30']):
    s = r[(r.model == 'ridge') & (r.window_ms == w)].groupby(['subject', 'horizon_ms']).r2.mean().groupby('horizon_ms').mean()
    ax[1].plot(s.index, s.values, marker='o', color=c, label=f'{w} ms window')
ax[1].set_xlabel('prediction horizon (ms)'); ax[1].set_ylabel('R2, mean over 5 DoAs'); ax[1].set_title('Ridge R2 vs horizon'); ax[1].legend(fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'results', 'grid_raw.png'), dpi=130)
