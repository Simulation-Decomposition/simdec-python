from pathlib import Path
from typing_extensions import Annotated

import matplotlib.pyplot as plt
import pandas as pd
import panel as pn
import typer

import simdec as sd

app = typer.Typer()


@app.command()
def main(
    data: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ]
):
    data = pd.read_csv(data)
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    res = sd.significance(inputs=inputs, output=output)
    si = res.si

    res = sd.decomposition(inputs=inputs, output=output, significance=si)

    fig, ax = plt.subplots()
    palette = sd.palette(states=res.states)
    ax, palette = sd.visualization(
        bins=res.bins, palette=palette, states=res.states, ax=ax
    )

    # use a notebook to see the styling
    table, styler = sd.tableau(
        statistic=res.statistic,
        var_names=res.var_names,
        states=res.states,
        bins=res.bins,
        palette=palette,
    )

    # panel app
    pn.extension(template="material")
    pn_fig = pn.pane.Matplotlib(fig, dpi=144)
    pn_table = pn.pane.DataFrame(styler)
    pn_app = pn.Column(pn_fig, pn_table)
    pn_app.save("app.html")
