import html
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path("outputs/major_revision")
DATA = ROOT / "figure_data"
INDEPENDENT = ROOT / "figures_independent"
GROUPED = ROOT / "figures_grouped"
WIDTH = 1800
HEIGHT = 1200
COLORS = ["#176B87", "#C35A21", "#3B7A57", "#6B4C9A"]


def esc(value):
    return html.escape(str(value))


def svg_start(width=WIDTH, height=HEIGHT):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        "<style>"
        "text{font-family:Georgia,'Times New Roman',serif;fill:#18252B}"
        ".axis{stroke:#18252B;stroke-width:3}"
        ".grid{stroke:#D9E2E7;stroke-width:2}"
        ".tick{font-size:30px}.label{font-size:36px}.legend{font-size:30px}"
        "</style>",
    ]


def axes(parts, y_min, y_max, y_label, categories, x=180, y=90, w=1500, h=920):
    parts.append(f'<line class="axis" x1="{x}" y1="{y}" x2="{x}" y2="{y+h}"/>')
    parts.append(
        f'<line class="axis" x1="{x}" y1="{y+h}" x2="{x+w}" y2="{y+h}"/>'
    )
    for index in range(6):
        value = y_min + (y_max - y_min) * index / 5
        py = y + h - h * index / 5
        parts.append(
            f'<line class="grid" x1="{x}" y1="{py}" x2="{x+w}" y2="{py}"/>'
        )
        parts.append(
            f'<text class="tick" x="{x-22}" y="{py+10}" text-anchor="end">'
            f"{value:.3f}</text>"
        )
    for index, category in enumerate(categories):
        px = x + w * (index + 0.5) / len(categories)
        parts.append(
            f'<text class="tick" x="{px}" y="{y+h+55}" text-anchor="middle">'
            f"{esc(category)}</text>"
        )
    parts.append(
        f'<text class="label" transform="translate(48 {y+h/2}) rotate(-90)" '
        f'text-anchor="middle">{esc(y_label)}</text>'
    )
    return lambda value: y + h - (value - y_min) / (y_max - y_min) * h


def grouped_bars(frame, category, series, value, error, ylabel, path, y_min=0):
    categories = list(frame[category].drop_duplicates())
    series_values = list(frame[series].drop_duplicates())
    y_max = max(
        1e-9,
        max(
            frame[value]
            + (frame[error] if error and error in frame else 0)
        )
        * 1.12,
    )
    parts = svg_start()
    scale = axes(parts, y_min, y_max, ylabel, categories)
    plot_x, plot_y, plot_w, plot_h = 180, 90, 1500, 920
    group_w = plot_w / len(categories)
    bar_w = group_w * 0.68 / len(series_values)
    for series_index, series_name in enumerate(series_values):
        for category_index, category_name in enumerate(categories):
            row = frame[
                (frame[category] == category_name)
                & (frame[series] == series_name)
            ].iloc[0]
            center = (
                plot_x
                + group_w * (category_index + 0.5)
                + (series_index - (len(series_values) - 1) / 2) * bar_w
            )
            top = scale(row[value])
            baseline = scale(y_min)
            parts.append(
                f'<rect x="{center-bar_w*0.44}" y="{top}" '
                f'width="{bar_w*0.88}" height="{baseline-top}" '
                f'fill="{COLORS[series_index]}"/>'
            )
            if error and error in row:
                low = scale(row[value] - row[error])
                high = scale(row[value] + row[error])
                parts.extend(
                    [
                        f'<line class="axis" x1="{center}" y1="{low}" x2="{center}" y2="{high}"/>',
                        f'<line class="axis" x1="{center-12}" y1="{low}" x2="{center+12}" y2="{low}"/>',
                        f'<line class="axis" x1="{center-12}" y1="{high}" x2="{center+12}" y2="{high}"/>',
                    ]
                )
        legend_x = 250 + series_index * 330
        parts.append(
            f'<rect x="{legend_x}" y="1120" width="35" height="24" '
            f'fill="{COLORS[series_index]}"/>'
        )
        parts.append(
            f'<text class="legend" x="{legend_x+48}" y="1142">'
            f"{esc(series_name)}</text>"
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def line_plot(frame, x_field, y_field, error_field, ylabel, path):
    frame = frame.sort_values(x_field)
    y_low = max(0, (frame[y_field] - frame[error_field]).min() * 0.995)
    y_high = (frame[y_field] + frame[error_field]).max() * 1.005
    categories = [str(value) for value in frame[x_field]]
    parts = svg_start()
    scale = axes(parts, y_low, y_high, ylabel, categories)
    plot_x, plot_w = 180, 1500
    points = []
    for index, row in frame.reset_index(drop=True).iterrows():
        px = plot_x + plot_w * (index + 0.5) / len(frame)
        py = scale(row[y_field])
        points.append((px, py))
        low = scale(row[y_field] - row[error_field])
        high = scale(row[y_field] + row[error_field])
        parts.extend(
            [
                f'<line class="axis" x1="{px}" y1="{low}" x2="{px}" y2="{high}"/>',
                f'<line class="axis" x1="{px-14}" y1="{low}" x2="{px+14}" y2="{low}"/>',
                f'<line class="axis" x1="{px-14}" y1="{high}" x2="{px+14}" y2="{high}"/>',
            ]
        )
    parts.append(
        '<polyline fill="none" stroke="#176B87" stroke-width="8" points="'
        + " ".join(f"{x},{y}" for x, y in points)
        + '"/>'
    )
    for px, py in points:
        parts.append(f'<circle cx="{px}" cy="{py}" r="13" fill="#176B87"/>')
    parts.append(
        '<text class="label" x="930" y="1135" text-anchor="middle">Clients</text>'
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def scatter_plot(frame, x_field, y_field, path):
    x_min, x_max = frame[x_field].min(), frame[x_field].max()
    y_min, y_max = frame[y_field].min(), frame[y_field].max()
    x_pad = max(0.01, (x_max - x_min) * 0.08)
    y_pad = max(0.001, (y_max - y_min) * 0.08)
    x_min, x_max = x_min - x_pad, x_max + x_pad
    y_min, y_max = y_min - y_pad, y_max + y_pad
    parts = svg_start()
    categories = [""] * 6
    scale_y = axes(parts, y_min, y_max, "Test accuracy", categories)
    plot_x, plot_y, plot_w, plot_h = 180, 90, 1500, 920
    for index in range(6):
        value = x_min + (x_max - x_min) * index / 5
        px = plot_x + plot_w * index / 5
        parts.append(
            f'<text class="tick" x="{px}" y="{plot_y+plot_h+55}" '
            f'text-anchor="middle">{value:.2f}</text>'
        )
    color_map = {
        name: COLORS[index]
        for index, name in enumerate(sorted(frame["partition"].unique()))
    }
    for _, row in frame.iterrows():
        px = plot_x + (row[x_field] - x_min) / (x_max - x_min) * plot_w
        py = scale_y(row[y_field])
        parts.append(
            f'<circle cx="{px}" cy="{py}" r="13" '
            f'fill="{color_map[row["partition"]]}" fill-opacity="0.8"/>'
        )
    rho, p_value = stats.spearmanr(frame[x_field], frame[y_field])
    parts.append(
        '<text class="label" x="930" y="1135" text-anchor="middle">'
        "Mean normalized label entropy</text>"
    )
    parts.append(
        f'<text class="legend" x="1250" y="145">Spearman rho={rho:.3f}; '
        f"p={p_value:.3g}</text>"
    )
    for index, (label, color) in enumerate(color_map.items()):
        x = 250 + index * 390
        parts.append(f'<circle cx="{x}" cy="1128" r="12" fill="{color}"/>')
        parts.append(
            f'<text class="legend" x="{x+25}" y="1138">{esc(label)}</text>'
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def verifier_plot(frame, path):
    classified = frame.copy()
    classified["outcome"] = np.where(
        classified["rejected"].astype(str).str.lower() == "true",
        "Rejected",
        "Accepted limitation",
    )
    summary = (
        classified.groupby("outcome", dropna=False)
        .size()
        .rename("count")
        .reset_index()
    )
    summary["series"] = "Security scenarios"
    grouped_bars(
        summary,
        "outcome",
        "series",
        "count",
        None,
        "Scenario count",
        path,
    )
    return summary


def main():
    for directory in (DATA, INDEPENDENT, GROUPED):
        directory.mkdir(parents=True, exist_ok=True)

    summary = pd.read_csv(
        ROOT / "expanded-analysis-466cb07" / "experiment_summary.csv"
    )
    core = pd.read_csv(
        ROOT / "core-statistics-a8fe359" / "summary_statistics.csv"
    )
    baseline = core[
        (core["metric"] == "accuracy") & core["method"].isin(["B0", "B3"])
    ].copy()
    baseline["dataset"] = baseline["scenario_id"].str.replace("_core", "")
    baseline["error"] = baseline["ci95_high"] - baseline["mean"]
    baseline[["dataset", "method", "mean", "error", "ci95_low", "ci95_high"]].to_csv(
        DATA / "baseline_comparison.csv", index=False
    )
    grouped_bars(
        baseline,
        "dataset",
        "method",
        "mean",
        "error",
        "Test accuracy",
        INDEPENDENT / "baseline_comparison.svg",
    )

    scaling = summary[
        (summary["suite"] == "scaling") & (summary["metric"] == "accuracy")
    ].copy()
    scaling["error"] = scaling["ci95_high"] - scaling["mean"]
    scaling.to_csv(DATA / "client_scaling.csv", index=False)
    line_plot(
        scaling,
        "client_count",
        "mean",
        "error",
        "Test accuracy",
        INDEPENDENT / "client_scaling.svg",
    )

    entropy_rows = []
    heterogeneity = ROOT / "heterogeneity-10seed-2d2b220"
    metrics = pd.read_csv(heterogeneity / "metrics" / "test_metrics.csv")
    for path in sorted((heterogeneity / "partitions").glob("**/entropy_summary.csv")):
        values = pd.read_csv(path).set_index("metric")["mean"]
        entropy_rows.append(
            {
                "seed": int(path.parts[-4].removeprefix("seed_")),
                "partition": path.parent.name,
                "mean_label_entropy": values["label_entropy"],
            }
        )
    entropy = metrics.merge(
        pd.DataFrame(entropy_rows), on=["seed", "partition"]
    )
    entropy.to_csv(DATA / "heterogeneity_entropy.csv", index=False)
    scatter_plot(
        entropy,
        "mean_label_entropy",
        "accuracy",
        INDEPENDENT / "heterogeneity_entropy.svg",
    )

    threshold_accuracy = summary[
        (summary["suite"] == "threshold") & (summary["metric"] == "accuracy")
    ][["policy_profile", "mean", "ci95_low", "ci95_high"]].copy()
    threshold_accuracy["error"] = (
        threshold_accuracy["ci95_high"] - threshold_accuracy["mean"]
    )
    threshold_accuracy["series"] = "Test accuracy"
    approval = pd.read_csv(
        ROOT / "expanded-analysis-466cb07" / "threshold_approval.csv"
    ).rename(columns={"mean": "approval_mean", "std": "approval_std"})
    threshold_data = threshold_accuracy.merge(approval, on="policy_profile")
    threshold_data.to_csv(DATA / "threshold_sensitivity.csv", index=False)
    grouped_bars(
        threshold_accuracy,
        "policy_profile",
        "series",
        "mean",
        "error",
        "Test accuracy",
        INDEPENDENT / "threshold_sensitivity.svg",
    )

    adversarial = summary[
        (summary["suite"] == "adversarial")
        & (summary["metric"] == "accuracy")
    ].copy()
    adversarial["error"] = adversarial["ci95_high"] - adversarial["mean"]
    adversarial.to_csv(DATA / "adversarial_accuracy.csv", index=False)
    grouped_bars(
        adversarial,
        "attack_type",
        "method",
        "mean",
        "error",
        "Test accuracy",
        INDEPENDENT / "adversarial_accuracy.svg",
    )

    attack_matrix = pd.read_csv(
        ROOT / "security-evidence" / "attack_matrix.csv"
    )
    verifier_data = attack_matrix[
        attack_matrix["scenario"].str.startswith(("A2", "A3", "A4", "A14"))
    ]
    verifier_summary = verifier_plot(
        verifier_data, INDEPENDENT / "verifier_security.svg"
    )
    verifier_summary.to_csv(DATA / "verifier_security.csv", index=False)

    pd.DataFrame(
        [
            {
                "status": "blocked",
                "blocker": "BLK-002",
                "measurement": "two-peer add pin cold warm concurrency recovery",
                "source": "BLOCKERS.md",
            }
        ]
    ).to_csv(DATA / "ipfs_measurement_status.csv", index=False)

    grouped = svg_start(1800, 1200)
    grouped.append(
        '<text class="label" x="900" y="580" text-anchor="middle">'
        "Panel-ready source figures are provided independently; "
        "IPFS panel omitted because BLK-002 prevents measurement.</text>"
    )
    grouped.append(
        '<text class="legend" x="900" y="640" text-anchor="middle">'
        "See figures_independent and figure_data.</text>"
    )
    grouped.append("</svg>")
    (GROUPED / "panel_manifest.svg").write_text(
        "\n".join(grouped), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
