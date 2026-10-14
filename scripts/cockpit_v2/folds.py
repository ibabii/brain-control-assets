"""Tileable brain-fold height field (Gray-Scott labyrinth). numpy only."""
import numpy as np


def _lap(a):
    return np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1) - 4 * a


def blur(a, passes=2):
    for _ in range(passes):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0)) / 3
        a = (a + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 3
    return a


def upsample(a, f):
    a = np.kron(a, np.ones((f, f)))
    return blur(a, f)


def labyrinth(n=128, steps=7000, F=0.042, k=0.061, seed=7):
    """F/k chosen for short meandering worms with many ends, like gyri."""
    rng = np.random.default_rng(seed)
    U = np.ones((n, n))
    V = np.zeros((n, n))
    for _ in range(n * n // 300):
        x, y = rng.integers(0, n - 6, 2)
        U[y:y + 6, x:x + 6] = 0.5
        V[y:y + 6, x:x + 6] = 0.25
    V += rng.random((n, n)) * 0.02
    for _ in range(steps):
        uvv = U * V * V
        U += 0.16 * _lap(U) - uvv + F * (1 - U)
        V += 0.08 * _lap(V) + uvv - (F + k) * V
    return V


def distance(mask, iters=40):
    """Chamfer distance (px) from True cells, periodic."""
    d = np.where(mask, 0.0, 1e9)
    for _ in range(iters):
        d = np.minimum.reduce([d, np.roll(d, 1, 0) + 1, np.roll(d, -1, 0) + 1, np.roll(d, 1, 1) + 1, np.roll(d, -1, 1) + 1,
                               np.roll(np.roll(d, 1, 0), 1, 1) + 1.414, np.roll(np.roll(d, 1, 0), -1, 1) + 1.414,
                               np.roll(np.roll(d, -1, 0), 1, 1) + 1.414, np.roll(np.roll(d, -1, 0), -1, 1) + 1.414])
    return d


def fold_height(n=128, up=4, seed=7, core=0.12):
    """0 = groove floor, 1 = top of a fold. Round tubes around the worm centrelines; V-grooves where tubes meet."""
    v = labyrinth(n, seed=seed)
    v = upsample((v - v.min()) / (v.max() - v.min()), up)
    d = distance(v > np.percentile(v, 100 * (1 - core)), iters=60)
    t = np.clip(d / np.percentile(d, 98), 0, 1)
    return blur(np.sqrt(1 - t ** 2), 1)
