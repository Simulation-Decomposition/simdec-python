import matplotlib.pyplot as plt
import pandas as pd
import simdec as sd


def main():
    data = pd.read_csv("../../tests/data/stress.csv", sep=";", decimal=",")
    output_name, *v_names = list(data.columns)
    inputs, output = data[v_names], data[output_name]

    res = sd.significance(inputs=inputs, output=output)
    si = res.si

    res = sd.decomposition(inputs=inputs, output=output, significance=si)

    ax, palette = sd.visualization(bins=res.bins, states=res.states)
    plt.show()

    # use a notebook to see the styling
    table, styler = sd.tableau(bins=res.bins, palette=palette)
    print(table)


if __name__ == "__main__":
    main()
