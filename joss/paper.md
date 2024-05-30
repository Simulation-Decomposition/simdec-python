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

Uncertainties are everywhere. Whether you are developing a new Artificial Intelligence (AI) system,
running complex simulations or making an experiment in a lab, uncertainties
influence the system. Therefore, an approach is needed to understand how these uncertainties impact the system's performance.

SimDec offers a novel visual way to understand the intricate role that
uncertainties play. A clear Python Application Programming Interface (API) and a no-code interactive web
dashboard make uncertainty analysis with SimDec accessible to everyone.

# Statement of need

From real life experiments to numerical simulations, uncertainties play a
crucial role in the system under study. With the advent of AI
and new regulations such as the [AI Act](https://artificialintelligenceact.eu) or the
*Better Regulation Guideline* [@europeancommission2021], there is a growing need for explainability and
impact assessments of systems under uncertainties.

Traditional methods to analyse the uncertainties focus on quantitative methods
to compare the importance of factors, there is a large body of literature and
the field is known as: Sensitivity Analysis (SA) [@Saltelli2007]. The indices of Sobol' are a
prominent example of such methods [@sobol1993].

Simulation Decomposition or SimDec moves the field of SA forward by supplementing the computation of sensitivity indices with the visualization of the type of interactions involved, which proves critical for understanding the system's behavior and decision-making [@Kozlova2024].
In short, SimDec is a hybrid uncertainty-sensitivity analysis approach
that reveals the critical behavior of a computational model or an empirical
dataset. It decomposes the distribution of the output
(target variable) by automatically forming scenarios that reveal the most critical behavior of the system. The scenarios are formed out of the most influential input variables (defined with variance-based sensitivity indices) by breaking down their numeric ranges into states (e.g. _low_ and _high_) and creating an exhaustive list of their combinations (e.g. (i) _low_ _**A**_ & _low_ _**B**_, (ii) _low_ _**A**_ & _high_ _**B**_, (iii) _high_ **_A_** & _low_ **_B_**, and (iv) _high_ **_A_** and _high_ **_B_**). The resulting visualization shows how different
output ranges can be achieved and what kind of critical interactions affect
the output—as seen in \autoref{fig:simdec}. The method has shown value for
various computational models from different fields, including business,
environment, and engineering, as well as an emerging evidence of use for
empirical data and AI.

![SimDec: explanation of output by most important inputs. A simulation dataset of a structural reliability model with one key output variable and four input variables is used for this case. Inputs 3 and 1 have the highest sensitivity indices and thus are automatically chosen for decomposition. The most influential input 3 divides the distribution of the output into three main states with distinct colors. Input 1 further subdivides them into shades. From the graph, it becomes obvious that input 1 influences the output when input 3 is low, but has a negligible effect when input 3 is medium or high.\label{fig:simdec}](simdec_presentation.png)

Besides proposing a comprehensive yet simple API through a Python package
available on PyPi, SimDec is also made available
to practitioners through an online dashboard at [https://simdec.io](https://simdec.io). The project
relies on powerful variance-based sensitivity analysis methods from SALib [@Herman2017] and
SciPy [@Virtanen2020; @Roy2023]&mdash;notably the Quasi-Monte Carlo capabilities with
`sp.stats.qmc` and in the future sensitivity indices with `sp.stats.sensitivity_indices`.
The dashboard is made possible thanks to Panel [@panel].

# Acknowledgements

The work on this open-source software was supported by grant #220177 from
Finnish Foundation for Economic Foundation.

# References
