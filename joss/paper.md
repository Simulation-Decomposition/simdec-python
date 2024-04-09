---
title: 'Simulation Decomposition in Python'
tags:
  - Python
  - SimDec
  - statistics
  - Sensitivity Analysis
  - Visualization
authors:
  - name: Pamphile T. Roy
    affiliation: 1
    corresponding: true
    orcid: 0000-0001-9816-1416
  - name: Mariia Kozlova
    affiliation: 2
    orcid: 0000-0002-6952-7682
affiliations:
    - name: Consulting Manao GmbH, Vienna, Austria
      index: 1
    - name: LUT Business School, LUT University, Lappeenranta, Finland
      index: 2
date: 1 April 2024
bibliography: paper.bib

---

# Summary

Uncertainties are everywhere! Whether you are developing a new AI system,
running complex simulations or making an experiment in a lab, uncertainties
influence the system. And you need a way to understand how these impact your
results.

SimDec offers a novel visual way to understand the intricate role that
uncertainties play. Thanks to a clear API and our dashboard, we are making
uncertainty analysis accessible to everyone.

# Statement of need

From real life experiments to numerical simulations, uncertainties play a
crucial role in the system under study. With the avenment of Artificial
Intelligence and new regulations such as the AI Act or the
*Better Regulation Guideline*, there is a growing need for explainability and
impact assessments of systems under uncertainties.

Traditional methods to analyse the uncertainties focus on quantitative methods
to compare the importance of factors, there is a large body of literature and
the field is known as: Sensitivity Analysis (SA). The indices of Sobol' are a
prominent example of such methods.

Simulation Decomposition is a hybrid uncertainty-sensitivity analysis approach
that reveals the critical behavior of a computational model or an empirical
dataset. It decomposes the distribution of the output (target variable) by the
multivariable scenarios, formed out of the most influential input variables.
The resulting visualization shows how different output ranges can be achieved
and what kind of critical interactions affect the output. The method has shown
value for various computational models from different fields,
including business, environment, and engineering, as well as an emerging
evidence of use for empirical data and AI.

Besides proposing a comprehensive yet simple API through a Python packages
available on PyPi, SimDec is also made available
to practitioners through an online dashboard at https://simdec.io. The
innovative methods of SimDec, the project relies on powerful methods
from SALib [@Herman2017] and SciPy [@virtanen2020scipy, @Roy2023]-notably the QMC
capabilities with `sp.stats.qmc` and sensitivity indices with
`sp.stats.sensitivity_indices`. The dashboard is made possible thanks to Panel.

# Acknowledgements

The authors thank ...

# References
