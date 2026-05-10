from __future__ import annotations

from typing import Iterable, List

import numpy as np

from agent import Agent


def clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def gini(values: Iterable[float]) -> float:
    x = np.array(list(values), dtype=float)
    if len(x) == 0:
        return 0.0
    if np.allclose(x, 0.0):
        return 0.0
    x = np.sort(x)
    n = len(x)
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * x) / (n * np.sum(x))) - (n + 1) / n)


def behavior_entropy(values: Iterable[float], bins: int = 10) -> float:
    arr = np.array(list(values), dtype=float)
    hist, _ = np.histogram(arr, bins=bins, range=(-1.0, 1.0), density=True)
    p = hist / (hist.sum() + 1e-12)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def avg_neighbor_u(agents: List[Agent], neighbors: List[List[int]]) -> float:
    vals = []
    for i, nbrs in enumerate(neighbors):
        if not nbrs:
            vals.append(agents[i].u)
            continue
        vals.append(float(np.mean([agents[j].u for j in nbrs])))
    return float(np.mean(vals)) if vals else 0.0
