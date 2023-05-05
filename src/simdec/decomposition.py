from typing import Literal

import numpy as np


__all__ = ["decomposition"]


def decomposition(
    inputs: np.ndarray,
    output: np.ndarray,
    significance: np.ndarray,
    dec_limit: float,
    threshold_type: Literal["percentile", "median"] = "median",
) -> tuple[np.ndarray, ...]:
    ...
