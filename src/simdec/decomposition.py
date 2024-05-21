from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats


__all__ = ["decomposition", "states_expansion"]


def states_expansion(states: list[int], inputs: pd.DataFrame) -> list[list[str]]:
    """Expand states list to fully represent all scenarios."""
    inputs = pd.DataFrame(inputs)
    expanded_states = []
    for state in states:
        if isinstance(state, int):
            if state == 2:
                expanded_states.append(["low", "high"])
            elif state == 3:
                expanded_states.append(["low", "medium", "high"])
        else:
            expanded_states.append(state)

    # categorical for a given variable
    cat_cols = inputs.select_dtypes(exclude=["number"])
    cat_cols_idx = []
    states_cats_ = []
    for cat_col in cat_cols:
        _, cats = pd.factorize(inputs[cat_col])
        cat_cols_idx.append(inputs.columns.get_loc(cat_col))
        states_cats_.append(cats)

    for i, states_cat_ in zip(cat_cols_idx, states_cats_):
        n_unique = np.unique(inputs.iloc[:, i]).size
        expanded_states[i] = list(states_cat_) if n_unique < 5 else expanded_states[i]

    return expanded_states


@dataclass
class DecompositionResult:
    var_names: list[str]
    statistic: np.ndarray
    bins: pd.DataFrame
    states: list[int]
    bin_edges: np.ndarray

    def __reduce__(self):
        h = blake2b(key=b"result hashing", digest_size=20)

        h.update(str(self.var_names).encode())
        h.update(str(self.statistic).encode())
        h.update(str(self.bins).encode())
        h.update(str(self.states).encode())
        h.update(str(self.bin_edges).encode())

        return [h.hexdigest()]


def decomposition(
    inputs: pd.DataFrame,
    output: pd.DataFrame,
    *,
    sensitivity_indices: np.ndarray,
    dec_limit: float = 1,
    auto_ordering: bool = True,
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
    sensitivity_indices : ndarray of shape (n_factors, 1)
        Sensitivity indices, combined effect of each input.
    dec_limit : float
        Explained variance ratio to filter the number input variables.
    auto_ordering : bool
        Automatically order input columns based on the relative sensitivity_indices
        or use the provided order.
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

    cat_cols = inputs.select_dtypes(exclude=["number"])
    for cat_col in cat_cols:
        codes, cat_states_ = pd.factorize(inputs[cat_col])
        inputs[cat_col] = codes

    inputs = inputs.to_numpy()
    output = output.to_numpy()

    # 1. variables for decomposition
    var_order = np.argsort(sensitivity_indices)[::-1]

    # only keep the explained variance corresponding to `dec_limit`
    sensitivity_indices = sensitivity_indices[var_order]

    if auto_ordering:
        n_var_dec = np.where(np.cumsum(sensitivity_indices) < dec_limit)[0].size
        n_var_dec = max(1, n_var_dec)  # keep at least one variable
        n_var_dec = min(5, n_var_dec)  # use at most 5 variables
    else:
        n_var_dec = inputs.shape[1]

    # 2. states formation
    if states is None:
        states = 3 if n_var_dec < 3 else 2
        states = [states] * n_var_dec

        for i in range(n_var_dec):
            n_unique = np.unique(inputs[:, i]).size
            states[i] = n_unique if n_unique <= 5 else states[i]

    if auto_ordering:
        var_names = var_names[var_order[:n_var_dec]].tolist()
        inputs = inputs[:, var_order[:n_var_dec]]

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

    # make bins with equal number of samples for a given dimension
    # sort and then split in n-state
    sorted_inputs = np.sort(inputs, axis=0)
    bin_edges = []
    for i, states_ in enumerate(states):
        splits = np.array_split(sorted_inputs[:, i], states_)
        bin_edges_ = [splits_[0] for splits_ in splits]
        bin_edges_.append(splits[-1][-1])  # last point to close the edges
        # bin_edges_ = np.unique(bin_edges_)  # remove duplicate points, sorted
        bin_edges_ += 1e-10 * np.linspace(0, 1, len(bin_edges_))
        bin_edges.append(bin_edges_)

    res = stats.binned_statistic_dd(
        inputs, values=output, statistic=statistic_, bins=bin_edges
    )

    bins = pd.DataFrame(bins[1:]).T

    if len(bins.columns) != np.prod(states):
        # mismatch with the number of states vs bins
        # when it happens, we have NaNs in the statistic
        # we can add empty columns with NaNs on these positions as bins
        # then are not present for these states
        nan_idx = np.argwhere(np.isnan(res.statistic).flatten()).flatten()

        for idx in nan_idx:
            bins = np.insert(bins, idx, np.nan, axis=1)

        bins = pd.DataFrame(bins)

    return DecompositionResult(
        var_names=var_names,
        statistic=res.statistic,
        bins=bins,
        states=states,
        bin_edges=res.bin_edges,
    )
