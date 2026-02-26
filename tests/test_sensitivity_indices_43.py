import numpy as np
import numpy.testing as npt
import pandas as pd
from scipy.stats import qmc, uniform, lognorm
import simdec as sd

# Testing fix for issue #43


def test_sensitivity_indices_43():
    m = 13
    sampler = qmc.Sobol(d=2, scramble=True, seed=42)
    sample = sampler.random_base2(m=m)

    # deposit_0: uniform(500, 1500)
    deposit_0 = uniform.ppf(sample[:, 0], loc=500, scale=1000)

    # interest_rate: lognormal
    sigma = 0.5
    mu = np.log(0.01) + sigma**2
    interest_rate = lognorm.ppf(sample[:, 1], s=sigma, scale=np.exp(mu))

    deposit_20 = deposit_0 * (1 + interest_rate) ** 20

    inputs = pd.DataFrame({"deposit_0": deposit_0, "interest_rate": interest_rate})
    output = pd.Series(deposit_20, name="deposit_20")

    res = sd.sensitivity_indices(inputs, output)

    # MATLAB Results
    expected_si = np.array([0.7101, 0.2739])
    expected_foe = np.array([0.7028, 0.2666])
    expected_soe_12 = 0.0146

    npt.assert_allclose(res.si, expected_si, atol=3e-2)
    npt.assert_allclose(res.first_order, expected_foe, atol=3e-2)
    npt.assert_allclose(res.second_order[0, 1], expected_soe_12, atol=1e-2)
