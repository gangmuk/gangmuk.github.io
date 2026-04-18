#!/usr/bin/env python3
"""
Create bar charts comparing two benchmark experiment results.

Default behavior compares:
- tp4-pp3-3x_g5_12xlarge-ratelimited-20260315_154331-success/results.json
- tp4-pp3-3x_g5_12xlarge-sendall-20260315_170511-success/results.json

Usage examples:
    python plot_comparison_bars.py
    python plot_comparison_bars.py --output comparison_bars.png
    python plot_comparison_bars.py --exp-a path/to/a/results.json --exp-b path/to/b/results.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def set_publication_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Inter", "Helvetica Neue", "Arial", "sans-serif"],
            "font.size": 28,
            "font.weight": "normal",
            "axes.titlesize": 32,
            "axes.titleweight": "600",
            "axes.labelsize": 28,
            "axes.labelweight": "500",
            "xtick.labelsize": 26,
            "ytick.labelsize": 26,
            "legend.fontsize": 24,
            "figure.titlesize": 38,
            "figure.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": True,
            "axes.spines.bottom": True,
            "axes.linewidth": 1.2,
            "axes.edgecolor": "#E0E0E0",
            "grid.linewidth": 0.6,
            "grid.alpha": 0.4,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.1,
            "savefig.facecolor": "white",
        }
    )


def load_result(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        if not data:
            raise ValueError(f"Empty list in {path}")
        return data[0]
    if isinstance(data, dict):
        return data
    raise ValueError(f"Unsupported JSON structure in {path}")


def human_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.2f}h"


def annotate_bars(ax: plt.Axes, bars, formatter, fontsize: int = 26):
    ymax = ax.get_ylim()[1]
    offset = ymax * 0.025
    for b in bars:
        h = b.get_height()
        ax.text(
            b.get_x() + b.get_width() / 2.0,
            h + offset,
            formatter(h),
            ha="center",
            va="bottom",
            fontsize=fontsize,
            fontweight="600",
            color="#2C3E50",
        )


def build_plot(a: dict, b: dict, label_a: str, label_b: str, output_path: Path):
    set_publication_style()
    labels = [label_a.upper(), label_b.upper()]

    throughput_vals = [a["total_tokens_per_sec"], b["total_tokens_per_sec"]]
    
    # Use pre-calculated cost per 1M tokens
    cost_per_1m_vals = [a["cost_per_1m_tokens_total_usd"], b["cost_per_1m_tokens_total_usd"]]
    
    preemption_vals = [a["num_preemptions"], b["num_preemptions"]]
    
    # Use e2e_ms_mean if available, otherwise fall back to e2e_ms_p50
    e2e_avg_a = a.get("e2e_ms_mean", a["e2e_ms_p50"]) / 1000.0
    e2e_avg_b = b.get("e2e_ms_mean", b["e2e_ms_p50"]) / 1000.0
    e2e_avg_vals = [e2e_avg_a, e2e_avg_b]

    x = np.arange(len(labels), dtype=float)
    width = 0.55
    
    # Modern, sophisticated color palette
    colors = ["#4A90E2", "#E85D75"]  # sky blue / coral red
    bar_edge_color = "#FFFFFF"
    
    fig = plt.figure(figsize=(28, 8))
    fig.patch.set_facecolor("#FAFAFA")
    
    # Create grid with 1x4 layout (single row)
    gs = fig.add_gridspec(1, 4, hspace=0.35, wspace=0.32, 
                          left=0.05, right=0.97, top=0.88, bottom=0.18)
    
    axes = [fig.add_subplot(gs[0, j]) for j in range(4)]

    def draw_metric(ax: plt.Axes, values, title: str, ylabel: str, fmt, lower_is_better: bool):
        # Set clean background
        ax.set_facecolor("#FFFFFF")
        
        bars = ax.bar(
            x,
            values,
            width=width,
            color=colors,
            edgecolor=bar_edge_color,
            linewidth=2.5,
            zorder=3,
            alpha=0.9,
        )
        
        # Add subtle gradient effect with overlays
        for i, bar in enumerate(bars):
            bar_height = bar.get_height()
            bar_x = bar.get_x()
            bar_width = bar.get_width()
            # Add highlight effect
            highlight = plt.Rectangle(
                (bar_x, bar_height * 0.85),
                bar_width,
                bar_height * 0.15,
                facecolor=colors[i],
                edgecolor="none",
                alpha=0.3,
                zorder=4,
            )
            ax.add_patch(highlight)
        
        ax.set_title(f"{title}", pad=18, fontweight="600", color="#2C3E50")
        ax.set_ylabel(ylabel, fontweight="500", color="#546E7A")
        ax.set_xticks(x, labels, fontweight="600", color="#34495E")
        
        # Professional grid
        ax.grid(axis="y", alpha=0.25, linestyle="-", linewidth=0.8, color="#BDBDBD", zorder=0)
        ax.set_axisbelow(True)
        
        # Style spines
        for spine in ax.spines.values():
            spine.set_edgecolor("#E0E0E0")
            spine.set_linewidth(1.2)
        
        annotate_bars(ax, bars, fmt, fontsize=26)

        v0 = values[0]
        v1 = values[1]
        if v0 > 0:
            delta_pct = ((v1 - v0) / v0) * 100.0
            
            # Determine if this is a good or bad change
            is_improvement = (delta_pct > 0 and not lower_is_better) or (delta_pct < 0 and lower_is_better)
            
            # Color code the delta
            delta_color = "#27AE60" if is_improvement else "#E74C3C"
            
            # Create styled badge
            badge_text = f"{(1+abs(delta_pct)/100):.2f}x"
            
            ax.text(
                0.5,
                0.97,
                badge_text,
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=20,
                fontweight="bold",
                color=delta_color,
                bbox=dict(
                    boxstyle="round,pad=0.5",
                    facecolor=delta_color,
                    edgecolor="none",
                    alpha=0.15,
                ),
            )

    # Metrics
    draw_metric(
        axes[0],
        throughput_vals,
        "Throughput",
        "tokens/sec",
        lambda v: f"{v:,.1f}",
        lower_is_better=False,
    )

    draw_metric(
        axes[1],
        cost_per_1m_vals,
        "Cost per 1M Tokens",
        "USD",
        lambda v: f"${v:.2f}",
        lower_is_better=True,
    )

    draw_metric(
        axes[2],
        preemption_vals,
        "Preemptions",
        "count",
        lambda v: f"{int(v):,}",
        lower_is_better=True,
    )

    draw_metric(
        axes[3],
        e2e_avg_vals,
        "End-to-End Latency (p50)",
        "seconds",
        human_seconds,
        lower_is_better=True,
    )

    # Modern title with more space below
    fig.suptitle(
        "LLM Inference Strategy Comparison",
        fontsize=42,
        fontweight="bold",
        color="#1A1A1A",
        y=1.22,
    )

    # Metadata footer with better styling
    model = a.get("model_name", a.get("model", "unknown"))
    metadata_text = f"Model: {model}  •  TP={a.get('tp')}  PP={a.get('pp')}  •  {a.get('benchmark_num_requests'):,} Requests"
    
    fig.text(
        0.5,
        0.06,
        metadata_text,
        ha="center",
        fontsize=20,
        color="#7F8C8D",
        style="italic",
    )

    # Modern legend with better styling
    legend_handles = [
        plt.Rectangle(
            (0, 0), 1, 1,
            facecolor=colors[0],
            edgecolor=bar_edge_color,
            linewidth=2,
            label=labels[0],
            alpha=0.9,
        ),
        plt.Rectangle(
            (0, 0), 1, 1,
            facecolor=colors[1],
            edgecolor=bar_edge_color,
            linewidth=2,
            label=labels[1],
            alpha=0.9,
        ),
    ]
    
    legend = fig.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=2,
        frameon=True,
        bbox_to_anchor=(0.5, 1.12),
        fontsize=24,
        title="Strategy",
        title_fontsize=24,
    )
    
    legend.get_frame().set_facecolor("white")
    legend.get_frame().set_edgecolor("#E0E0E0")
    legend.get_frame().set_linewidth(1.5)
    legend.get_frame().set_alpha(0.95)

    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="#FAFAFA")
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor="#FAFAFA")
    plt.close(fig)


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    default_a = (
        base_dir
        / "aws_g5_A10G"
        / "tp4-pp3-3x_g5_12xlarge-ratelimited-20260315_154331-success"
        / "results.json"
    )
    default_b = (
        base_dir
        / "aws_g5_A10G"
        / "tp4-pp3-3x_g5_12xlarge-sendall-20260315_170511-success"
        / "results.json"
    )

    parser = argparse.ArgumentParser(description="Plot bar-chart comparison of two experiments.")
    parser.add_argument("--exp-a", type=Path, default=default_a, help="Path to experiment A results.json")
    parser.add_argument("--exp-b", type=Path, default=default_b, help="Path to experiment B results.json")
    parser.add_argument(
        "--label-a",
        default="ratelimited",
        help="Display label for experiment A (default: ratelimited)",
    )
    parser.add_argument(
        "--label-b",
        default="sendall",
        help="Display label for experiment B (default: sendall)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=base_dir / "comparison_bars.png",
        help="Output image path",
    )

    args = parser.parse_args()

    if not args.exp_a.exists():
        raise FileNotFoundError(f"Missing file: {args.exp_a}")
    if not args.exp_b.exists():
        raise FileNotFoundError(f"Missing file: {args.exp_b}")

    result_a = load_result(args.exp_a)
    result_b = load_result(args.exp_b)
    build_plot(result_a, result_b, args.label_a, args.label_b, args.output)
    print(f"Saved plot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
