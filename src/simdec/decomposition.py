from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from typing import Literal


__all__ = ["decomposition"]


def decomposition(
    inputs: np.ndarray,
    output: np.ndarray,
    significance: np.ndarray,
    dec_limit: float,
    threshold_type: Literal["percentile", "median"] = "median",
) -> tuple[np.ndarray, ...]:
    ...
