from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

from analysis_2018c import DATA_FILE, STATES, read_xlsx_xml


OUT = Path("outputs/figures")
OUT.mkdir(parents=True, exist_ok=True)


def setup_style():
    candidates = ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140
    plt.rcParams["savefig.bbox"] = "tight"
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def load_data():
    seseds, _ = read_xlsx_xml(DATA_FILE)
    data = {}
    for r in seseds[1:]:
        data[(r["B"], int(float(r["C"])), r["A"])] = float(r["D"])
    return data


def load_csv(name):
    with open(Path("outputs") / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fig_renewable_share_trend(data):
    years = list(range(1960, 2010))
    colors = {"AZ": "#4C78A8", "CA": "#F58518", "NM": "#54A24B", "TX": "#B279A2"}
    plt.figure(figsize=(8.3, 4.5))
    for st in STATES:
        vals = []
        for y in years:
            vals.append(100 * data[(st, y, "RETCB")] / data[(st, y, "TETCB")])
        plt.plot(years, vals, label=st, linewidth=2.1, color=colors[st])
    plt.title("1960-2009 年可再生能源消费占比演变")
    plt.xlabel("年份")
    plt.ylabel("可再生能源消费占比（%）")
    plt.grid(axis="y", alpha=0.25)
    plt.legend(ncol=4, frameon=False, loc="upper right")
    plt.tight_layout()
    plt.savefig(OUT / "renewable_share_trend.pdf")
    plt.close()


def fig_score_2009(profiles):
    rows = sorted(profiles, key=lambda r: float(r["Clean profile score"]), reverse=True)
    states = [r["State"] for r in rows]
    scores = [float(r["Clean profile score"]) for r in rows]
    colors = ["#4C78A8", "#72B7B2", "#F58518", "#E45756"]
    plt.figure(figsize=(7.2, 4.2))
    bars = plt.bar(states, scores, color=colors, width=0.62)
    for b, s in zip(bars, scores):
        plt.text(b.get_x() + b.get_width() / 2, s + 0.025, f"{s:.3f}", ha="center", fontsize=10)
    plt.ylim(0, 1.12)
    plt.title("2009 年清洁可再生能源画像综合得分")
    plt.xlabel("州")
    plt.ylabel("综合得分")
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(OUT / "score_2009.pdf")
    plt.close()


def fig_renewable_components(data):
    comps = [
        ("BMTCB", "生物质"),
        ("HYTCB", "水电"),
        ("GETCB", "地热"),
        ("SOTCB", "太阳能"),
        ("WYTCB", "风能"),
    ]
    colors = ["#59A14F", "#4E79A7", "#B07AA1", "#F2CF5B", "#76B7B2"]
    bottoms = [0] * len(STATES)
    plt.figure(figsize=(8.0, 4.8))
    for (code, label), color in zip(comps, colors):
        vals = [data[(st, 2009, code)] / 1000 for st in STATES]
        plt.bar(STATES, vals, bottom=bottoms, label=label, color=color)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    plt.title("2009 年主要可再生能源构成")
    plt.xlabel("州")
    plt.ylabel("能源量（万亿 Btu）")
    plt.legend(ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(OUT / "renewable_components_2009.pdf")
    plt.close()


def fig_baseline_target(forecasts):
    targets = {
        2025: {"AZ": 10.0, "CA": 15.0, "NM": 15.0, "TX": 10.5},
        2050: {"AZ": 25.0, "CA": 35.0, "NM": 30.0, "TX": 30.0},
    }
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.2), sharey=True)
    width = 0.35
    for ax, year in zip(axes, [2025, 2050]):
        rows = [r for r in forecasts if int(r["Year"]) == year]
        rows = sorted(rows, key=lambda r: STATES.index(r["State"]))
        baseline = [100 * float(r["Renewable consumption share"]) for r in rows]
        target = [targets[year][r["State"]] for r in rows]
        x = range(len(rows))
        ax.bar([i - width / 2 for i in x], baseline, width=width, label="无政策基线", color="#BAB0AC")
        ax.bar([i + width / 2 for i in x], target, width=width, label="协定目标", color="#4C78A8")
        ax.set_title(f"{year} 年")
        ax.set_xticks(list(x), [r["State"] for r in rows])
        ax.grid(axis="y", alpha=0.25)
        ax.set_xlabel("州")
    axes[0].set_ylabel("可再生能源消费占比（%）")
    axes[1].legend(frameon=False, loc="upper left")
    fig.suptitle("无政策基线与协定目标对比")
    plt.tight_layout()
    plt.savefig(OUT / "baseline_target_compare.pdf")
    plt.close()


def fig_method_compare():
    labels = ["指标覆盖", "模型复杂度", "预测稳健性", "政策可解释性", "展示友好度"]
    ours = [3.0, 2.5, 3.2, 4.5, 4.0]
    cafe = [4.5, 4.5, 4.0, 3.5, 3.5]
    x = range(len(labels))
    width = 0.34
    plt.figure(figsize=(8.5, 4.6))
    plt.bar([i - width / 2 for i in x], ours, width=width, label="本文方案", color="#4C78A8")
    plt.bar([i + width / 2 for i in x], cafe, width=width, label="公开优秀论文 CAFE 思路", color="#F58518")
    plt.xticks(list(x), labels)
    plt.ylim(0, 5)
    plt.ylabel("相对评价（1-5）")
    plt.title("本文方案与公开优秀论文 CAFE 思路的侧重点对比")
    plt.legend(frameon=False)
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(OUT / "method_compare_cafe.pdf")
    plt.close()


def main():
    setup_style()
    data = load_data()
    profiles = load_csv("state_profiles_2009.csv")
    forecasts = load_csv("baseline_forecasts_2025_2050.csv")
    fig_renewable_share_trend(data)
    fig_score_2009(profiles)
    fig_renewable_components(data)
    fig_baseline_target(forecasts)
    fig_method_compare()
    print("saved figures to", OUT)


if __name__ == "__main__":
    main()
