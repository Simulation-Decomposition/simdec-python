import numpy as np
import pytest
from scipy.stats import qmc

from simdec import significance


def f_ishigami(x):
    f_eval = np.sin(x[0]) + 7 * np.sin(x[1]) ** 2 + 0.1 * (x[2] ** 4) * np.sin(x[0])
    return f_eval


@pytest.fixture(scope="session")
def ishigami_ref_indices():
    """Reference values for Ishigami from Saltelli2007.

    Chapter 4, exercise 5 pages 179-182.

    S1 = [0.31390519, 0.44241114, 0.        ]
    S2 = [[0.        , 0.        , 0.24368366],
          [0.        , 0.        , 0.        ],
          [0.24368366, 0.        , 0.        ]]
    St = [0.55758886, 0.44241114, 0.24368366]
    """
    a = 7.0
    b = 0.1

    var = 0.5 + a**2 / 8 + b * np.pi**4 / 5 + b**2 * np.pi**8 / 18
    v1 = 0.5 + b * np.pi**4 / 5 + b**2 * np.pi**8 / 50
    v2 = a**2 / 8
    v3 = 0
    v12 = 0
    # v13: mistake in the book, see other derivations e.g. in 10.1002/nme.4856
    v13 = b**2 * np.pi**8 * 8 / 225
    v23 = 0

    s_first = np.array([v1, v2, v3]) / var
    s_second = np.array([[0.0, 0.0, v13], [v12, 0.0, v23], [v13, v23, 0.0]]) / var
    s_total = s_first + s_second.sum(axis=1)

    return s_first, s_second, s_total


def test_significance():
    rng = np.random.default_rng(1655943881803900660874135192647741156)
    n_dim = 3

    inputs = qmc.Sobol(d=n_dim, seed=rng).random(1024)
    inputs = qmc.scale(
        sample=inputs, l_bounds=[-np.pi, -np.pi, -np.pi], u_bounds=[np.pi, np.pi, np.pi]
    )
    output = f_ishigami(inputs.T)

    si, foe, soe = significance(inputs=inputs, output=output)

    assert si.shape == (3,)
    assert foe.shape == (3,)
    assert soe.shape == (3, 3)
