"""Per-frame inference time of the final decoder's readout (run 6). Uses random data of the real input size (192 features)
and the final model's settings with early stopping off, so the tree count is the 400 maximum (an upper bound)."""
import time
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
rng = np.random.default_rng(0); X = rng.normal(size=(20000, 192)); Y = X[:, :5] @ rng.normal(size=(5, 5)) + rng.normal(size=(20000, 5))
g = [HistGradientBoostingRegressor(max_iter=400, max_leaf_nodes=63, early_stopping=False).fit(X, Y[:, j]) for j in range(5)]
m = MLPRegressor(hidden_layer_sizes=(256, 128), max_iter=5).fit(X, Y)
x = X[:1]; ts = []
for _ in range(300):
    t = time.perf_counter(); [gg.predict(x) for gg in g]; m.predict(x); ts.append(time.perf_counter() - t)
ts = np.array(ts) * 1000; print('per-frame inference ms: median', np.median(ts).round(2), 'p95', np.percentile(ts, 95).round(2))
