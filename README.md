> **Warning**
> This library is under active development and things can change at anytime! Suggestions and help are greatly appreciated.



![image](https://user-images.githubusercontent.com/37065157/233836694-5312496e-4ada-47cb-bc09-3bf8c00be135.png)

<!---
When public
![image](https://raw.githubusercontent.com/Simulation-Decomposition/simdec-python/main/docs/_static/simdec_presentation.png)
-->

**Simulation decomposition** or **SimDec** is an uncertainty and sensitivity
analysis method, which is based on Monte Carlo simulation. SimDec consists of
three major parts:

1. computing sensitivity indices,
2. creating multi-variable scenarios and mapping the output values to them, and
3. visualizing the scenarios on the output distribution by color-coding its segments.

SimDec reveals the nature of causalities and interaction effects in the model.
See our [publications](https://www.simdec.fi/publications) and join our
[discord community](https://discord.gg/54SFcNsZS4).

## Python API
The library is distributed on PyPi and can be installed with:

    pip install simdec

## Dashboard
A live dashboard is available at:

https://simdec.io

## Citations

The algorithms and visualizations used in this package came primarily out of
research at LUT University, Lappeenranta, Finland, and Stanford University,
California, U.S., supported with grants from Business Finland, Wihuri
Foundation, and Finnish Foundation for Economic Education.

If you use SimDec in your research we would appreciate a citation to the
following publications:

- Kozlova, M., Moss, R. J., Yeomans, J. S., & Caers, J. (2024). Uncovering Heterogeneous Effects in Computational Models for Sustainable Decision-making. _Environmental Modelling & Software_, 171, 105898. [https://doi.org/10.1016/j.envsoft.2023.105898](https://doi.org/10.1016/j.envsoft.2023.105898)
- Kozlova, M., Moss, R. J., Roy, P., Alam, A., & Yeomans, J. S. (2024). SimDec algorithm and guidelines for its usage and interpretation. In M. Kozlova & J. S. Yeomans (Eds.), _Sensitivity Analysis for Business, Technology, and Policymaking. Made Easy with Simulation Decomposition_. Routledge. [Available here](https://github.com/Simulation-Decomposition/SimDec-book/blob/74ce72c1d3dda650eba1c59e3b215a4bb35c6be0/chapters/02_SimDec_algorithm_and_instructions/Ch2.pdf).
