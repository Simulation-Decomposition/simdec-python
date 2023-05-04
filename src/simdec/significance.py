from typing import Literal

import numpy as np
from scipy import stats


__all__ = ["significance"]


def number_of_bins(n_runs: int, n_factors: int) -> tuple[int, int]:
    """Optimal number of bins for first & second-order significance indices.

    Linear approximation of experimental results from (Marzban & Lahmer, 2016).
    """
    n_bins_foe = 36 - 2.7 * n_factors + (0.0017 - 0.00008 * n_factors) * n_runs
    n_bins_foe = np.ceil(n_bins_foe)
    if n_bins_foe <= 30:
        n_bins_foe = 10  # setting a limit to fit the experimental results

    while (n_runs % n_bins_foe) != 0:
        n_bins_foe = n_bins_foe + 1

    n_bins_soe = max(4, np.round(np.sqrt(n_bins_foe)))

    return n_bins_foe, n_bins_soe


def _weighted_var(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    avg = np.average(x, weights=weights)
    variance = np.average((x - avg) ** 2, weights=weights)
    return np.sqrt(variance)


def significance(
    inputs: np.ndarray, output: np.ndarray, method: Literal["simdec"]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Significance indices.

    The significance express how much variability of the output is
    explained by the inputs.

    Parameters
    ----------
    inputs : ndarray of shape (n_runs, n_factors)
        Input variables.
    output : ndarray of shape (n_runs, 1)
        Target variable.
    method : {'simdec'}
        Formulation used to compute significance indices.

    Returns
    -------
    si : ndarray of shape (n_factors, 1)
        Significance index, combined effect of each input.
    foe : ndarray of shape (n_factors, 1)
        First-order effects (also called 'main' or 'individual').
    soe : ndarray of shape (n_factors, 1)
        Second-order effects (also called 'interaction').

    """
    ...
    n_runs, n_factors = inputs.shape
    n_bins_foe, n_bins_soe = number_of_bins(n_runs, n_factors)

    # Overall variance of the output
    var_y = np.var(output)

    si = np.empty(n_factors)
    foe = np.empty(n_factors)
    soe = np.empty((n_factors, n_factors))

    # first order
    for i in range(n_factors):
        xi = inputs[:, i]

        bin_avg, _, bin_count = stats.binned_statistic(
            x=xi, values=output, bins=n_bins_foe
        )

        # weighted variance and divide by the overall variance of the output
        foe[i] = _weighted_var(bin_avg, weights=bin_count)

        # second order
        for j in range(n_factors):
            if i == j and j < i:
                continue

            xj = inputs[:, i]
            bin_avg, *_, bin_counts = stats.binned_statistic_2d(
                x=xi, y=xj, values=output, bins=n_bins_soe, expand_binnumbers=True
            )

            var_ij = ...  # _weighted_var(bin_avg, weights=bin_counts)
            var_i = _weighted_var(bin_avg, weights=bin_counts[0])
            var_j = _weighted_var(bin_avg, weights=bin_counts[1])

            soe[i, j] = (var_ij - var_i - var_j) / var_y

    return si, foe, soe
