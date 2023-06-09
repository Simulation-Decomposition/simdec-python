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

    n_bins_soe = max(4, np.round(np.sqrt(n_bins_foe)))

    return n_bins_foe, n_bins_soe


def _weighted_var(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    avg = np.average(x, weights=weights)
    variance = np.average((x - avg) ** 2, weights=weights)
    return variance


def significance(
    inputs: np.ndarray, output: np.ndarray, *, method: Literal["simdec"] = "simdec"
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
    n_runs, n_factors = inputs.shape
    n_bins_foe, n_bins_soe = number_of_bins(n_runs, n_factors)

    # Overall variance of the output
    var_y = np.var(output)

    si = np.empty(n_factors)
    foe = np.empty(n_factors)
    soe = np.zeros((n_factors, n_factors))

    for i in range(n_factors):
        # first order
        xi = inputs[:, i]

        bin_avg, _, binnumber = stats.binned_statistic(
            x=xi, values=output, bins=n_bins_foe
        )
        # can have NaN in the average but no corresponding binnumber
        bin_avg = bin_avg[~np.isnan(bin_avg)]
        bin_counts = np.unique(binnumber, return_counts=True)[1]

        # weighted variance and divide by the overall variance of the output
        foe[i] = _weighted_var(bin_avg, weights=bin_counts) / var_y

        # second order
        for j in range(n_factors):
            if i == j or j < i:
                continue

            xj = inputs[:, j]

            bin_avg, *edges, binnumber = stats.binned_statistic_2d(
                x=xi, y=xj, values=output, bins=n_bins_soe, expand_binnumbers=False
            )

            mean_ij = bin_avg[~np.isnan(bin_avg)]
            bin_counts = np.unique(binnumber, return_counts=True)[1]
            var_ij = _weighted_var(mean_ij, weights=bin_counts)

            # expand_binnumbers here
            nbin = np.array([len(edges_) + 1 for edges_ in edges])
            binnumbers = np.asarray(np.unravel_index(binnumber, nbin))

            bin_counts_i = np.unique(binnumbers[0], return_counts=True)[1]
            bin_counts_j = np.unique(binnumbers[1], return_counts=True)[1]

            # handle NaNs
            mean_i = np.nanmean(bin_avg, axis=1)
            mean_i = mean_i[~np.isnan(mean_i)]
            mean_j = np.nanmean(bin_avg, axis=0)
            mean_j = mean_j[~np.isnan(mean_j)]

            var_i = _weighted_var(mean_i, weights=bin_counts_i)
            var_j = _weighted_var(mean_j, weights=bin_counts_j)

            soe[i, j] = (var_ij - var_i - var_j) / var_y

        soe = np.clip(soe, a_min=0, a_max=None)
        soe = np.where(soe == 0, soe.T, soe)
        si[i] = foe[i] + soe[:, i].sum() / 2

    return si, foe, soe
