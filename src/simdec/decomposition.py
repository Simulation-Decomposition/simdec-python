from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


__all__ = ["decomposition"]


@dataclass
class DecompositionResult:
    var_names: list[str]
    statistic: np.ndarray
    bins: pd.DataFrame
    states: np.ndarray


def decomposition(
    inputs: pd.DataFrame,
    output: pd.DataFrame,
    significance: np.ndarray,
    dec_limit: float = 1,
    states: list[int] | None = None,
) -> DecompositionResult:
    var_names = inputs.columns
    inputs = inputs.to_numpy()
    output = output.to_numpy()

    # 1. variables for decomposition
    var_order = np.argsort(significance)[::-1]

    # only keep the explained variance corresponding to `dec_limit`
    significance = significance[var_order]
    n_var_dec = np.where(np.cumsum(significance) < dec_limit)[0].size

    var_names = var_names[var_order[:n_var_dec]]
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

    return DecompositionResult(var_names, res.statistic, bins, states)
