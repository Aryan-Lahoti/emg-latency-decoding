# Model runs

Every script runs from the repository root and reads the 36 processed files from `data/processed/`
(override with `DB8_PROCESSED=/path/to/processed`). One model per person in every run.
Train = sessions 1 and 2, test = session 3. Results land in `results/`.

The training runs split subjects across two processes (`1,2,3,4,5,6` and `7,8,9,10,11,12`) to use two CPU cores;
`python models/collect.py` merges the parts into the combined tables the website uses.

| Run | What | Command | Output |
|---|---|---|---|
| 1 | Persistence + ridge (RMS+MAV, 1.5 s history), 3 windows × 4 horizons. Penalty chosen on repetitions 9–10 | `python models/train_grid.py data/processed results` then `python models/plot_grid.py` | `results/grid_raw.csv`, `grid_raw_lambdas.csv`, `grid_raw.png` |
| 2a | Ridge, current snapshot only, windows 50/100/200 ms | `python models/experiments.py data/processed results/followups window_only 1,2,3,4,5,6` (and 7–12) | `results/followups/window_only_*.csv` |
| 2b | Ridge, 100 ms window, history 0 / 0.3 / 0.75 / 1.5 s | same with `history` | `results/followups/history_*.csv` |
| 2c | Ridge with current angle + EMG vs persistence, error by phase | same with `stateful` | `results/followups/stateful_*.csv` |
| 2 | Merge and plot | `python models/collect.py` then `python models/plot_followups.py` | `results/followups_all.csv`, `followups_summary.png` |
| 3 | Bias–variance by bootstrap over repetitions, ridge geometry on two inputs (subject 3) | `python models/bv.py` then `python models/bv_plot.py` | `results/followups/bv_out.npz`, `geo_out.npz`, `results/bias_variance_ridge.png` |
| 4 | Task 2 gates: EMG-only ridge, stateful ridge, soft deadband (two thresholds), tree gate, hold-freeze, persistence. Val and test scores | `python models/gates.py data/processed results/gates 100 1500 <subjects>` | `results/gates/models_W100_H1500_*.csv`, `models_info_*.csv` |
| 4b | Corner checks | same with `50 300` and `200 1500` | `results/gates/models_W50_H300_*`, `models_W200_H1500_*`; merged in `models_all_settings.csv` |
| 5 | No-EMG velocity baselines, perfect-gate ceiling, label-noise floors, finger ranges | `python models/velocity_baselines.py` | `results/velocity_baselines.csv` |
| 6.1 | Leaky-integrator features + ridge, validation | `python models/benchmark/s1_integrator_ridge.py` | `results/benchmark/s1_val.csv` |
| 6.2 | Boosted trees and neural net, same-session validation (subjects 1, 3, 5, 8, 11 only) | `python models/benchmark/s2_nonlinear_within_session.py 1,3,5 a` (and `8,11 b`) | `results/benchmark/s2_val.csv` |
| 6.3 | Per-session calibration: first minute vs whole session; causal variants (session 1 ↔ 2 only) | `python models/benchmark/calib_first_vs_whole.py`, `calib_causal.py` | printed (see below) |
| 6.4 | Model selection across sessions (train s1 → test s2 and reverse), ± calibration | `python models/benchmark/s2b_cross_session_selection.py <subjects> <tag>` | `results/benchmark/s2b_xsess_all.csv` |
| 6.5 | Final test on session 3, chosen model + ablations; saves predictions for the video | `python models/benchmark/s3_final_test.py <subjects> <tag>` | `results/benchmark/s3_test_all.csv`, `s3_preds_a.npz`, `s3_preds_b.npz` |
| 6.6 | Context ablation (timescales ≤1.5 s) and horizon sweep 50/100/150 ms | `python models/benchmark/s4_ablation_horizon.py <subjects> <tag>` | `results/benchmark/s4_all.csv` |
| 6.7 | Inference time per frame | `python models/benchmark/timing.py` | printed: median 16.5 ms, p95 23.7 ms |
| 7 | MuJoCo video and per-movement clips (needs `MENAGERIE=/path/to/mujoco_menagerie`, `MUJOCO_GL=egl`) | `cd models/viz && python make_video.py 3 0 260 out.mp4`, then `python models/viz/cut_clips.py` | `results/viz/emg_decoder_subject3_session3.mp4`, clips (`docs/assets/media/m1–m9.mp4`) |

## Analyses that print instead of writing a file

| Script | What it prints | Values we got |
|---|---|---|
| `models/analysis/auc_all.py` | Rest-vs-hold and still-vs-moving separability from mean EMG level (AUC), session 3, descriptive | Table on the website (`auc` in `docs/assets/js/data.js`) |
| `models/analysis/holdcheck.py` | During holds: how far EMG-only ridge sits from rest toward the held angle; direction of stateful corrections (subjects 1, 3, 5, 8) | 58–68% of the held deviation; corrections toward rest 50–62% of the time |
| `models/analysis/offset.py` | Session 1 → 2 offsets, ridge on integrator features (subjects 1, 3, 5, 8, 11) | Offsets up to about 25° per DoA |
| `models/benchmark/calib_first_vs_whole.py` | Cross-session MAE, no calibration / first 60 s / whole session (all 12) | 13.79° / 16.90° / 12.08° |
| `models/benchmark/calib_causal.py` | Same, causal variants | none 13.79°, whole 12.08°, expanding 11.82°, slow EMA in between |

## Notes

- Neural network: scikit-learn `MLPRegressor` (256, 128), at most 60 epochs with early stopping; it usually stops at the cap with a
  convergence warning. Trees: `HistGradientBoostingRegressor`, 400 iterations max, early stopping. Settings were chosen once, not tuned.
- Rows: the first 3 s of each session are dropped so every integrator has warmed up (benchmark runs); 1.5 s for the lag-feature runs.
- `results/benchmark/logs/` holds the console output of the long runs.
