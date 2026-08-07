from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("outputs/major_revision")
DATA = ROOT / "figure_data"
OUTPUT = ROOT / "figures_independent"
GROUPED = ROOT / "figures_grouped"
SIZE = (1800, 1200)
COLORS = ["#176B87", "#C35A21", "#3B7A57", "#6B4C9A"]
FONT = "/System/Library/Fonts/Supplemental/Georgia.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def canvas():
    image = Image.new("RGB", SIZE, "white")
    return image, ImageDraw.Draw(image)


def text(draw, xy, value, size=30, anchor="mm", bold=False):
    draw.text(xy, str(value), fill="#18252B", font=font(size, bold), anchor=anchor)


def base_axes(draw, y_min, y_max, categories, ylabel):
    x0, y0, width, height = 180, 90, 1500, 920
    draw.line((x0, y0, x0, y0 + height), fill="#18252B", width=3)
    draw.line(
        (x0, y0 + height, x0 + width, y0 + height),
        fill="#18252B",
        width=3,
    )
    for index in range(6):
        value = y_min + (y_max - y_min) * index / 5
        y = y0 + height - height * index / 5
        draw.line((x0, y, x0 + width, y), fill="#D9E2E7", width=2)
        text(draw, (x0 - 20, y), f"{value:.3f}", anchor="rm")
    for index, category in enumerate(categories):
        x = x0 + width * (index + 0.5) / len(categories)
        text(draw, (x, y0 + height + 48), category, anchor="ma")
    label = Image.new("RGBA", (600, 60), (255, 255, 255, 0))
    label_draw = ImageDraw.Draw(label)
    text(label_draw, (300, 30), ylabel, size=36)
    label = label.rotate(90, expand=True)
    draw._image.paste(label, (20, 360), label)
    return (
        x0,
        y0,
        width,
        height,
        lambda value: y0
        + height
        - (value - y_min) / (y_max - y_min) * height,
    )


def save(image, name):
    path = OUTPUT / name
    image.save(path, dpi=(300, 300))


def bars(frame, category, series, value, error, ylabel, filename):
    categories = list(frame[category].drop_duplicates())
    series_values = list(frame[series].drop_duplicates())
    y_max = (
        frame[value]
        + (frame[error] if error and error in frame else 0)
    ).max() * 1.12
    image, draw = canvas()
    x0, _, width, _, scale = base_axes(draw, 0, y_max, categories, ylabel)
    group_width = width / len(categories)
    bar_width = group_width * 0.68 / len(series_values)
    for s_index, series_name in enumerate(series_values):
        for c_index, category_name in enumerate(categories):
            row = frame[
                (frame[category] == category_name)
                & (frame[series] == series_name)
            ].iloc[0]
            center = (
                x0
                + group_width * (c_index + 0.5)
                + (s_index - (len(series_values) - 1) / 2) * bar_width
            )
            top, bottom = scale(row[value]), scale(0)
            draw.rectangle(
                (center - bar_width * 0.44, top, center + bar_width * 0.44, bottom),
                fill=COLORS[s_index],
            )
            if error:
                low = scale(row[value] - row[error])
                high = scale(row[value] + row[error])
                draw.line((center, low, center, high), fill="#18252B", width=3)
                draw.line((center - 12, low, center + 12, low), fill="#18252B", width=3)
                draw.line((center - 12, high, center + 12, high), fill="#18252B", width=3)
        legend_x = 250 + s_index * 360
        draw.rectangle((legend_x, 1112, legend_x + 35, 1136), fill=COLORS[s_index])
        text(draw, (legend_x + 48, 1124), series_name, anchor="lm")
    save(image, filename)


def line_plot(frame, filename):
    frame = frame.sort_values("client_count")
    low = (frame["mean"] - frame["error"]).min() * 0.995
    high = (frame["mean"] + frame["error"]).max() * 1.005
    image, draw = canvas()
    x0, _, width, _, scale = base_axes(
        draw, low, high, frame["client_count"].astype(int).astype(str), "Test accuracy"
    )
    points = []
    for index, row in frame.reset_index(drop=True).iterrows():
        x = x0 + width * (index + 0.5) / len(frame)
        y = scale(row["mean"])
        points.append((x, y))
        y_low, y_high = scale(row["mean"] - row["error"]), scale(
            row["mean"] + row["error"]
        )
        draw.line((x, y_low, x, y_high), fill="#18252B", width=3)
        draw.line((x - 12, y_low, x + 12, y_low), fill="#18252B", width=3)
        draw.line((x - 12, y_high, x + 12, y_high), fill="#18252B", width=3)
    draw.line(points, fill=COLORS[0], width=8, joint="curve")
    for point in points:
        draw.ellipse(
            (point[0] - 13, point[1] - 13, point[0] + 13, point[1] + 13),
            fill=COLORS[0],
        )
    text(draw, (930, 1135), "Clients", size=36)
    save(image, filename)


def scatter_plot(frame, filename):
    x_field, y_field = "mean_label_entropy", "accuracy"
    x_min, x_max = frame[x_field].min(), frame[x_field].max()
    y_min, y_max = frame[y_field].min(), frame[y_field].max()
    x_pad, y_pad = (x_max - x_min) * 0.08, (y_max - y_min) * 0.08
    x_min, x_max = x_min - x_pad, x_max + x_pad
    y_min, y_max = y_min - y_pad, y_max + y_pad
    image, draw = canvas()
    x0, y0, width, height, scale_y = base_axes(
        draw, y_min, y_max, [""] * 6, "Test accuracy"
    )
    for index in range(6):
        value = x_min + (x_max - x_min) * index / 5
        x = x0 + width * index / 5
        text(draw, (x, y0 + height + 48), f"{value:.2f}", anchor="ma")
    color_map = {
        name: COLORS[index]
        for index, name in enumerate(sorted(frame["partition"].unique()))
    }
    for _, row in frame.iterrows():
        x = x0 + (row[x_field] - x_min) / (x_max - x_min) * width
        y = scale_y(row[y_field])
        draw.ellipse((x - 13, y - 13, x + 13, y + 13), fill=color_map[row["partition"]])
    text(draw, (930, 1105), "Mean normalized label entropy", size=36)
    for index, (name, color) in enumerate(color_map.items()):
        x = 240 + index * 430
        draw.ellipse((x - 11, 1150, x + 11, 1172), fill=color)
        text(draw, (x + 25, 1161), name, anchor="lm")
    save(image, filename)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    GROUPED.mkdir(parents=True, exist_ok=True)
    baseline = pd.read_csv(DATA / "baseline_comparison.csv")
    bars(baseline, "dataset", "method", "mean", "error", "Test accuracy", "baseline_comparison.png")
    scaling = pd.read_csv(DATA / "client_scaling.csv")
    line_plot(scaling, "client_scaling.png")
    scatter_plot(pd.read_csv(DATA / "heterogeneity_entropy.csv"), "heterogeneity_entropy.png")
    threshold = pd.read_csv(DATA / "threshold_sensitivity.csv")
    bars(threshold, "policy_profile", "series", "mean", "error", "Test accuracy", "threshold_sensitivity.png")
    adversarial = pd.read_csv(DATA / "adversarial_accuracy.csv")
    bars(adversarial, "attack_type", "method", "mean", "error", "Test accuracy", "adversarial_accuracy.png")
    verifier = pd.read_csv(DATA / "verifier_security.csv")
    bars(verifier, "outcome", "series", "count", None, "Scenario count", "verifier_security.png")
    ipfs = pd.read_csv(DATA / "ipfs_overhead.csv")
    bars(ipfs, "payload", "operation", "mean_ms", "error_ms", "Latency (ms; p95 upper bars)", "ipfs_overhead.png")

    names = [
        "baseline_comparison.png",
        "client_scaling.png",
        "heterogeneity_entropy.png",
        "threshold_sensitivity.png",
        "adversarial_accuracy.png",
        "verifier_security.png",
        "ipfs_overhead.png",
    ]
    panel = Image.new("RGB", (3200, 1500), "white")
    panel_draw = ImageDraw.Draw(panel)
    for index, name in enumerate(names):
        image = Image.open(OUTPUT / name)
        image.thumbnail((780, 700))
        x = (index % 4) * 800 + 10
        y = (index // 4) * 730 + 65
        panel.paste(image, (x, y))
        text(panel_draw, (x + 20, y - 35), chr(65 + index), size=44, anchor="lm", bold=True)
    panel.save(GROUPED / "measured_results_panels.png", dpi=(300, 300))


if __name__ == "__main__":
    main()
