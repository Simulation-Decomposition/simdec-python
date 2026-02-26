import numpy as np
import pandas as pd
from scipy.stats import qmc, uniform, lognorm
import simdec as sd


def test_decomposition_default():
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
    indices = sd.sensitivity_indices(inputs=inputs, output=output)
    si = indices.si
    res = sd.decomposition(inputs=inputs, output=output, sensitivity_indices=si)

    assert len(res.var_names) == 2
    assert res.var_names == ["deposit_0", "interest_rate"]
