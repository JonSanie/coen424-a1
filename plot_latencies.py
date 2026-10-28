import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.cbook import boxplot_stats


INPUT_FILE = Path(__file__).with_name("latencies.csv")
OUTPUT_FILE = Path(__file__).with_name("boxplot.png")
QUERY_LABELS = ["Query 1", "Query 2", "Query 3"]
LATENCY_COLUMNS = ["query_1_ms", "query_2_ms", "query_3_ms"]


def read_latencies() -> list[list[float]]:
    with INPUT_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if len(rows) != 100:
        raise ValueError(f"Expected 100 latency rows, found {len(rows)}.")

    return [
        [float(row[column]) for row in rows]
        for column in LATENCY_COLUMNS
    ]


def annotate_box_plot(axis: plt.Axes, values: list[list[float]]) -> None:
    for position, query_values in enumerate(values, start=1):
        quartiles = axis.boxplot(
            query_values,
            positions=[position],
            widths=0.35,
            patch_artist=True,
            boxprops={"facecolor": "lightsteelblue"},
            medianprops={"color": "darkred", "linewidth": 2},
            whiskerprops={"color": "black"},
            capprops={"color": "black"},
            flierprops={"marker": "o", "markersize": 4},
        )

        statistics = boxplot_stats(query_values)[0]
        lower_whisker = statistics["whislo"]
        upper_whisker = statistics["whishi"]
        first_quartile = statistics["q1"]
        third_quartile = statistics["q3"]
        median = statistics["med"]

        labels = [
            ("Upper whisker", upper_whisker),
            ("Q3", third_quartile),
            ("Median", median),
            ("Q1", first_quartile),
            ("Lower whisker", lower_whisker),
        ]
        offset = (axis.get_ylim()[1] - axis.get_ylim()[0]) * 0.015
        for label, value in labels:
            axis.annotate(
                f"{label}: {value:.2f} ms",
                xy=(position, value),
                xytext=(position + 0.12, value + offset),
                fontsize=8,
                arrowprops={"arrowstyle": "-", "color": "gray"},
            )


def main() -> None:
    values = read_latencies()
    figure, axis = plt.subplots(figsize=(12, 8))
    annotate_box_plot(axis, values)
    axis.set_xticks(range(1, len(QUERY_LABELS) + 1), QUERY_LABELS)
    axis.set_ylabel("End-to-end delay (ms)")
    axis.set_title("End-to-End gRPC Query Latencies")
    axis.grid(axis="y", linestyle="--", alpha=0.5)
    figure.tight_layout()
    figure.savefig(OUTPUT_FILE, dpi=300)
    plt.close(figure)
    print(f"Saved box plot to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
