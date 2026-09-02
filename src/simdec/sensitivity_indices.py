from dataclasses import dataclass
import warnings

import numpy as np
import pandas as pd
from scipy import stats

__all__ = ["sensitivity_indices"]

try:
    from IPython.display import display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False


def _quantile_edges(x: np.ndarray, n_bins: int) -> np.ndarray:
    """Bin edges holding approximately the same number of points.

    Bins are defined by value, so identical values always fall in the same
    bin. Duplicated edges are dropped: a factor with many ties gets fewer
    than ``n_bins`` bins, and a constant factor gets a single one.

    Discrete variables (few unique values relative to n_bins) get one bin
    per unique value instead of quantile-based edges, to avoid collapsing
    minority categories into a majority bin.
    """
    unique_vals = np.unique(x[~np.isnan(x)])
    if len(unique_vals) <= n_bins:
        # midpoints between consecutive unique values, so each value gets
        # its own bin
        if unique_vals.size == 1:
            return np.array([unique_vals[0], np.nextafter(unique_vals[0], np.inf)])
        midpoints = (unique_vals[:-1] + unique_vals[1:]) / 2
        return np.concatenate([[unique_vals[0]], midpoints, [unique_vals[-1]]])

    edges = np.unique(np.nanquantile(x, np.linspace(0, 1, n_bins + 1)))
    if edges.size < 2:
        edges = np.array([edges[0], np.nextafter(edges[0], np.inf)])
    return edges


def _conditional_var(sample: np.ndarray, y: np.ndarray, edges: list) -> float:
    """Var(E[Y | bins]), each bin weighted by its number of points."""
    mean, *_ = stats.binned_statistic_dd(sample, y, statistic="mean", bins=edges)
    count, *_ = stats.binned_statistic_dd(sample, y, statistic="count", bins=edges)
    valid = count > 0
    return _weighted_var(mean[valid], weights=count[valid])


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
    inputs: pd.DataFrame | np.ndarray,
    output: pd.DataFrame | np.ndarray,
    print_indices: bool = False,
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
    print_indices : bool, default False
        If True, displays computed indices.

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
        var_names = inputs.columns.tolist()
        cat_cols = inputs.select_dtypes(include=["category", "O", "string"]).columns
        if not cat_cols.empty:
            inputs = inputs.copy()  # Avoid SettingWithCopyWarning
            inputs[cat_cols] = inputs[cat_cols].apply(
                lambda x: x.astype("category").cat.codes
            )
        inputs = inputs.to_numpy()
    else:
        inputs = np.asarray(inputs)
        # Fallback names if it's just a numpy array
        var_names = [f"x{i}" for i in range(inputs.shape[1])]

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

    edges_foe = [
        _quantile_edges(inputs[:, k], int(n_bins_foe)) for k in range(n_factors)
    ]
    edges_soe = [
        _quantile_edges(inputs[:, k], int(n_bins_soe)) for k in range(n_factors)
    ]

    # Marginal Var(E[Y|Xk]) on the SOE binning, identical for every pair
    var_marginal = np.array(
        [
            _conditional_var(inputs[:, [k]], output, [edges_soe[k]])
            for k in range(n_factors)
        ]
    )

    for i in range(n_factors):
        # 1. First-order effects (FOE)
        foe[i] = _conditional_var(inputs[:, [i]], output, [edges_foe[i]]) / var_y

        for j in range(n_factors):
            if j <= i:
                continue

            var_ij = _conditional_var(
                inputs[:, [i, j]], output, [edges_soe[i], edges_soe[j]]
            )
            soe[i, j] = (var_ij - var_marginal[i] - var_marginal[j]) / var_y

    # Mirror SOE and calculate Combined Effect (SI)
    # SI is FOE + half of all interactions associated with that variable
    soe = soe + soe.T
    for k in range(n_factors):
        si[k] = foe[k] + (soe[:, k].sum() / 2)

    if print_indices:
        if not HAS_IPYTHON:
            warnings.warn(
                "print_indices=True requires ipython to be installed. "
                "Install it with: pip install simdec[display]. Table skipped.",
                stacklevel=2,
            )
        else:
            df_foe = pd.DataFrame(foe, index=var_names, columns=["First-order effect"])
            df_soe = pd.DataFrame(soe, index=var_names, columns=var_names)
            df_si = pd.DataFrame(si, index=var_names, columns=["Combined effect"])

            df_indices = pd.concat([df_foe, df_soe, df_si], axis=1)
            display(df_indices)

    return SensitivityAnalysisResult(si, foe, soe)
