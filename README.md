# emg-latency-decoding
# Latency-aware EMG decoding (NinaPro DB8)

## Data
- Raw: NinaPro DB8 (ninapro.hevs.ch → DB8). Put the .mat files in `data/raw/DB8/`.
- Processed: run `notebooks/06_build_dataset.ipynb` → `data/processed/S{s}_E1_A{k}.npz`
  (s = subject 1–12, k = session 1–3). Subjects 11 and 12 are transradial amputees.

## One row = one 10 ms frame
| key | shape | meaning |
|---|---|---|
| t | (T,) | frame time (s) |
| rms_50/100/200, mav_50/100/200 | (T,16) | causal EMG envelope over the last 50/100/200 ms |
| glove | (T,18) | glove angles at the same instant → `emgproc.to_doa()` gives 5 DoA targets |
| restim, rerep | (T,) | movement (0 = rest, 1–9) and repetition labels |
| valid | (16,) | False = electrode not recorded (S11: 3 empty, S12: 4 empty) |

## Fixed preprocessing (done in the builder, no learning)
4th-order Butterworth low-pass 450 Hz → downsample 2000→1000 Hz → 2nd-order high-pass 20 Hz
(all causal, `sosfilt`) → moving RMS/MAV. Filter delay ≈ 1–3 ms; window delay ≈ W/2.
No notch needed (mains already removed in the released data).

## Rules for training (to avoid leakage)
- Train: sessions 1–2. Test: session 3, used once at the end.
- Validation for tuning: held-out repetitions from sessions 1–2.
- Normalisation statistics from training data only; use only `valid` channels.
- Horizon Δ: features at frame i → target at frame i + Δ/10.