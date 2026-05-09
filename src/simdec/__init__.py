"""SimDec main namespace."""
from simdec.decomposition import *
from simdec.sensitivity_indices import *
from simdec.visualization import *
from simdec.heterogeneity_indices import *

__all__ = [
    "sensitivity_indices",
    "states_expansion",
    "decomposition",
    "visualization",
    "two_output_visualization",
    "tableau",
    "palette",
    "heterogeneity_indices",
]
