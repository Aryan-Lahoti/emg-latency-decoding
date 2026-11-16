# Latency-aware EMG decoding for prosthetic hands (NinaPro DB8)

ES 335 Machine Learning course project, IIT Gandhinagar, 2026.

**Project website:** https://aryan-lahoti.github.io/emg-latency-decoding/

We predict five finger angles from 16 channels of forearm EMG for the 12 participants of
NinaPro DB8 (10 able-bodied, 2 transradial amputees), and measure how the decoder's window
length and prediction horizon trade accuracy against delay.

| Result (test session 3) | Value |
|---|---|
| Final decoder, all 12 people | MAE 6.39°, R² 0.76 |
| Able-bodied / amputees | 6.06° / 8.04° |
| Predicting 150 ms ahead | 6.56°, R² 0.74 |
| Decoder delay | about 45 ms (filters 1-3 ms, 50 ms envelope about 25 ms, inference 16.5 ms median) |
| First ridge baseline | 9.35°, R² 0.53 |

The website explains the reasoning. This repository lets you check it.

## Repository layout

| Path | What it holds |
|---|---|
| `src/emgproc.py` | Loading, causal filters, envelope features, onset detection, 18-to-5 glove mapping, dataset builder |
| `notebooks/01_inspect_data.ipynb` | First look at one raw file: variables, labels, rates |
| `notebooks/02_spectrum.ipynb` | Power spectrum of every channel; rest vs movement amplitude |
| `notebooks/03_filters.ipynb` | Filter design and measured group delay |
| `notebooks/04_envelope.ipynb` | Moving-RMS envelope, window delay, first onset-timing analysis |
| `notebooks/05_leads_all_subjects.ipynb` | EMG-vs-glove onset timing for all 12 people (writes `results/onset_leads.csv`) |
| `notebooks/06_build_dataset.ipynb` | Builds the 36 processed files |
| `notebooks/07_targets.ipynb` | The five finger targets; which finger moves in which movement |
| `models/` | Training and evaluation scripts (see "Model runs" below) |
| `results/` | Result tables and figures written by the notebooks and scripts |
| `docs/` | The website (GitHub Pages). Every number shown is in `docs/assets/js/data.js` |

## Setup

Python 3.11.

```
git clone https://github.com/Aryan-Lahoti/emg-latency-decoding
cd emg-latency-decoding
pip install -r requirements.txt
```

## Data access

The data is not in this repository.

1. Download NinaPro DB8 from https://ninapro.hevs.ch/instructions/DB8.html
   (also at Newcastle University, doi:10.25405/data.ncl.9577598.v1). There are 36 MATLAB files,
   `S{1..12}_E1_A{1,2,3}.mat`, about 1 GB each for sessions 1 and 2.
2. Put them in `data/raw/DB8/`.

The notebooks were written on Windows and use absolute paths starting with `D:\emg-project`.
Either clone to that location or change the path strings at the top of each notebook.

## Preprocessing (exact steps)

Run `notebooks/06_build_dataset.ipynb`. For each raw file it calls `emgproc.build_file`, which:

1. low-pass filters the 2 kHz EMG at 450 Hz (4th-order Butterworth, `sosfilt`, causal);
2. keeps every second sample (1 kHz);
3. high-pass filters at 20 Hz (2nd-order Butterworth, causal);
4. computes causal moving RMS and MAV over the last 50, 100 and 200 ms;
5. writes one frame every 10 ms, with the glove reading at the same instant.

Output: `data/processed/S{s}_E1_A{k}.npz` (s = subject 1-12, k = session 1-3).

| key | shape | meaning |
|---|---|---|
| `t` | (T,) | frame time in seconds |
| `rms_50/100/200`, `mav_50/100/200` | (T,16) | causal EMG envelope over the last 50/100/200 ms |
| `glove` | (T,18) | glove angles at the same instant; `emgproc.to_doa()` gives the 5 targets |
| `restim`, `rerep` | (T,) | movement (0 = rest, 1-9) and repetition labels |
| `valid` | (16,) | False = electrode not recorded (subject 11: 3 empty, subject 12: 4 empty) |

Nothing in preprocessing is learned from data. Filter delay is 1-3 ms; window delay is about W/2.
No notch filter is used because mains interference was already removed in the released data.

## Data splits

- **Train:** sessions 1 and 2 of each person. **Test:** session 3, used to report results.
- **Validation for ridge and the gates:** repetitions 9 and 10 of sessions 1 and 2.
- **Validation for the final decoder:** across sessions (train on session 1, validate on session 2, and the reverse).
- Splits are by session or repetition, never by random frames.
- Scaling statistics come from training data only. Only `valid` channels are used.
- Horizon Δ: features at frame i are paired with targets at frame i + Δ/10.
- Phases: "moving" = any finger faster than 20°/s; "hold" = still during a repetition; "rest" = still between repetitions.

## Model runs

One model per person in every run. Full commands, outputs and the analyses that only print are in
[`models/README.md`](models/README.md). Set `DB8_PROCESSED` if your processed files are not in `data/processed/`.

| Run | What it does | Script | Result file |
|---|---|---|---|
| 1 | Persistence and ridge, 3 windows × 4 horizons | `models/train_grid.py`, `models/plot_grid.py` | `results/grid_raw.csv`, `results/grid_raw.png` |
| 2 | Window without history; history length; ridge with current angle; error by phase | `models/experiments.py`, `models/plot_followups.py` | `results/followups_all.csv`, `results/followups_summary.png` |
| 3 | Bias-variance and ridge geometry (subject 3) | `models/bv.py`, `models/bv_plot.py` | `results/bias_variance_ridge.png` |
| 4 | Deadband and tree gates, validation ranking, corner checks | `models/gates.py` | `results/gates/` |
| 5 | No-EMG velocity baselines, perfect-gate ceiling, label-noise floors | `models/velocity_baselines.py` | `results/velocity_baselines.csv` |
| 6 | Final decoder: integrator features, neural net + boosted trees, cross-session selection, test, ablations, horizon sweep, inference timing | `models/benchmark/` | `results/benchmark/` |
| 7 | MuJoCo replay video and per-movement clips | `models/viz/` | `results/viz/`, `docs/assets/media/` |

Run scripts from the repository root, for example `python models/train_grid.py data/processed results`.

## Website

`docs/` is a static site with no build step. Open `docs/index.html` in a browser, or serve it with
`python -m http.server --directory docs`.

The nine MuJoCo clips at the top of the Results section are read from `docs/assets/media/`
(`m1.mp4` to `m9.mp4`, one per movement; the list is `clips` in `docs/assets/js/data.js`).

## Integrity notes

- While debugging the first ridge run, session-3 results for subjects 1 and 5 were looked at. No setting was chosen from them.
- Per-session calibration was selected on validation and slightly hurt on the test session (6.39° with, 6.15° without). The selected model is reported as the official result.
- Tree settings are library defaults and were not tuned.
- The per-person label time shift and the recurrent network described in the proposal were not run.

## AI-use disclosure

We used Claude (Anthropic) throughout the project.

- **What it did:** literature and dataset search; explanations of signal-processing and machine-learning concepts; writing most of the preprocessing, training and evaluation code from our instructions; running the model training in its own workspace on our processed files; drafting the website and this README.
- **What we did:** chose the question and dataset; ran the preprocessing notebooks on our own machine and inspected the outputs; made the modelling decisions described on the website (state for holds, trees as a soft state detector, testing the reason for ridge, the delay budget).
- **How we checked it:** figures in the data and signal sections come from notebooks we ran ourselves; quoted result tables were recomputed from the saved result files; claims by the assistant that we tested and found wrong are corrected on the website.

## Citations

- Krasoulis A., Vijayakumar S., Nazarpour K. (2019). Effect of user practice on prosthetic finger control with an intuitive myoelectric decoder. Frontiers in Neuroscience 13:891. doi:10.3389/fnins.2019.00891 (dataset and 18-to-5 mapping)
- NinaPro DB8. https://ninapro.hevs.ch/instructions/DB8.html ; doi:10.25405/data.ncl.9577598.v1
- Leroux N., Finkbeiner J., Neftci E. (2023). Online transformers with spiking neurons for fast prosthetic hand control. arXiv:2303.11860
- Zanghieri M. et al. (2021). sEMG-based regression of hand kinematics with temporal convolutional networks on a low-power edge microcontroller. IEEE COINS. doi:10.1109/COINS51742.2021.9524188
- Baracat F., Manneschi L., Donati E. (2025). Heterogeneous population encoding for multi-joint regression using sEMG signals. arXiv:2501.15347
- Gilardini S., Ma C., Nazarpour K. (2026). KinEMbed: decoding kinematics from electromyography via cross-modal contrastive learning. Workshop on Structured Data for Health at ICML 2026. arXiv:2607.04820
- Farrell T. R., Weir R. F. (2007). The optimal controller delay for myoelectric prostheses. IEEE TNSRE 15(1), 111-118.
- Cavanagh P. R., Komi P. V. (1979). Electromechanical delay in human skeletal muscle under concentric and eccentric contractions. Eur. J. Appl. Physiol. 42, 159-163.
- Diedrichsen J., Hazeltine E., Nurss W. K., Ivry R. B. (2003). The role of the corpus callosum in the coupling of bimanual isometric force pulses. J. Neurophysiol. 90, 2409-2418.
- George J. A., Tully T. N., Colgan P. C., Clark G. A. (2020). Bilaterally mirrored movements improve the accuracy and precision of training data for supervised learning of neural or myoelectric prosthetic control. IEEE EMBC. arXiv:2001.08807
- Website fonts: Bricolage Grotesque and Atkinson Hyperlegible Next, SIL Open Font License 1.1.
