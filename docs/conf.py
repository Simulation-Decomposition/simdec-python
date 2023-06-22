# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "SimDec"
copyright = "2023, SimDec Developers"
author = "Pamphile Roy"
release = "1.0.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "numpydoc",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- autosummary -------------------------------------------------------------

autosummary_generate = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

html_logo = "_static/logo.gif"
html_favicon = "_static/favicon.png"

html_theme_options = {
    "pygment_light_style": "github-light-colorblind",
    "pygment_dark_style": "pitaya-smoothie",
    "github_url": "https://github.com/Simulation-Decomposition/simdec-python",
    # "switcher": {
    #     "json_url": "https://simdec.readthedocs.io/en/latest/_static/version_switcher.json",  # noqa
    #     "version_match": release,
    # },
}
