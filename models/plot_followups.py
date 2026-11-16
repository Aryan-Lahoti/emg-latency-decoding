"""Figure for run 2: results/followups_summary.png (window without history, history length, stateful ridge vs persistence)."""
import os
import pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
r = pd.read_csv(os.path.join(ROOT, 'results', 'followups_all.csv')); g = pd.read_csv(os.path.join(ROOT, 'results', 'grid_raw.csv'))
r = r[~r.amputee]; g = g[~g.amputee]
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
a = r[(r.experiment == 'window_only') & (r.horizon_ms == 0)].groupby('window_ms').r2.mean()
b = g[(g.model == 'ridge') & (g.horizon_ms == 0)].groupby('window_ms').r2.mean()
ax[0].plot(a.index, a.values, 'o-', color='#378ADD', label='current snapshot only'); ax[0].plot(b.index, b.values, 'o-', color='#D85A30', label='+ 1.5 s history')
ax[0].set_xlabel('window (ms)'); ax[0].set_ylabel('R2 (horizon 0)'); ax[0].set_title('A. Window length matters only without history'); ax[0].legend(fontsize=8); ax[0].set_ylim(0.3, 0.6)
h = r[(r.experiment == 'history') & (r.horizon_ms == 0)].groupby('history_ms').r2.mean()
ax[1].plot(h.index, h.values, 'o-', color='#1D9E75'); ax[1].set_xlabel('history length (ms)'); ax[1].set_ylabel('R2 (100 ms window, horizon 0)'); ax[1].set_title('B. More past context helps, with diminishing returns'); ax[1].set_ylim(0.3, 0.6)
c = r[r.experiment == 'stateful']
for m, col, lab in [('persistence', 'k', 'persistence (current angle)'), ('ridge+angle', '#D85A30', 'ridge: current angle + EMG')]:
    s = c[c.model == m].groupby('horizon_ms').mae_moving.mean(); ax[2].plot(s.index, s.values, 'o-', color=col, label=lab)
ax[2].set_xlabel('prediction horizon (ms)'); ax[2].set_ylabel('MAE during movement (degrees)'); ax[2].set_title('C. EMG improves prediction while fingers move'); ax[2].legend(fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'results', 'followups_summary.png'), dpi=130)
