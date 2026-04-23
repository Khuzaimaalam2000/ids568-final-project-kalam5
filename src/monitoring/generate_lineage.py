"""
Generate lineage diagram: data -> training -> evaluation -> deployment -> monitoring
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import os

os.makedirs("docs", exist_ok=True)


def generate_lineage_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(16, 8))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8)
    ax.axis("off")
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    fig.suptitle(
        "LLM System Lineage Diagram — kalam5\n"
        "Data → Training → Evaluation → Deployment → Monitoring",
        color="white", fontsize=13, fontweight="bold", y=0.98
    )

    # Define stages
    stages = [
        {
            "label": "DATA\nSOURCE",
            "x": 0.3, "y": 5.5,
            "w": 2.4, "h": 2.0,
            "color": "#1e40af",
            "items": [
                "WebText Corpus",
                "~40GB text",
                "Reddit outbound links",
                "Pre-2019 content",
                "English-dominant"
            ]
        },
        {
            "label": "TRAINING",
            "x": 3.2, "y": 5.5,
            "w": 2.4, "h": 2.0,
            "color": "#7c3aed",
            "items": [
                "GPT-2 Pretraining",
                "OpenAI (2019)",
                "Knowledge Distillation",
                "Hugging Face",
                "82M parameters"
            ]
        },
        {
            "label": "EVALUATION",
            "x": 6.1, "y": 5.5,
            "w": 2.4, "h": 2.0,
            "color": "#065f46",
            "items": [
                "Perplexity: 21.1",
                "WikiText-103",
                "PTB: 60.8",
                "Bias evaluation",
                "Safety checks"
            ]
        },
        {
            "label": "DEPLOYMENT",
            "x": 9.0, "y": 5.5,
            "w": 2.4, "h": 2.0,
            "color": "#92400e",
            "items": [
                "FastAPI server",
                "Dynamic batching",
                "LRU cache (TTL=300s)",
                "CPU inference",
                "Port 8000"
            ]
        },
        {
            "label": "MONITORING",
            "x": 11.9, "y": 5.5,
            "w": 2.4, "h": 2.0,
            "color": "#881337",
            "items": [
                "Prometheus metrics",
                "Grafana dashboard",
                "Drift detection",
                "Alert rules",
                "Audit trail"
            ]
        }
    ]

    # Draw stages
    for stage in stages:
        rect = mpatches.FancyBboxPatch(
            (stage["x"], stage["y"]),
            stage["w"], stage["h"],
            boxstyle="round,pad=0.1",
            facecolor=stage["color"],
            edgecolor="white",
            linewidth=1.5,
            alpha=0.9
        )
        ax.add_patch(rect)

        # Stage label
        ax.text(
            stage["x"] + stage["w"]/2,
            stage["y"] + stage["h"] - 0.25,
            stage["label"],
            ha="center", va="top",
            color="white", fontsize=9,
            fontweight="bold"
        )

        # Items
        for i, item in enumerate(stage["items"]):
            ax.text(
                stage["x"] + 0.15,
                stage["y"] + stage["h"] - 0.55 - i * 0.28,
                f"• {item}",
                ha="left", va="top",
                color="#e2e8f0", fontsize=7.5
            )

    # Draw arrows between stages
    arrow_props = dict(
        arrowstyle="->",
        color="white",
        lw=2.0,
        connectionstyle="arc3,rad=0"
    )

    arrow_positions = [
        (2.7, 6.5, 3.2, 6.5),
        (5.6, 6.5, 6.1, 6.5),
        (8.5, 6.5, 9.0, 6.5),
        (11.4, 6.5, 11.9, 6.5),
    ]

    for x1, y1, x2, y2 in arrow_positions:
        ax.annotate(
            "",
            xy=(x2, y2), xytext=(x1, y1),
            arrowprops=arrow_props
        )

    # Bottom row: artifacts
    artifacts = [
        {"label": "WebText\nDataset", "x": 0.5, "y": 3.5, "color": "#1e3a5f"},
        {"label": "DistilGPT-2\nWeights", "x": 3.4, "y": 3.5, "color": "#4c1d95"},
        {"label": "Benchmark\nResults", "x": 6.3, "y": 3.5, "color": "#064e3b"},
        {"label": "Server\nConfig", "x": 9.2, "y": 3.5, "color": "#78350f"},
        {"label": "Metrics\n& Alerts", "x": 12.1, "y": 3.5, "color": "#4c0519"},
    ]

    for artifact in artifacts:
        rect2 = mpatches.FancyBboxPatch(
            (artifact["x"], artifact["y"]),
            2.0, 0.9,
            boxstyle="round,pad=0.1",
            facecolor=artifact["color"],
            edgecolor="#94a3b8",
            linewidth=1,
            alpha=0.8,
            linestyle="dashed"
        )
        ax.add_patch(rect2)
        ax.text(
            artifact["x"] + 1.0,
            artifact["y"] + 0.45,
            artifact["label"],
            ha="center", va="center",
            color="white", fontsize=8
        )

    # Connect stages to artifacts
    for i, (stage, artifact) in enumerate(zip(stages, artifacts)):
        ax.annotate(
            "",
            xy=(artifact["x"] + 1.0, artifact["y"] + 0.9),
            xytext=(stage["x"] + stage["w"]/2, stage["y"]),
            arrowprops=dict(
                arrowstyle="->",
                color="#64748b",
                lw=1.0,
                connectionstyle="arc3,rad=0"
            )
        )

    # Governance overlay
    gov_rect = mpatches.FancyBboxPatch(
        (0.2, 0.3), 15.6, 2.8,
        boxstyle="round,pad=0.1",
        facecolor="#1e293b",
        edgecolor="#f59e0b",
        linewidth=2,
        alpha=0.6
    )
    ax.add_patch(gov_rect)

    ax.text(
        8.0, 2.85,
        "GOVERNANCE LAYER",
        ha="center", va="center",
        color="#f59e0b", fontsize=10,
        fontweight="bold"
    )

    gov_items = [
        "Model Card (docs/model-card.md)",
        "Risk Register (docs/risk-register.md)",
        "Audit Trail (logs/audit-trail.json)",
        "A/B Testing (EXP-001)",
        "Drift Detection (src/drift/)",
        "Privacy Controls (SHA-256 cache keys, TTL, no PII storage)"
    ]

    for i, item in enumerate(gov_items[:3]):
        ax.text(
            1.5, 2.3 - i * 0.45,
            f"✓ {item}",
            ha="left", va="center",
            color="#94a3b8", fontsize=8
        )

    for i, item in enumerate(gov_items[3:]):
        ax.text(
            8.5, 2.3 - i * 0.45,
            f"✓ {item}",
            ha="left", va="center",
            color="#94a3b8", fontsize=8
        )

    plt.tight_layout()
    path = "docs/lineage-diagram.png"
    plt.savefig(path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"Lineage diagram saved to {path}")


if __name__ == "__main__":
    generate_lineage_diagram()