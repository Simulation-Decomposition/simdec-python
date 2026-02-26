from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


__all__ = ["sensitivity_indices"]


def number_of_bins(n_runs: int, n_factors: int) -> tuple[int, int]:
    """Optimal number of bins for first & second-order sensitivity_indices indices.

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
class SensitivityAnalysisResult:
    si: np.ndarray
    first_order: np.ndarray
    second_order: np.ndarray


def sensitivity_indices(
    inputs: pd.DataFrame | np.ndarray, output: pd.DataFrame | np.ndarray
) -> SensitivityAnalysisResult:
    """Sensitivity indices.

    The sensitivity_indices express how much variability of the output is
    explained by the inputs.

    Parameters
    ----------
    inputs : ndarray or DataFrame of shape (n_runs, n_factors)
        Input variables.
    output : ndarray or DataFrame of shape (n_runs, 1)
        Target variable.

    Returns
    -------
    res : SensitivityAnalysisResult
        An object with attributes:

        si : ndarray of shape (n_factors, 1)
            Sensitivity indices, combined effect of each input.
        foe : ndarray of shape (n_factors, 1)
            First-order effects (also called 'main' or 'individual').
        soe : ndarray of shape (n_factors, n_factors)
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

    We can now pass our inputs and outputs to the `sensitivity_indices` function:

    >>> res = sd.sensitivity_indices(inputs=inputs, output=output)
    >>> res.si
    array([0.43157591, 0.44241433, 0.11767249])

    """
    # Handle inputs conversion
    if isinstance(inputs, pd.DataFrame):
        cat_columns = inputs.select_dtypes(["category", "O"]).columns
        inputs[cat_columns] = inputs[cat_columns].apply(
            lambda x: x.astype("category").cat.codes
        )
        inputs = inputs.to_numpy()

    # Handle output conversion first, then flatten
    if isinstance(output, (pd.DataFrame, pd.Series)):
        output = output.to_numpy()

    # Flatten output if it's (N, 1)
    output = output.flatten()

    n_runs, n_factors = inputs.shape
    n_bins_foe, n_bins_soe = number_of_bins(n_runs, n_factors)

    # Overall variance of the output
    var_y = np.var(output)

    si = np.empty(n_factors)
    foe = np.empty(n_factors)
    soe = np.zeros((n_factors, n_factors))

    for i in range(n_factors):
        # 1. First-order effects (FOE)
        xi = inputs[:, i]

        bin_avg, _, binnumber = stats.binned_statistic(
            x=xi, values=output, bins=n_bins_foe, statistic="mean"
        )

        # Filter empty bins and get weights (counts)
        mask_foe = ~np.isnan(bin_avg)
        mean_i_foe = bin_avg[mask_foe]
        # binnumber starts at 1; 0 is for values outside range
        bin_counts_foe = np.unique(binnumber[binnumber > 0], return_counts=True)[1]

        foe[i] = _weighted_var(mean_i_foe, weights=bin_counts_foe) / var_y

        # 2. Second-order effects (SOE)
        for j in range(n_factors):
            if j <= i:
                continue

            xj = inputs[:, j]

            # 2D Binned Statistic for Var(E[Y|Xi, Xj])
            bin_avg_ij, x_edges, y_edges, binnumber_ij = stats.binned_statistic_2d(
                x=xi, y=xj, values=output, bins=n_bins_soe, expand_binnumbers=False
            )

            mask_ij = ~np.isnan(bin_avg_ij)
            mean_ij = bin_avg_ij[mask_ij]
            counts_ij = np.unique(binnumber_ij[binnumber_ij > 0], return_counts=True)[1]
            var_ij = _weighted_var(mean_ij, weights=counts_ij)

            # Marginal Var(E[Y|Xi]) using n_bins_soe to match MATLAB logic
            bin_avg_i_soe, _, binnumber_i_soe = stats.binned_statistic(
                x=xi, values=output, bins=n_bins_soe, statistic="mean"
            )
            mask_i = ~np.isnan(bin_avg_i_soe)
            counts_i = np.unique(
                binnumber_i_soe[binnumber_i_soe > 0], return_counts=True
            )[1]
            var_i_soe = _weighted_var(bin_avg_i_soe[mask_i], weights=counts_i)

            # Marginal Var(E[Y|Xj]) using n_bins_soe to match MATLAB logic
            bin_avg_j_soe, _, binnumber_j_soe = stats.binned_statistic(
                x=xj, values=output, bins=n_bins_soe, statistic="mean"
            )
            mask_j = ~np.isnan(bin_avg_j_soe)
            counts_j = np.unique(
                binnumber_j_soe[binnumber_j_soe > 0], return_counts=True
            )[1]
            var_j_soe = _weighted_var(bin_avg_j_soe[mask_j], weights=counts_j)

            soe[i, j] = (var_ij - var_i_soe - var_j_soe) / var_y

    # Mirror SOE and calculate Combined Effect (SI)
    # SI is FOE + half of all interactions associated with that variable
    soe = soe + soe.T
    for k in range(n_factors):
        si[k] = foe[k] + (soe[:, k].sum() / 2)

    return SensitivityAnalysisResult(si, foe, soe)
