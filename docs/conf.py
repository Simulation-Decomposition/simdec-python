import importlib.metadata
import os

project = "SimDec"
copyright = "2023, SimDec Developers"
author = "Pamphile Roy"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "numpydoc",
    "myst_nb",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- autosummary -------------------------------------------------------------

autosummary_generate = True

# -- Notebook tutorials with MyST-NB ------------------------------------------

nb_execution_mode = "auto"

# -- Version matching --------------------------------------------------------

json_url = (
    "https://simdec.readthedocs.io/en/latest/_static/version_switcher.json"  # noqa
)
# Define the version we use for matching in the version switcher.
version_match = os.environ.get("READTHEDOCS_VERSION")
# If READTHEDOCS_VERSION doesn't exist, we're not on RTD
# If it is an integer, we're in a PR build and the version isn't correct.
if not version_match or version_match.isdigit():
    # For local development, infer the version to match from the package.
    release = importlib.metadata.version("simdec")
    if "dev" in release or "rc" in release:
        version_match = "latest"
        json_url = "_static/version_switcher.json"
    else:
        version_match = release

# -- Options for HTML output -------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

html_logo = "_static/logo.gif"
html_favicon = "_static/favicon.png"

html_theme_options = {
    "pygment_light_style": "github-light-colorblind",
    "pygment_dark_style": "pitaya-smoothie",
    "external_links": [
        {"name": "Official website", "url": "https://simdec.fi"},
    ],
    "icon_links": [
        {
            "name": "Discord",
            "url": "https://discord.gg/54SFcNsZS4",
            "icon": "fa-brands fa-discord",
        },
        {
            "name": "GitHub",
            "url": "https://github.com/Simulation-Decomposition/simdec-python",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/simdec",
            "icon": "fa-brands fa-python",
        },
    ],
    "navbar_center": ["version-switcher", "navbar-nav"],
    "switcher": {
        "json_url": json_url,
        "version_match": version_match,
    },
}
