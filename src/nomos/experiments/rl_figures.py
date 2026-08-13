"""Publication figures for the verifier-quality frontier (V4, #275).

Two figures. The headline is bypass rate against verifier accuracy — the curve
the epic exists to produce, because its *shape* is the finding: whether
governance degrades gracefully as the verifier gets worse, or falls off a cliff
somewhere between "perfect" and "merely good".

The companion panel exists so the headline cannot be read in isolation.
Detection rate and Safety-silencing say *how* the layer failed; veto precision
says what a degraded verifier costs when it errs the other way, blocking safe
actions for lies nobody told; and spoof-region occupancy says whether the
adversary was ever really in the game — without which a flat curve would mean
nothing at all.

Intervals are clamped to [0, 1] because these are rates, following the
convention Appendix E §E.4 already uses for bounded quantities.
"""

from __future__ import annotations

import os
from typing import Any

#: Arm colours, chosen to stay distinguishable in greyscale print.
_ARM_STYLE = {
    "unshaped": {"color": "#1f77b4", "marker": "o", "linestyle": "-"},
    "shaped": {"color": "#d62728", "marker": "s", "linestyle": "--"},
}
_CONTROL_STYLE = {
    "no_governance": {"color": "#7f7f7f", "linestyle": ":", "label": "no_governance (ceiling)"},
    "static_mask": {"color": "#2ca02c", "linestyle": "-.", "label": "static_mask (floor)"},
}


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)


def _series(frontier: dict[str, Any], arm: str, key: str):
    """Return ``(epsilons, means, lows, highs)`` for one arm's metric.

    Points whose metric was undefined for every seed are dropped rather than
    plotted as zero — the same rule the metrics use. A gap in a line is honest;
    a zero is a claim.
    """
    xs: list[float] = []
    means: list[float] = []
    lows: list[float] = []
    highs: list[float] = []
    for point in sorted(
        (p for p in frontier["points"] if p["arm"] == arm), key=lambda p: p["epsilon"]
    ):
        block = point.get(key)
        if not isinstance(block, dict) or not block.get("n", 0):
            continue
        mean, ci = block["mean"], block.get("ci95", 0.0)
        xs.append(point["epsilon"])
        means.append(mean)
        lows.append(max(0.0, mean - ci))
        highs.append(min(1.0, mean + ci))
    return xs, means, lows, highs


def _plot_metric(ax, frontier: dict[str, Any], key: str, title: str, ylabel: str) -> None:
    for arm, style in _ARM_STYLE.items():
        xs, means, lows, highs = _series(frontier, arm, key)
        if not xs:
            continue
        ax.plot(xs, means, label=arm, linewidth=1.8, markersize=5, **style)
        ax.fill_between(xs, lows, highs, alpha=0.15, color=style["color"])
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Verifier accuracy ε")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def plot_verifier_frontier(frontier: dict[str, Any], output_dir: str = "docs/benchmarks") -> Any:
    """Plot the headline curve: governance bypass rate against verifier accuracy.

    Args:
        frontier: The dict produced by :func:`~.rl_sweep.run_sweep`.
        output_dir: Directory for the PNG and SVG outputs.

    Returns:
        The :class:`matplotlib.figure.Figure`.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = f"{output_dir}/verifier_frontier.png"
    _ensure_dir(path)

    fig, ax = plt.subplots(figsize=(9, 6))
    _plot_metric(ax, frontier, "bypass_rate", "", "Governance bypass rate")
    fig.suptitle("Governance bypass rate vs. verifier accuracy", fontsize=14, fontweight="bold")

    for mode, style in _CONTROL_STYLE.items():
        control = frontier.get("controls", {}).get(mode)
        if not isinstance(control, dict):
            continue
        block = control.get("bypass_rate")
        if isinstance(block, dict) and block.get("n", 0):
            ax.axhline(
                block["mean"],
                color=style["color"],
                linestyle=style["linestyle"],
                linewidth=1.2,
                label=style["label"],
            )

    # Shade the critical-ε region when the curve actually has one. Drawing it
    # unconditionally would invite reading a cliff into a smooth curve.
    region = frontier.get("verdicts", {}).get("curve_shape", {}).get("critical_epsilon_region")
    if region:
        ax.axvspan(min(region), max(region), color="#d62728", alpha=0.08, label="critical-ε region")

    ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=9, loc="upper right")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.savefig(f"{output_dir}/verifier_frontier.svg", format="svg")
    plt.close()
    print(f"  -> {path}")
    return fig


def plot_frontier_panels(frontier: dict[str, Any], output_dir: str = "docs/benchmarks") -> Any:
    """Plot the companion panels that stop the headline being read alone.

    Args:
        frontier: The dict produced by :func:`~.rl_sweep.run_sweep`.
        output_dir: Directory for the PNG and SVG outputs.

    Returns:
        The :class:`matplotlib.figure.Figure`.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = f"{output_dir}/verifier_frontier_panels.png"
    _ensure_dir(path)

    panels = [
        ("detection_rate", "Falsification detection", "Detection rate"),
        ("safety_silenced_rate", "Safety silencing", "Silenced rate"),
        ("veto_precision", "Cost of false alarms", "Veto precision"),
        ("spoof_region_rate", "Was the adversary in the game?", "Spoof-region occupancy"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("Verifier-quality frontier: companion panels", fontsize=14, fontweight="bold")
    for ax, (key, title, ylabel) in zip(axes.flatten(), panels, strict=True):
        _plot_metric(ax, frontier, key, title, ylabel)
        ax.set_ylim(-0.02, 1.02)
    axes[0][0].legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.savefig(f"{output_dir}/verifier_frontier_panels.svg", format="svg")
    plt.close()
    print(f"  -> {path}")
    return fig


def generate_frontier_figures(
    frontier: dict[str, Any], output_dir: str = "docs/benchmarks"
) -> dict[str, Any]:
    """Generate both frontier figures.

    Args:
        frontier: The dict produced by :func:`~.rl_sweep.run_sweep`.
        output_dir: Directory for the outputs.

    Returns:
        Mapping of figure name to :class:`matplotlib.figure.Figure`.
    """
    print("Generating verifier-frontier figures...")
    return {
        "verifier_frontier": plot_verifier_frontier(frontier, output_dir),
        "verifier_frontier_panels": plot_frontier_panels(frontier, output_dir),
    }
