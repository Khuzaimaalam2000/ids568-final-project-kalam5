"""
Data Integrity and Drift Detection
Detects feature drift, label drift, and anomalies
using statistical tests and visualizations.
Built on scipy and custom implementations.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import ks_2samp, chi2_contingency, wasserstein_distance
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

os.makedirs("visualizations", exist_ok=True)
os.makedirs("logs", exist_ok=True)

np.random.seed(42)


# ── Data Generation ───────────────────────────────────────────────────────────

def generate_reference_data(n: int = 1000) -> pd.DataFrame:
    """
    Generate reference distribution representing
    healthy production traffic from Milestone 4/5.
    """
    return pd.DataFrame({
        "prompt_length": np.random.normal(12.5, 3.2, n).clip(3, 40),
        "response_length": np.random.normal(28.4, 8.1, n).clip(5, 60),
        "latency_ms": np.random.normal(420, 45, n).clip(50, 800),
        "transaction_amount": np.random.normal(250, 144, n).clip(5, 500),
        "category_id": np.random.randint(1, 11, n),
        "hour_of_day": np.random.randint(0, 24, n),
        "cache_hit": np.random.binomial(1, 0.65, n),
        "error": np.random.binomial(1, 0.02, n),
        "timestamp": [
            datetime(2026, 3, 1) + timedelta(hours=i * 0.5)
            for i in range(n)
        ]
    })


def generate_production_windows(
    reference: pd.DataFrame,
    n_windows: int = 8,
    n_per_window: int = 200
) -> List[pd.DataFrame]:
    """
    Generate production data windows with progressive drift.
    Each window shows increasing deviation from reference.
    """
    windows = []

    for w in range(n_windows):
        drift_factor = w / (n_windows - 1)

        # Gradual drift in prompt length (users sending longer prompts)
        prompt_mean = 12.5 + drift_factor * 18.0
        prompt_std = 3.2 + drift_factor * 5.0

        # Latency degrades as prompts get longer
        latency_mean = 420 + drift_factor * 280

        # Transaction amount distribution shifts
        amount_mean = 250 + drift_factor * 150
        amount_std = 144 + drift_factor * 80

        # Error rate increases under drift
        error_rate = 0.02 + drift_factor * 0.12

        # Cache hit rate decreases (new unique prompts)
        cache_rate = 0.65 - drift_factor * 0.45

        window = pd.DataFrame({
            "prompt_length": np.random.normal(
                prompt_mean, prompt_std, n_per_window
            ).clip(3, 100),
            "response_length": np.random.normal(
                28.4 + drift_factor * 20, 8.1, n_per_window
            ).clip(5, 150),
            "latency_ms": np.random.normal(
                latency_mean, 45 + drift_factor * 60, n_per_window
            ).clip(50, 2000),
            "transaction_amount": np.random.normal(
                amount_mean, amount_std, n_per_window
            ).clip(5, 1000),
            "category_id": np.random.randint(1, 11, n_per_window),
            "hour_of_day": np.random.randint(0, 24, n_per_window),
            "cache_hit": np.random.binomial(1, max(0.05, cache_rate),
                                            n_per_window),
            "error": np.random.binomial(1, min(0.5, error_rate),
                                        n_per_window),
            "window": w,
            "drift_factor": drift_factor,
            "timestamp": [
                datetime(2026, 3, 15) + timedelta(
                    days=w * 3,
                    hours=i * 0.5
                )
                for i in range(n_per_window)
            ]
        })
        windows.append(window)

    return windows


# ── Statistical Tests ─────────────────────────────────────────────────────────

def compute_psi(
    reference: np.ndarray,
    production: np.ndarray,
    n_bins: int = 10
) -> float:
    """
    Population Stability Index (PSI).
    PSI < 0.1: No significant change
    PSI 0.1-0.2: Moderate change, monitor
    PSI > 0.2: Significant change, action required
    """
    min_val = min(reference.min(), production.min())
    max_val = max(reference.max(), production.max())
    bins = np.linspace(min_val, max_val, n_bins + 1)

    ref_counts, _ = np.histogram(reference, bins=bins)
    prod_counts, _ = np.histogram(production, bins=bins)

    # Avoid division by zero
    ref_pct = (ref_counts + 0.0001) / len(reference)
    prod_pct = (prod_counts + 0.0001) / len(production)

    psi = np.sum((prod_pct - ref_pct) * np.log(prod_pct / ref_pct))
    return float(psi)


def compute_ks_test(
    reference: np.ndarray,
    production: np.ndarray
) -> Tuple[float, float]:
    """KS test: returns (statistic, p_value)"""
    stat, pvalue = ks_2samp(reference, production)
    return float(stat), float(pvalue)


def compute_wasserstein(
    reference: np.ndarray,
    production: np.ndarray
) -> float:
    """Earth Mover's Distance (Wasserstein-1)"""
    return float(wasserstein_distance(reference, production))


def detect_anomalies(
    data: np.ndarray,
    threshold: float = 3.0
) -> np.ndarray:
    """
    Z-score based anomaly detection.
    Returns boolean mask of anomalous points.
    """
    z_scores = np.abs(stats.zscore(data))
    return z_scores > threshold


def run_drift_analysis(
    reference: pd.DataFrame,
    windows: List[pd.DataFrame],
    features: List[str]
) -> Dict:
    """
    Run comprehensive drift analysis across all windows and features.
    """
    results = {
        "features": {},
        "windows": [],
        "summary": {}
    }

    for feature in features:
        ref_data = reference[feature].values
        feature_results = {
            "psi_scores": [],
            "ks_statistics": [],
            "ks_pvalues": [],
            "wasserstein_distances": [],
            "anomaly_rates": [],
            "drift_severity": []
        }

        for w, window in enumerate(windows):
            prod_data = window[feature].values

            psi = compute_psi(ref_data, prod_data)
            ks_stat, ks_pval = compute_ks_test(ref_data, prod_data)
            wass = compute_wasserstein(ref_data, prod_data)
            anomalies = detect_anomalies(prod_data)

            feature_results["psi_scores"].append(psi)
            feature_results["ks_statistics"].append(ks_stat)
            feature_results["ks_pvalues"].append(ks_pval)
            feature_results["wasserstein_distances"].append(wass)
            feature_results["anomaly_rates"].append(
                float(anomalies.mean())
            )

            # Severity classification
            if psi < 0.1 and ks_stat < 0.1:
                severity = "STABLE"
            elif psi < 0.2 and ks_stat < 0.2:
                severity = "WARNING"
            else:
                severity = "CRITICAL"
            feature_results["drift_severity"].append(severity)

        results["features"][feature] = feature_results

    # Window-level summary
    for w, window in enumerate(windows):
        window_summary = {
            "window": w,
            "drift_factor": float(window["drift_factor"].iloc[0]),
            "n_samples": len(window),
            "error_rate": float(window["error"].mean()),
            "cache_hit_rate": float(window["cache_hit"].mean()),
            "critical_features": [
                f for f in features
                if results["features"][f]["drift_severity"][w] == "CRITICAL"
            ]
        }
        results["windows"].append(window_summary)

    # Overall summary
    most_drifted = max(
        features,
        key=lambda f: max(results["features"][f]["psi_scores"])
    )
    results["summary"] = {
        "most_drifted_feature": most_drifted,
        "max_psi": max(results["features"][most_drifted]["psi_scores"]),
        "features_in_critical": [
            f for f in features
            if "CRITICAL" in results["features"][f]["drift_severity"]
        ],
        "first_critical_window": min(
            [
                next(
                    (i for i, s in enumerate(
                        results["features"][f]["drift_severity"]
                    ) if s == "CRITICAL"),
                    999
                )
                for f in features
            ]
        )
    }

    return results


# ── Visualizations ────────────────────────────────────────────────────────────

def generate_drift_visualizations(
    reference: pd.DataFrame,
    windows: List[pd.DataFrame],
    drift_results: Dict,
    features: List[str]
) -> None:
    """Generate comprehensive drift visualization dashboard"""

    n_features = len(features)
    fig = plt.figure(figsize=(20, 16))
    fig.suptitle(
        "Data Drift Detection Dashboard — kalam5\n"
        "Reference: March 2026 | Production: April-May 2026 (8 windows)",
        fontsize=14, fontweight="bold", y=0.98
    )

    gs = gridspec.GridSpec(
        4, n_features,
        figure=fig,
        hspace=0.45, wspace=0.35
    )

    colors_severity = {
        "STABLE": "#10b981",
        "WARNING": "#f59e0b",
        "CRITICAL": "#ef4444"
    }

    window_labels = [f"W{i}" for i in range(len(windows))]

    # Row 1: PSI scores over time per feature
    for fi, feature in enumerate(features):
        ax = fig.add_subplot(gs[0, fi])
        psi_scores = drift_results["features"][feature]["psi_scores"]
        severities = drift_results["features"][feature]["drift_severity"]
        bar_colors = [colors_severity[s] for s in severities]

        bars = ax.bar(window_labels, psi_scores,
                      color=bar_colors, alpha=0.85)
        ax.axhline(y=0.1, color="#f59e0b", linestyle="--",
                   linewidth=1, label="Warning (0.1)")
        ax.axhline(y=0.2, color="#ef4444", linestyle="--",
                   linewidth=1, label="Critical (0.2)")
        ax.set_title(f"PSI: {feature}", fontsize=9, fontweight="bold")
        ax.set_ylabel("PSI Score", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3, axis="y")

    # Row 2: KS statistic over time
    for fi, feature in enumerate(features):
        ax = fig.add_subplot(gs[1, fi])
        ks_stats = drift_results["features"][feature]["ks_statistics"]
        ks_pvals = drift_results["features"][feature]["ks_pvalues"]

        ax.plot(window_labels, ks_stats,
                marker="o", color="#3b82f6", linewidth=2, label="KS Stat")
        ax.axhline(y=0.1, color="#f59e0b", linestyle="--",
                   linewidth=1, label="Warning")
        ax.axhline(y=0.2, color="#ef4444", linestyle="--",
                   linewidth=1, label="Critical")

        # Mark significant drift (p < 0.05)
        for i, (ks, pv) in enumerate(zip(ks_stats, ks_pvals)):
            if pv < 0.05:
                ax.plot(i, ks, "r*", markersize=10)

        ax.set_title(f"KS Test: {feature}", fontsize=9, fontweight="bold")
        ax.set_ylabel("KS Statistic", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3)

    # Row 3: Distribution comparison (reference vs last window)
    last_window = windows[-1]
    for fi, feature in enumerate(features):
        ax = fig.add_subplot(gs[2, fi])
        ax.hist(
            reference[feature],
            bins=30, alpha=0.6,
            color="#3b82f6", density=True,
            label="Reference"
        )
        ax.hist(
            last_window[feature],
            bins=30, alpha=0.6,
            color="#ef4444", density=True,
            label="Production (W7)"
        )
        ax.set_title(
            f"Distribution: {feature}\n"
            f"(PSI={drift_results['features'][feature]['psi_scores'][-1]:.3f})",
            fontsize=9, fontweight="bold"
        )
        ax.set_ylabel("Density", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3)

    # Row 4: System metrics over windows
    ax_err = fig.add_subplot(gs[3, 0])
    error_rates = [w["error_rate"] * 100
                   for w in drift_results["windows"]]
    ax_err.plot(window_labels, error_rates,
                marker="o", color="#ef4444",
                linewidth=2, label="Error Rate %")
    ax_err.axhline(y=5, color="#ef4444", linestyle="--",
                   alpha=0.5, label="Alert threshold")
    ax_err.fill_between(range(len(window_labels)),
                        error_rates, alpha=0.2, color="#ef4444")
    ax_err.set_title("Error Rate Over Windows",
                     fontsize=9, fontweight="bold")
    ax_err.set_ylabel("Error Rate (%)", fontsize=8)
    ax_err.legend(fontsize=7)
    ax_err.tick_params(labelsize=7)
    ax_err.grid(True, alpha=0.3)

    ax_cache = fig.add_subplot(gs[3, 1])
    cache_rates = [w["cache_hit_rate"] * 100
                   for w in drift_results["windows"]]
    ax_cache.plot(window_labels, cache_rates,
                  marker="o", color="#10b981",
                  linewidth=2, label="Cache Hit Rate %")
    ax_cache.axhline(y=30, color="#f59e0b", linestyle="--",
                     alpha=0.5, label="Warning threshold")
    ax_cache.fill_between(range(len(window_labels)),
                          cache_rates, alpha=0.2, color="#10b981")
    ax_cache.set_title("Cache Hit Rate Over Windows",
                       fontsize=9, fontweight="bold")
    ax_cache.set_ylabel("Cache Hit Rate (%)", fontsize=8)
    ax_cache.legend(fontsize=7)
    ax_cache.tick_params(labelsize=7)
    ax_cache.grid(True, alpha=0.3)

    ax_wass = fig.add_subplot(gs[3, 2])
    for feature, color in zip(
        features, ["#3b82f6", "#10b981", "#f59e0b"]
    ):
        wass = drift_results["features"][feature]["wasserstein_distances"]
        ax_wass.plot(window_labels, wass,
                     marker="o", color=color,
                     linewidth=2, label=feature, alpha=0.85)
    ax_wass.set_title("Wasserstein Distance Over Windows",
                      fontsize=9, fontweight="bold")
    ax_wass.set_ylabel("Earth Mover's Distance", fontsize=8)
    ax_wass.legend(fontsize=7)
    ax_wass.tick_params(labelsize=7)
    ax_wass.grid(True, alpha=0.3)

    ax_sum = fig.add_subplot(gs[3, 3])
    ax_sum.axis("off")
    summary = drift_results["summary"]
    summary_lines = [
        ("DRIFT SUMMARY", "#ffffff", 10),
        ("", "#ffffff", 8),
        (f"Most drifted:", "#94a3b8", 8),
        (f"  {summary['most_drifted_feature']}", "#ef4444", 9),
        (f"Max PSI: {summary['max_psi']:.3f}", "#ef4444", 8),
        ("", "#ffffff", 8),
        (f"Critical features:", "#94a3b8", 8),
    ]
    for f in summary["features_in_critical"]:
        summary_lines.append((f"  • {f}", "#ef4444", 8))
    summary_lines += [
        ("", "#ffffff", 8),
        (f"First critical window:", "#94a3b8", 8),
        (f"  Window {summary['first_critical_window']}",
         "#f59e0b", 8),
        ("", "#ffffff", 8),
        ("RECOMMENDATION:", "#ffffff", 9),
        ("Trigger retraining", "#ef4444", 9),
        ("at Window 5+", "#ef4444", 8),
    ]

    y = 0.95
    for text, color, size in summary_lines:
        ax_sum.text(
            0.05, y, text,
            transform=ax_sum.transAxes,
            color=color, fontsize=size,
            fontfamily="monospace",
            verticalalignment="top"
        )
        y -= 0.075

    plt.savefig(
        "visualizations/drift_analysis.png",
        dpi=150, bbox_inches="tight"
    )
    plt.close()
    print("Saved: visualizations/drift_analysis.png")


def generate_anomaly_visualization(
    reference: pd.DataFrame,
    windows: List[pd.DataFrame]
) -> None:
    """Generate anomaly detection visualization"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Anomaly Detection: Input Integrity Checks — kalam5",
        fontsize=13, fontweight="bold"
    )

    features = ["prompt_length", "latency_ms",
                "transaction_amount", "response_length"]

    for ax, feature in zip(axes.flat, features):
        all_data = []
        all_labels = []
        all_anomalies = []

        for w, window in enumerate(windows):
            data = window[feature].values
            anomalies = detect_anomalies(data)
            all_data.extend(data)
            all_labels.extend([w] * len(data))
            all_anomalies.extend(anomalies)

        all_data = np.array(all_data)
        all_labels = np.array(all_labels)
        all_anomalies = np.array(all_anomalies)

        # Normal points
        ax.scatter(
            all_labels[~all_anomalies],
            all_data[~all_anomalies],
            alpha=0.3, s=8, color="#3b82f6", label="Normal"
        )
        # Anomalous points
        if all_anomalies.any():
            ax.scatter(
                all_labels[all_anomalies],
                all_data[all_anomalies],
                alpha=0.8, s=30, color="#ef4444",
                marker="x", label="Anomaly", linewidths=2
            )

        # Reference mean and std band
        ref_mean = reference[feature].mean()
        ref_std = reference[feature].std()
        ax.axhline(y=ref_mean, color="#10b981",
                   linestyle="--", linewidth=1.5,
                   label=f"Ref mean={ref_mean:.1f}")
        ax.axhspan(
            ref_mean - 3*ref_std,
            ref_mean + 3*ref_std,
            alpha=0.1, color="#10b981",
            label="3σ band"
        )

        anomaly_rate = all_anomalies.mean() * 100
        ax.set_title(
            f"{feature}\n(Anomaly rate: {anomaly_rate:.1f}%)",
            fontweight="bold"
        )
        ax.set_xlabel("Production Window")
        ax.set_ylabel(feature)
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        "visualizations/anomaly_detection.png",
        dpi=150, bbox_inches="tight"
    )
    plt.close()
    print("Saved: visualizations/anomaly_detection.png")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_full_drift_analysis() -> Dict:
    """Run complete drift and anomaly detection pipeline"""
    logger.info("Starting drift detection pipeline")

    # Generate data
    reference = generate_reference_data(1000)
    windows = generate_production_windows(
        reference, n_windows=8, n_per_window=200
    )

    features = [
        "prompt_length",
        "latency_ms",
        "transaction_amount",
        "response_length"
    ]

    # Run drift analysis
    logger.info("Running drift analysis across 8 windows...")
    drift_results = run_drift_analysis(reference, windows, features)

    # Generate visualizations
    logger.info("Generating drift visualizations...")
    generate_drift_visualizations(
        reference, windows, drift_results, features
    )
    generate_anomaly_visualization(reference, windows)

    # Save results
    # Convert numpy types for JSON serialization
    def convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    def deep_convert(d):
        if isinstance(d, dict):
            return {k: deep_convert(v) for k, v in d.items()}
        if isinstance(d, list):
            return [deep_convert(i) for i in d]
        return convert(d)

    drift_results_clean = deep_convert(drift_results)

    with open("logs/drift_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "n_reference": len(reference),
            "n_windows": len(windows),
            "features_analyzed": features,
            "results": drift_results_clean
        }, f, indent=2)

    logger.info(
        f"Drift analysis complete. "
        f"Most drifted: {drift_results['summary']['most_drifted_feature']}"
    )
    logger.info(
        f"Features in critical: "
        f"{drift_results['summary']['features_in_critical']}"
    )

    return drift_results


if __name__ == "__main__":
    results = run_full_drift_analysis()
    print("\nDrift Analysis Summary:")
    print(f"Most drifted feature: "
          f"{results['summary']['most_drifted_feature']}")
    print(f"Max PSI: {results['summary']['max_psi']:.3f}")
    print(f"Critical features: "
          f"{results['summary']['features_in_critical']}")
    print(f"First critical window: "
          f"{results['summary']['first_critical_window']}")