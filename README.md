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

To install the development version, download the source and from the root of
the repository:

    pip install -e .[dev]

## Dashboard
A live dashboard is available at:

https://simdec.io

### Local use

The dashboard can be run locally using:

    make serve

### Deployment

The live version of the dashboard is hosted on GCP. To deploy a new version:

    PANEL_TOKEN=... make production

###

## Citations

The algorithms and visualizations used in this package came primarily out of
research at LUT University, Lappeenranta, Finland, and Stanford University,
California, U.S., supported with grants from Business Finland, Wihuri
Foundation, and Finnish Foundation for Economic Education.

If you use SimDec in your research we would appreciate a citation to the
following publications:

- Kozlova, M., & Yeomans, J. S. (2022). Monte Carlo Enhancement via Simulation
  Decomposition: A “Must-Have” Inclusion for Many Disciplines. _INFORMS
  Transactions on Education, 22_(3), 147-159. DOI:10.1287/ited.2019.0240.
- Kozlova, M., Moss, R. J., Yeomans, J. S., & Caers, J. (forthcoming).
  Uncovering Heterogeneous Effects in Computational Models for Sustainable
  Decision-making. _Environmental Modelling & Software_.
- Kozlova, M., Moss, R. J., Roy, P., Alam, A., & Yeomans, J. S. (forthcoming).
  SimDec algorithm. In M. Kozlova & J. S. Yeomans (Eds.), _Sensitivity Analysis
  for Business, Technology, and Policymaking Made Easy with Simulation
  Decomposition_. Routledge.
