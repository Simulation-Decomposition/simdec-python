from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats


__all__ = ["decomposition"]


@dataclass
class DecompositionResult:
    statistic: np.ndarray
    bins: pd.DataFrame
    states: np.ndarray


def decomposition(
    inputs: np.ndarray,
    output: np.ndarray,
    significance: np.ndarray,
    var_names: str = None,
    dec_limit: float = 1,
    states: np.ndarray | None = None,
    threshold_type: Literal["percentile", "median"] | None = "median",
) -> DecompositionResult:
    # 1. variables for decomposition
    var_order = np.argsort(significance)

    # TODO could use pandas or an index to select variable
    # var_names = var_names[var_order]

    # only keep the explained variance corresponding to `dec_limit`
    significance = significance[var_order]
    n_var_dec = np.where(np.cumsum(significance) < dec_limit)[0].size

    # var_names = var_names[var_order[:n_var_dec]]
    inputs = inputs[:, var_order[:n_var_dec]]

    # 2. states formation
    if states is None:
        states = 3 if n_var_dec < 3 else 2
        states = [states] * n_var_dec

        # categorical for a given variable
        for i in range(n_var_dec):
            n_unique = np.unique(inputs[:, i]).size
            states[i] = n_unique if n_unique < 5 else states[i]

    # 3. decomposition
    bins = []

    def statistic(inputs):
        """Custom function to keep track of the content of bins."""
        bins.append(inputs)
        return np.median(inputs)

    res = stats.binned_statistic_dd(
        inputs, values=output, statistic=statistic, bins=states
    )

    bins = pd.DataFrame(bins[1:]).T

    return DecompositionResult(res.statistic, bins, states)
