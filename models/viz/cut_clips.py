"""Cut the full-session video into one clip per movement (both test repetitions, 2 s either side).
Writes NN_name_full.mp4 (1280x720, used on the website as docs/assets/media/m1..m9.mp4) and NN_name_hand.mp4 (hand only)."""
import os, sys, json, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DATA_DIR = os.environ.get('DB8_PROCESSED', os.path.join(ROOT, 'data', 'processed'))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'results', 'viz', 'emg_decoder_subject3_session3.mp4')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'results', 'viz', 'clips'); os.makedirs(OUT, exist_ok=True)
r = np.load(os.path.join(DATA_DIR, 'S3_E1_A3.npz'))['restim'][300:]          # same 3 s warm-up as the model
NAMES = {1: "thumb_flexion", 2: "thumb_abduction", 3: "index_flexion", 4: "middle_flexion", 5: "ring_little_flexion",
         6: "index_pointer", 7: "cylindrical_grip", 8: "lateral_grip", 9: "tripod_grip"}
man = []
for k, n in NAMES.items():
    idx = np.flatnonzero(r == k); a = max(idx[0] / 100 - 2, 0); b = min(idx[-1] / 100 + 2, len(r) / 100); base = f"{k:02d}_{n}"
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{a:.2f}', '-i', SRC, '-t', f'{b - a:.2f}', '-an', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', '-c:v', 'libx264', '-preset', 'slow']
    subprocess.run(cmd + ['-crf', '27', os.path.join(OUT, f'{base}_full.mp4')], check=True)
    subprocess.run(cmd + ['-vf', 'crop=640:720:0:0,scale=360:404', '-crf', '28', os.path.join(OUT, f'{base}_hand.mp4')], check=True)
    man.append(dict(id=k, name=n.replace('_', ' '), start_s=round(a, 2), duration_s=round(b - a, 2), full=f'{base}_full.mp4', hand=f'{base}_hand.mp4'))
json.dump(man, open(os.path.join(OUT, 'clips.json'), 'w'), indent=1)
