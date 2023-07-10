from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats


__all__ = ["decomposition"]


@dataclass
class DecompositionResult:
    var_names: list[str]
    statistic: np.ndarray
    bins: pd.DataFrame
    states: list[int]


def decomposition(
    inputs: pd.DataFrame,
    output: pd.DataFrame,
    *,
    significance: np.ndarray,
    dec_limit: float = 1,
    states: list[int] | None = None,
    statistic: Literal["mean", "median"] | None = "mean",
) -> DecompositionResult:
    """SimDec decomposition.

    Parameters
    ----------
    inputs : DataFrame of shape (n_runs, n_factors)
        Input variables.
    output : DataFrame of shape (n_runs, 1)
        Target variable.
    significance : ndarray of shape (n_factors, 1)
        Significance index, combined effect of each input.
    dec_limit : float
        Explained variance ratio to filter the number input variables.
    states : list of int, optional
        List of possible states for the considered parameter.
    statistic : {"mean", "median"}, optional
        Statistic to compute in each bin.

    Returns
    -------
    res : DecompositionResult
        An object with attributes:

        var_names : list of string (n_factors, 1)
            Variable names.
        statistic : ndarray of shape (n_factors, 1)
            Statistic in each bin.
        bins : DataFrame
            Multidimensional bins.
        states : list of int
            List of possible states for the considered parameter.

    """
    var_names = inputs.columns
    inputs = inputs.to_numpy()
    output = output.to_numpy()

    # 1. variables for decomposition
    var_order = np.argsort(significance)[::-1]

    # only keep the explained variance corresponding to `dec_limit`
    significance = significance[var_order]
    n_var_dec = np.where(np.cumsum(significance) < dec_limit)[0].size
    n_var_dec = max(1, n_var_dec)  # keep at least one variable
    n_var_dec = min(5, n_var_dec)  # use at most 5 variables

    var_names = var_names[var_order[:n_var_dec]].tolist()
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

    statistic_methods = {
        "mean": np.mean,
        "median": np.median,
    }
    try:
        statistic_method = statistic_methods[statistic]
    except IndexError:
        msg = f"'statistic' must be one of {statistic_methods.values()}"
        raise ValueError(msg)

    def statistic_(inputs):
        """Custom function to keep track of the content of bins."""
        bins.append(inputs)
        return statistic_method(inputs)

    res = stats.binned_statistic_dd(
        inputs, values=output, statistic=statistic_, bins=states
    )

    bins = pd.DataFrame(bins[1:]).T

    return DecompositionResult(var_names, res.statistic, bins, states)
