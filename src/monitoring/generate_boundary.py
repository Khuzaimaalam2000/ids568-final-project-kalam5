"""
Generate system boundary diagram
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import os

os.makedirs("docs", exist_ok=True)


def generate_boundary_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(18, 11))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 11)
    ax.axis("off")
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    fig.suptitle(
        "System Boundary Diagram — LLM Inference Server\n"
        "kalam5 | IDS568 Final Project",
        color="white", fontsize=14,
        fontweight="bold", y=0.98
    )

    def box(x, y, w, h, color, label, sublabel=None,
            edge="white", lw=1.5, alpha=0.85):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.15",
            facecolor=color,
            edgecolor=edge,
            linewidth=lw,
            alpha=alpha
        )
        ax.add_patch(rect)
        ax.text(
            x + w/2, y + h/2 + (0.15 if sublabel else 0),
            label, ha="center", va="center",
            color="white", fontsize=9,
            fontweight="bold"
        )
        if sublabel:
            ax.text(
                x + w/2, y + h/2 - 0.25,
                sublabel, ha="center", va="center",
                color="#cbd5e1", fontsize=7.5
            )

    def arrow(x1, y1, x2, y2, label="", color="white", lw=1.5):
        ax.annotate(
            "",
            xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle="->",
                color=color,
                lw=lw,
                connectionstyle="arc3,rad=0"
            )
        )
        if label:
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            ax.text(mx, my + 0.15, label,
                    ha="center", color="#94a3b8", fontsize=7)

    # ── External boundary ─────────────────────────────────────
    ext_rect = mpatches.FancyBboxPatch(
        (0.2, 0.3), 17.6, 10.2,
        boxstyle="round,pad=0.1",
        facecolor="none",
        edgecolor="#f59e0b",
        linewidth=2,
        linestyle="dashed"
    )
    ax.add_patch(ext_rect)
    ax.text(
        0.5, 10.35, "SYSTEM BOUNDARY",
        color="#f59e0b", fontsize=9, fontweight="bold"
    )

    # ── Client ────────────────────────────────────────────────
    box(0.5, 4.5, 2.2, 1.2,
        "#1e3a5f", "CLIENT",
        "HTTP POST /infer")

    # ── API Gateway ───────────────────────────────────────────
    box(3.2, 4.5, 2.4, 1.2,
        "#1e40af", "FastAPI\nGATEWAY",
        "Port 8000")

    # ── Rate limiter ──────────────────────────────────────────
    box(3.2, 6.5, 2.4, 0.9,
        "#374151", "Rate Limiter",
        "(planned: 100/min)")

    # ── Input validator ───────────────────────────────────────
    box(3.2, 2.8, 2.4, 0.9,
        "#374151", "Input Validator",
        "Sanitization")

    # ── Cache layer ───────────────────────────────────────────
    box(6.5, 4.5, 2.6, 1.2,
        "#065f46", "LRU CACHE",
        "TTL=300s | max=1000\nSHA-256 keys")

    # ── Cache store ───────────────────────────────────────────
    box(6.5, 2.5, 2.6, 1.0,
        "#064e3b", "Cache Store",
        "In-process dict\nNo PII stored")

    # ── Batcher ───────────────────────────────────────────────
    box(10.0, 4.5, 2.6, 1.2,
        "#7c3aed", "DYNAMIC\nBATCHER",
        "batch=8 | timeout=50ms")

    # ── Request queue ─────────────────────────────────────────
    box(10.0, 6.5, 2.6, 0.9,
        "#4c1d95", "Request Queue",
        "asyncio | max=100")

    # ── Model ─────────────────────────────────────────────────
    box(13.5, 4.5, 2.8, 1.2,
        "#92400e", "DistilGPT-2\nMODEL",
        "82M params | CPU")

    # ── Monitoring ────────────────────────────────────────────
    box(13.5, 7.0, 2.8, 1.0,
        "#881337", "PROMETHEUS\nMETRICS",
        "/metrics endpoint")

    box(13.5, 8.5, 2.8, 1.0,
        "#7f1d1d", "GRAFANA\nDASHBOARD",
        "Alerts + Visualization")

    box(13.5, 2.5, 2.8, 1.0,
        "#78350f", "DRIFT\nDETECTOR",
        "KS test | PSI | Z-score")

    # ── Audit log ─────────────────────────────────────────────
    box(10.0, 2.5, 2.6, 1.0,
        "#1e293b", "AUDIT TRAIL",
        "logs/audit-trail.json")

    # ── Arrows ────────────────────────────────────────────────
    # Client -> Gateway
    arrow(2.7, 5.1, 3.2, 5.1, "HTTP Request")

    # Gateway -> Cache
    arrow(5.6, 5.1, 6.5, 5.1, "Cache lookup")

    # Cache -> Batcher (miss)
    arrow(9.1, 5.1, 10.0, 5.1, "Cache miss")

    # Batcher -> Model
    arrow(12.6, 5.1, 13.5, 5.1, "Batch inference")

    # Model -> Cache (store)
    arrow(14.9, 4.5, 14.9, 3.5, "Store response")
    arrow(14.9, 3.5, 9.1, 3.0, "")

    # Cache -> Client (hit)
    arrow(6.5, 5.4, 5.6, 5.4, "Cache hit")
    arrow(3.2, 5.4, 2.7, 5.4, "Response")

    # Gateway -> Rate limiter
    arrow(4.4, 5.7, 4.4, 6.5, "Check limit", color="#94a3b8", lw=1)

    # Gateway -> Input validator
    arrow(4.4, 4.5, 4.4, 3.7, "Validate", color="#94a3b8", lw=1)

    # Batcher -> Queue
    arrow(11.3, 5.7, 11.3, 6.5, "Queue req", color="#94a3b8", lw=1)

    # Model -> Monitoring
    arrow(14.9, 5.7, 14.9, 7.0, "Emit metrics", color="#ef4444", lw=1)

    # Monitoring -> Dashboard
    arrow(14.9, 8.0, 14.9, 8.5, "Scrape", color="#ef4444", lw=1)

    # Model -> Drift detector
    arrow(14.9, 4.5, 14.9, 3.5, "", color="#f59e0b", lw=1)

    # Drift -> Audit
    arrow(13.5, 3.0, 12.6, 3.0, "Log event", color="#f59e0b", lw=1)

    # ── Legend ────────────────────────────────────────────────
    legend_items = [
        ("#1e40af", "API Layer"),
        ("#065f46", "Cache Layer"),
        ("#7c3aed", "Batching Layer"),
        ("#92400e", "Model Layer"),
        ("#881337", "Monitoring Layer"),
        ("#374151", "Security Controls (planned)"),
    ]

    for i, (color, label) in enumerate(legend_items):
        rect = mpatches.Rectangle(
            (0.5 + i * 2.9, 0.35), 0.4, 0.25,
            facecolor=color, edgecolor="white", linewidth=0.5
        )
        ax.add_patch(rect)
        ax.text(
            0.95 + i * 2.9, 0.48, label,
            color="#cbd5e1", fontsize=7.5, va="center"
        )

    plt.tight_layout()
    path = "docs/system-boundary-diagram.png"
    plt.savefig(path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"System boundary diagram saved to {path}")


if __name__ == "__main__":
    generate_boundary_diagram()