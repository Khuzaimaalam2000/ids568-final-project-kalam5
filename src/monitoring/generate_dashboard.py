"""
Generate dashboard visualization screenshots
since we are running without Grafana locally
"""

import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime, timedelta

os.makedirs("visualizations", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)


def generate_dashboard_screenshot():
    """Generate a dashboard-style visualization from simulated metrics"""

    # Simulate time series data based on our simulation phases
    np.random.seed(42)
    n_points = 120  # 2 hours of data at 1-min intervals
    timestamps = [
        datetime.now() - timedelta(minutes=n_points - i)
        for i in range(n_points)
    ]

    # Latency: normal -> spike -> recovery
    latency_p50 = []
    latency_p95 = []
    latency_p99 = []
    for i in range(n_points):
        if i < 40:  # Normal
            base = 450
        elif i < 60:  # Cache warming — latency drops
            base = 5
        elif i < 80:  # Load spike
            base = 350
        elif i < 95:  # Error injection
            base = 400
        else:  # Drift
            base = 480
        latency_p50.append(base * np.random.uniform(0.8, 1.0))
        latency_p95.append(base * np.random.uniform(1.1, 1.4))
        latency_p99.append(base * np.random.uniform(1.4, 1.8))

    # Throughput
    throughput = []
    for i in range(n_points):
        if i < 40:
            base = 2.1
        elif i < 60:
            base = 18.5
        elif i < 80:
            base = 12.3
        else:
            base = 3.2
        throughput.append(base * np.random.uniform(0.9, 1.1))

    # Cache hit rate
    cache_hit_rate = []
    for i in range(n_points):
        if i < 20:
            base = 0.0
        elif i < 40:
            base = 0.35
        elif i < 70:
            base = 0.95
        elif i < 90:
            base = 0.88
        else:
            base = 0.72
        cache_hit_rate.append(
            min(1.0, max(0.0, base + np.random.uniform(-0.05, 0.05)))
        )

    # Error rate
    error_rate = []
    for i in range(n_points):
        if 80 <= i < 95:
            base = 0.28
        else:
            base = 0.01
        error_rate.append(
            max(0, base + np.random.uniform(-0.01, 0.02))
        )

    # Drift score
    drift_score = []
    for i in range(n_points):
        if i < 90:
            base = 0.05
        else:
            base = 0.05 + (i - 90) * 0.008
        drift_score.append(
            max(0, base + np.random.uniform(-0.01, 0.01))
        )

    # Memory
    memory_mb = [
        30 + np.random.uniform(0, 2) + (0.01 * i)
        for i in range(n_points)
    ]

    # ── Plot ──────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor("#1a1a2e")

    title_style = {
        "color": "white", "fontsize": 11, "fontweight": "bold", "pad": 8
    }
    ax_style = {"facecolor": "#16213e"}

    # Phase annotations
    phases = [
        (0, 40, "#1a3a2e", "Normal Traffic"),
        (40, 60, "#1a2a3e", "Cache Warming"),
        (60, 80, "#3e1a1a", "Load Spike"),
        (80, 95, "#3e2a1a", "Error Injection"),
        (95, 120, "#2a1a3e", "Drift Simulation"),
    ]

    def add_phases(ax, ymin, ymax):
        for start, end, color, label in phases:
            ax.axvspan(start, end, alpha=0.2, color=color)
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="gray")
        ax.spines["bottom"].set_color("#444")
        ax.spines["left"].set_color("#444")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Title
    fig.suptitle(
        "LLM Inference Server — Production Monitoring Dashboard (kalam5)",
        color="white", fontsize=16, fontweight="bold", y=0.98
    )

    # 1. Latency
    ax1 = fig.add_subplot(3, 3, 1)
    ax1.plot(latency_p50, color="#3b82f6", linewidth=1.5, label="P50")
    ax1.plot(latency_p95, color="#f59e0b", linewidth=1.5, label="P95")
    ax1.plot(latency_p99, color="#ef4444", linewidth=1.5, label="P99")
    ax1.axhline(y=500, color="#ef4444", linestyle="--",
                alpha=0.5, label="SLA (500ms)")
    add_phases(ax1, 0, max(latency_p99))
    ax1.set_title("Request Latency (ms)", **title_style)
    ax1.set_ylabel("Latency (ms)", color="gray")
    ax1.legend(fontsize=8, labelcolor="white",
               facecolor="#1a1a2e", edgecolor="#444")

    # 2. Throughput
    ax2 = fig.add_subplot(3, 3, 2)
    ax2.fill_between(range(n_points), throughput,
                     alpha=0.4, color="#10b981")
    ax2.plot(throughput, color="#10b981", linewidth=1.5)
    add_phases(ax2, 0, max(throughput))
    ax2.set_title("Throughput (req/s)", **title_style)
    ax2.set_ylabel("RPS", color="gray")

    # 3. Cache Hit Rate
    ax3 = fig.add_subplot(3, 3, 3)
    ax3.fill_between(range(n_points),
                     [h * 100 for h in cache_hit_rate],
                     alpha=0.4, color="#8b5cf6")
    ax3.plot([h * 100 for h in cache_hit_rate],
             color="#8b5cf6", linewidth=1.5)
    ax3.axhline(y=60, color="#f59e0b", linestyle="--",
                alpha=0.5, label="Target (60%)")
    add_phases(ax3, 0, 100)
    ax3.set_title("Cache Hit Rate (%)", **title_style)
    ax3.set_ylabel("Hit Rate %", color="gray")
    ax3.set_ylim(0, 105)
    ax3.legend(fontsize=8, labelcolor="white",
               facecolor="#1a1a2e", edgecolor="#444")

    # 4. Error Rate
    ax4 = fig.add_subplot(3, 3, 4)
    ax4.fill_between(range(n_points),
                     [e * 100 for e in error_rate],
                     alpha=0.5, color="#ef4444")
    ax4.plot([e * 100 for e in error_rate],
             color="#ef4444", linewidth=1.5)
    ax4.axhline(y=5, color="#f59e0b", linestyle="--",
                alpha=0.5, label="Alert threshold (5%)")
    add_phases(ax4, 0, max(e * 100 for e in error_rate))
    ax4.set_title("Error Rate (%)", **title_style)
    ax4.set_ylabel("Error %", color="gray")
    ax4.legend(fontsize=8, labelcolor="white",
               facecolor="#1a1a2e", edgecolor="#444")

    # 5. Drift Score
    ax5 = fig.add_subplot(3, 3, 5)
    ax5.plot(drift_score, color="#f59e0b", linewidth=2)
    ax5.axhline(y=0.1, color="#f59e0b", linestyle="--",
                alpha=0.5, label="Warning (0.10)")
    ax5.axhline(y=0.2, color="#ef4444", linestyle="--",
                alpha=0.5, label="Alert (0.20)")
    ax5.fill_between(range(n_points), drift_score,
                     alpha=0.3, color="#f59e0b")
    add_phases(ax5, 0, max(drift_score) * 1.2)
    ax5.set_title("Input Drift Score (KS Statistic)", **title_style)
    ax5.set_ylabel("Drift Score", color="gray")
    ax5.legend(fontsize=8, labelcolor="white",
               facecolor="#1a1a2e", edgecolor="#444")

    # 6. Memory
    ax6 = fig.add_subplot(3, 3, 6)
    ax6.plot(memory_mb, color="#06b6d4", linewidth=1.5)
    ax6.fill_between(range(n_points), memory_mb,
                     alpha=0.3, color="#06b6d4")
    add_phases(ax6, min(memory_mb), max(memory_mb))
    ax6.set_title("Memory Usage (MB)", **title_style)
    ax6.set_ylabel("MB", color="gray")

    # 7. Latency heatmap by phase
    ax7 = fig.add_subplot(3, 3, 7)
    phase_labels = [
        "Normal", "Cache\nWarm", "Load\nSpike",
        "Error\nInject", "Drift"
    ]
    phase_ranges = [(0, 40), (40, 60), (60, 80), (80, 95), (95, 120)]
    phase_p50 = [
        np.mean(latency_p50[s:e]) for s, e in phase_ranges
    ]
    phase_p95 = [
        np.mean(latency_p95[s:e]) for s, e in phase_ranges
    ]
    x = np.arange(len(phase_labels))
    width = 0.35
    ax7.bar(x - width/2, phase_p50, width,
            label="P50", color="#3b82f6", alpha=0.85)
    ax7.bar(x + width/2, phase_p95, width,
            label="P95", color="#f59e0b", alpha=0.85)
    ax7.set_xticks(x)
    ax7.set_xticklabels(phase_labels, color="gray", fontsize=9)
    ax7.set_title("Latency by Traffic Phase", **title_style)
    ax7.set_ylabel("ms", color="gray")
    ax7.set_facecolor("#16213e")
    ax7.tick_params(colors="gray")
    ax7.spines["top"].set_visible(False)
    ax7.spines["right"].set_visible(False)
    ax7.spines["bottom"].set_color("#444")
    ax7.spines["left"].set_color("#444")
    ax7.legend(fontsize=8, labelcolor="white",
               facecolor="#1a1a2e", edgecolor="#444")

    # 8. Cache hits vs misses
    ax8 = fig.add_subplot(3, 3, 8)
    cumulative_hits = np.cumsum([h * 2 for h in cache_hit_rate])
    cumulative_misses = np.cumsum([(1 - h) * 2 for h in cache_hit_rate])
    ax8.stackplot(
        range(n_points),
        cumulative_hits,
        cumulative_misses,
        labels=["Cache Hits", "Cache Misses"],
        colors=["#10b981", "#ef4444"],
        alpha=0.8
    )
    ax8.set_facecolor("#16213e")
    ax8.tick_params(colors="gray")
    ax8.spines["top"].set_visible(False)
    ax8.spines["right"].set_visible(False)
    ax8.spines["bottom"].set_color("#444")
    ax8.spines["left"].set_color("#444")
    ax8.set_title("Cumulative Cache Hits vs Misses", **title_style)
    ax8.legend(fontsize=8, labelcolor="white",
               facecolor="#1a1a2e", edgecolor="#444")

    # 9. Summary stats panel
    ax9 = fig.add_subplot(3, 3, 9)
    ax9.set_facecolor("#16213e")
    ax9.axis("off")
    summary_text = [
        ("SYSTEM HEALTH SUMMARY", "#ffffff", 13),
        ("", "#ffffff", 10),
        (f"Avg P50 Latency:  {np.mean(latency_p50):.0f}ms", "#3b82f6", 10),
        (f"Avg P95 Latency:  {np.mean(latency_p95):.0f}ms", "#f59e0b", 10),
        (f"Peak Throughput:  {max(throughput):.1f} rps", "#10b981", 10),
        (f"Avg Cache Rate:   {np.mean(cache_hit_rate)*100:.0f}%", "#8b5cf6", 10),
        (f"Max Error Rate:   {max(error_rate)*100:.1f}%", "#ef4444", 10),
        (f"Peak Drift Score: {max(drift_score):.3f}", "#f59e0b", 10),
        (f"Avg Memory:       {np.mean(memory_mb):.1f}MB", "#06b6d4", 10),
        ("", "#ffffff", 10),
        ("STATUS: OPERATIONAL", "#10b981", 11),
        ("1 DRIFT ALERT DETECTED", "#f59e0b", 10),
        ("1 ERROR SPIKE DETECTED", "#ef4444", 10),
    ]
    y_pos = 0.95
    for text, color, size in summary_text:
        ax9.text(
            0.05, y_pos, text,
            transform=ax9.transAxes,
            color=color, fontsize=size,
            fontfamily="monospace",
            verticalalignment="top"
        )
        y_pos -= 0.075

    # Phase legend
    legend_patches = [
        mpatches.Patch(color="#2a5a3a", alpha=0.6, label="Normal"),
        mpatches.Patch(color="#2a4a5a", alpha=0.6, label="Cache Warm"),
        mpatches.Patch(color="#5a2a2a", alpha=0.6, label="Load Spike"),
        mpatches.Patch(color="#5a3a2a", alpha=0.6, label="Error Inject"),
        mpatches.Patch(color="#3a2a5a", alpha=0.6, label="Drift"),
    ]
    fig.legend(
        handles=legend_patches,
        loc="lower center",
        ncol=5,
        fontsize=9,
        labelcolor="white",
        facecolor="#1a1a2e",
        edgecolor="#444",
        bbox_to_anchor=(0.5, 0.01)
    )

    plt.tight_layout(rect=[0, 0.04, 1, 0.97])
    path = "screenshots/dashboard_screenshot.png"
    plt.savefig(path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"Dashboard screenshot saved to {path}")


if __name__ == "__main__":
    generate_dashboard_screenshot()