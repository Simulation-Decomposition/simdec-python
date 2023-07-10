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
    res = sd.decomposition(inputs=inputs, output=output, significance=si)

    assert res.var_names == ["sigma_res", "R", "Rp0.2", "Kf"]
    assert res.states == [2, 2, 2, 2]
    assert res.statistic.shape == (2, 2, 2, 2)
    npt.assert_allclose(res.bins.describe().T["mean"], res.statistic.flatten())
