from dataclasses import dataclass
import warnings

import numpy as np
import pandas as pd
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


@dataclass
class SignificanceResult:
    si: np.ndarray
    first_order: np.ndarray
    second_order: np.ndarray


def significance(
    inputs: pd.DataFrame | np.ndarray, output: pd.DataFrame | np.ndarray
) -> SignificanceResult:
    """Significance indices.

    The significance express how much variability of the output is
    explained by the inputs.

    Parameters
    ----------
    inputs : ndarray or DataFrame of shape (n_runs, n_factors)
        Input variables.
    output : ndarray or DataFrame of shape (n_runs, 1)
        Target variable.

    Returns
    -------
    res : SignificanceResult
        An object with attributes:

        si : ndarray of shape (n_factors, 1)
            Significance index, combined effect of each input.
        foe : ndarray of shape (n_factors, 1)
            First-order effects (also called 'main' or 'individual').
        soe : ndarray of shape (n_factors, 1)
            Second-order effects (also called 'interaction').

    Examples
    --------
    >>> import numpy as np
    >>> from scipy.stats import qmc
    >>> import simdec as sd

    We define first the function that we want to analyse. We use the
    well studied Ishigami function:

    >>> def f_ishigami(x):
    ...     return (np.sin(x[0]) + 7 * np.sin(x[1]) ** 2
    ...             + 0.1 * (x[2] ** 4) * np.sin(x[0]))

    Then we generate inputs using the Quasi-Monte Carlo method of Sobol' in
    order to cover uniformly our space. And we compute outputs of the function.

    >>> rng = np.random.default_rng()
    >>> inputs = qmc.Sobol(d=3, seed=rng).random(2**18)
    >>> inputs = qmc.scale(
    ...     sample=inputs,
    ...     l_bounds=[-np.pi, -np.pi, -np.pi],
    ...     u_bounds=[np.pi, np.pi, np.pi]
    ... )
    >>> output = f_ishigami(inputs.T)

    We can now pass our inputs and outputs to the `significance` function:

    >>> res = sd.significance(inputs=inputs, output=output)
    >>> res.si
    array([0.43157591, 0.44241433, 0.11767249])

    """
    cat_columns = inputs.select_dtypes(["category", "O"]).columns
    inputs[cat_columns] = inputs[cat_columns].apply(
        lambda x: x.astype("category").cat.codes
    )

    if isinstance(inputs, pd.DataFrame):
        inputs = inputs.to_numpy()
    if isinstance(output, pd.DataFrame):
        output = output.to_numpy()

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
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
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

    return SignificanceResult(si, foe, soe)
