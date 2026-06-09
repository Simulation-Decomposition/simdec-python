import pathlib

import numpy as np
import numpy.testing as npt
import pandas as pd

import simdec as sd


path_data = pathlib.Path(__file__).parent / "data"


def test_decomposition():
    fname = path_data / "stress.csv"
    data = pd.read_csv(fname)
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]
    si = np.array([0.04, 0.50, 0.11, 0.28])
    res = sd.decomposition(
        inputs=inputs, output=output, sensitivity_indices=si, dec_limit=1
    )

    assert res.var_names == ["sigma_res", "R", "Rp0.2", "Kf"]
    assert res.states == [2, 2, 2, 2]
    assert res.statistic.shape == (2, 2, 2, 2)
    npt.assert_allclose(res.bins.describe().T["mean"], res.statistic.flatten())


def test_auto_ordering_single_dominant_variable():
    fname = path_data / "stress.csv"
    data = pd.read_csv(fname)
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    si = np.array([0.90, 0.05, 0.03, 0.02])
    res = sd.decomposition(inputs=inputs, output=output, sensitivity_indices=si)
    assert len(res.var_names) == 1


def test_auto_ordering_two_variables_cross_threshold():
    fname = path_data / "stress.csv"
    data = pd.read_csv(fname)
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    # sum = 1.0, cumsum = [0.75, 0.81, ...] -> crosses 0.8 after 2nd variable
    si = np.array([0.75, 0.06, 0.10, 0.09])
    res = sd.decomposition(inputs=inputs, output=output, sensitivity_indices=si)
    assert len(res.var_names) == 2


def test_auto_ordering_cap_at_four():
    """Even if more than 4 variables are needed to reach 0.8, cap at 4."""
    fname = path_data / "stress.csv"
    data = pd.read_csv(fname)
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    # sum = 1.0, each variable contributes equally -> need all 4 to reach 0.8
    si = np.array([0.25, 0.25, 0.25, 0.25])
    res = sd.decomposition(inputs=inputs, output=output, sensitivity_indices=si)
    assert len(res.var_names) == 4


def test_auto_ordering_si_not_summing_to_one():
    """Threshold is relative to sum(si), not hardcoded 1.0."""
    fname = path_data / "stress.csv"
    data = pd.read_csv(fname)
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    # sum = 2.0, 0.8 * 2.0 = 1.6, cumsum = [1.8, ...] -> crosses after 1st variable
    si = np.array([1.80, 0.10, 0.05, 0.05])
    res = sd.decomposition(inputs=inputs, output=output, sensitivity_indices=si)
    assert len(res.var_names) == 1
