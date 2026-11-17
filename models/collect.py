"""Merge the per-process CSV parts that the training scripts write into the combined tables used on the website."""
import os, glob
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
R = lambda *p: os.path.join(ROOT, 'results', *p)
def merge(pattern, out, exclude='info'):
    fs = [f for f in sorted(glob.glob(pattern)) if exclude not in os.path.basename(f) and os.path.abspath(f) != os.path.abspath(out)]
    if fs:
        pd.concat([pd.read_csv(f) for f in fs]).to_csv(out, index=False); print(out, len(fs), 'parts')
merge(R('followups', '*_S*.csv'), R('followups_all.csv'))                       # run 2
merge(R('gates', 'models_W100_H1500_S*.csv'), R('gates', 'models_W100_H1500_all.csv'))   # run 4
merge(R('gates', 'models_W*_S*.csv'), R('gates', 'models_all_settings.csv'))            # run 4 corners
merge(R('benchmark', 's2b_xsess_*.csv'), R('benchmark', 's2b_xsess_all.csv'), exclude='_all')
merge(R('benchmark', 's3_test_*.csv'), R('benchmark', 's3_test_all.csv'), exclude='_all')
merge(R('benchmark', 's4_[ab]*.csv'), R('benchmark', 's4_all.csv'), exclude='_all')
