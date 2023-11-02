import ast
import io

import matplotlib.pyplot as plt
import pandas as pd
import panel as pn
import seaborn as sns
import scipy as sp


# panel app
pn.extension("floatpanel")

pn.config.sizing_mode = "stretch_width"
pn.config.throttled = True
font_size = "12pt"
blue_color = "#4099da"

template = pn.template.FastGridTemplate(
    title="Data generation (sampling)",
    # logo="_static/logo.gif",
    favicon="_static/favicon.png",
    meta_description="Data generation (sampling)",
    meta_keywords=(
        "Random Sampling, Monte Carlo, Quasi-Monte Carlo, " "Sobol', Halton, LHS"
    ),
    accent=blue_color,
    shadow=False,
    main_layout=None,
    theme_toggle=False,
    corner_radius=3,
)


@pn.cache
def figure(sample):
    plt.close("all")
    grid = sns.pairplot(sample, corner=True)
    return grid.figure


def csv_data(sample: pd.DataFrame) -> io.StringIO:
    sio = io.StringIO()
    sample.to_csv(sio, index=False)
    sio.seek(0)
    return sio


dim = pn.widgets.IntInput(
    name="Number of variables",
    start=1,
    end=10,
    value=2,
    step=1,
)


variables_details = pn.Card(title="Variables details")


def create_variable(dim):
    variables_ = []
    for i in range(dim):
        variable_name = pn.widgets.TextInput(name="Variable name", placeholder="X")
        distribution = pn.widgets.Select(
            name="Distribution",
            options={
                "Uniform": sp.stats.uniform,
                "Normal": sp.stats.norm,
                "Beta": sp.stats.beta,
            },
        )
        parameters = pn.widgets.TextInput(name="Parameters", placeholder="")
        bounds = pn.widgets.EditableRangeSlider(
            name="Bounds", start=0, end=1, value=(0.0, 1.0), step=0.1
        )

        variable = pn.Card(
            variable_name,
            distribution,
            parameters,
            bounds,
            title=f"X{i+1}",
        )
        variables_.append(variable)

    variables_details[:] = variables_


dummy_create_variable_bind = pn.bind(create_variable, dim)


n_samples = pn.widgets.IntInput(
    name="Number of samples",
    start=10,
    end=2**20,
    value=1024,
    step=50,
)


sampling_engine = pn.widgets.Select(
    name="Sampling method",
    options={
        "Sobol'": sp.stats.qmc.Sobol,
        "Halton": sp.stats.qmc.Halton,
        "Latin Hypercube": sp.stats.qmc.LatinHypercube,
    },
)


interactive_sample = sampling_engine.rx()(d=dim).random(n_samples)


def sample_to_distributions(sample, variables_details):
    for i, variable_details in enumerate(variables_details):
        dist = variable_details[1].value
        dist_name = dist.name
        params = variable_details[2].value
        if params != "":
            params = ast.literal_eval(params)
            dist = dist(**params)

        sample_ = dist.ppf(sample[:, i]).reshape(-1, 1)

        if dist_name != "uniform":
            sample_ = sp.stats.qmc.scale(
                sample_, l_bounds=min(sample_), u_bounds=max(sample_), reverse=True
            )

        bounds = variable_details[3].value
        sample_ = sp.stats.qmc.scale(sample_, l_bounds=bounds[0], u_bounds=bounds[1])

        sample[:, i] = sample_.flatten()

    return sample


def sample_to_dataframe(sample, variables_details):
    columns = []
    for i, variable_details in enumerate(variables_details):
        x_name = variable_details[0].value
        columns.append(x_name if x_name != "" else f"X{i+1}")

    df = pd.DataFrame(data=sample, columns=columns)
    return df


interactive_sample_dist = pn.bind(
    sample_to_distributions,
    sample=interactive_sample,
    variables_details=variables_details,
)

interactive_dataframe = pn.bind(
    sample_to_dataframe,
    sample=interactive_sample_dist,
    variables_details=variables_details,
)

interactive_figure = pn.bind(figure, interactive_dataframe)

indicator_discrepancy = pn.indicators.Number(
    name="Discrepancy:",
    value=pn.bind(sp.stats.qmc.discrepancy, interactive_sample.rx()),
    title_size=font_size,
    font_size=font_size,
)


# App layout

# Sidebar
sidebar_area = pn.layout.WidgetBox(
    pn.pane.Markdown("## Variables", styles={"color": blue_color}),
    dim,
    pn.Spacer(height=10),
    variables_details,
    dummy_create_variable_bind,
    pn.Spacer(height=10),
    pn.pane.Markdown("## Sampling", styles={"color": blue_color}),
    n_samples,
    sampling_engine,
    pn.pane.Markdown("## Metrics", styles={"color": blue_color}),
    indicator_discrepancy,
    sizing_mode="stretch_width",
)

template.sidebar.append(sidebar_area)

# Main window
template.main[0:4, 0:6] = pn.panel(interactive_figure, loading_indicator=True)


################################################################################################################

# Header
icon_size = "1.5em"

download_file_button = pn.widgets.FileDownload(
    callback=pn.bind(
        csv_data,
        interactive_dataframe,
    ),
    icon="file-download",
    icon_size=icon_size,
    button_type="success",
    filename="samples.csv",
    width=200,
    label="Download",
    align="center",
)

info_button = pn.widgets.Button(
    icon="info-circle",
    icon_size=icon_size,
    button_type="light",
    name="About",
    width=150,
    align="center",
)
info_button.js_on_click(code="""window.open('https://www.simdec.fi/')""")

issue_button = pn.widgets.Button(
    icon="message-report",
    icon_size=icon_size,
    button_type="light",
    name="Feedback",
    width=150,
    align="center",
)
issue_button.js_on_click(
    code="""window.open('https://github.com/Simulation-Decomposition/simdec-python/issues')"""
)

logout_button = pn.widgets.Button(name="Log out", width=100)
logout_button.js_on_click(code="""window.location.href = './logout'""")

docs_button = pn.widgets.Button(
    icon="notes",
    icon_size=icon_size,
    button_type="light",
    name="Docs",
    width=150,
    align="center",
)
docs = pn.Column(height=0, width=0)


def callback_docs(event):
    docs[:] = [
        pn.layout.FloatPanel(
            "This is some documentation",
            name="SimDec documentation",
            theme="info",
            contained=False,
            position="center",
        )
    ]


docs_button.on_click(callback_docs)


header_area = pn.Row(
    pn.HSpacer(),
    download_file_button,
    docs,
    docs_button,
    info_button,
    issue_button,
    # logout_button,
)

template.header.append(header_area)

# serve the template
template.servable()
