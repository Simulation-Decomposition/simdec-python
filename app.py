import io

import matplotlib.pyplot as plt
import pandas as pd
import panel as pn

import simdec as sd


# panel app
pn.extension(template="material")

text_fname = pn.widgets.FileInput()
slider_dec_limit = pn.widgets.FloatSlider(
    value=0.5, step=0.05, name="Decomposition limit"
)


@pn.cache
def load_data(text_fname):
    if text_fname is None:
        return

    data = pd.read_csv(io.BytesIO(text_fname), sep=",", decimal=".")
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    si = sd.significance(inputs=inputs, output=output).si

    return si, inputs, output


def decomposition(dec_limit, data):
    if data is None:
        return
    si, inputs, output = data
    return sd.decomposition(
        inputs=inputs, output=output, significance=si, dec_limit=dec_limit
    )


def palette(res):
    if res is None:
        return
    return sd.palette(res.states)


def figure(res, palette):
    if res is None:
        return
    fig, ax = plt.subplots()
    _ = sd.visualization(bins=res.bins, palette=palette, states=res.states, ax=ax)
    return fig


def tableau(res, palette):
    if res is None:
        return
    # use a notebook to see the styling
    _, styler = sd.tableau(
        statistic=res.statistic,
        var_names=res.var_names,
        states=res.states,
        bins=res.bins,
        palette=palette,
    )
    return styler


interactive_data = pn.bind(load_data, text_fname)
interactive_decomposition = pn.bind(decomposition, slider_dec_limit, interactive_data)
interactive_palette = pn.bind(palette, interactive_decomposition)
interactive_figure = pn.bind(figure, interactive_decomposition, interactive_palette)
interactive_tableau = pn.bind(tableau, interactive_decomposition, interactive_palette)

pn_params = pn.WidgetBox("# Parameters", slider_dec_limit, text_fname)
pn_app = pn.Column(
    pn_params, pn.Row(interactive_figure, interactive_tableau)
).servable()
