"""
A/B Test Simulation: Baseline vs Optimized LLM Inference Server
Compares Model A (baseline: no caching, batch_size=1) vs
Model B (optimized: caching enabled, batch_size=8)

Statistical evaluation using:
- Two-sample t-test for latency
- Z-test for throughput
- Chi-square test for error rates
- Bootstrap confidence intervals
- Power analysis for sample size justification
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import ttest_ind, chi2_contingency, norm
import json
import os
import logging
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from datetime import datetime
from typing import Tuple, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

np.random.seed(42)
os.makedirs("visualizations", exist_ok=True)
os.makedirs("logs", exist_ok=True)


# ── Power Analysis ─────────────────────────────────────────────────────────────

def compute_sample_size(
    baseline_mean: float,
    baseline_std: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80
) -> int:
    """
    Compute required sample size per group using power analysis.
    Based on two-sample t-test formula.
    """
    effect_size = minimum_detectable_effect / baseline_std
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)
    n = ((z_alpha + z_beta) / effect_size) ** 2 * 2
    return int(np.ceil(n))


# ── Data Generation ───────────────────────────────────────────────────────────

def generate_variant_a(n: int) -> pd.DataFrame:
    """
    Variant A: Baseline server
    - No caching
    - Batch size = 1
    - Higher latency, lower throughput
    """
    # Latency: normally distributed around 420ms cold inference
    latency = np.random.normal(420, 45, n)
    latency = np.clip(latency, 100, 1200)

    # Throughput: around 2.1 req/s
    throughput = np.random.normal(2.1, 0.3, n)
    throughput = np.clip(throughput, 0.5, 5.0)

    # Error rate: ~2%
    errors = np.random.binomial(1, 0.02, n)

    # Cache hit rate: 0 (no caching)
    cache_hits = np.zeros(n)

    # Token generation time
    token_time = np.random.normal(8.4, 1.2, n)

    return pd.DataFrame({
        "variant": "A",
        "latency_ms": latency,
        "throughput_rps": throughput,
        "error": errors,
        "cache_hit": cache_hits,
        "token_time_ms": token_time,
        "request_id": range(n)
    })


def generate_variant_b(n: int) -> pd.DataFrame:
    """
    Variant B: Optimized server
    - Caching enabled (TTL=300s, max=1000)
    - Batch size = 8
    - Mixed latency: low for cache hits, similar for misses
    - Higher throughput due to batching
    """
    # 65% of requests are cache hits
    cache_hits = np.random.binomial(1, 0.65, n)

    latency = np.where(
        cache_hits == 1,
        # Cache hits: very fast
        np.random.normal(4.5, 1.8, n),
        # Cache misses: similar to baseline but batching helps
        np.random.normal(385, 40, n)
    )
    latency = np.clip(latency, 1.0, 1100)

    # Throughput: higher due to batching + caching
    throughput = np.random.normal(9.8, 1.4, n)
    throughput = np.clip(throughput, 1.0, 25.0)

    # Error rate: ~1.2% (slightly lower due to better queue management)
    errors = np.random.binomial(1, 0.012, n)

    # Token generation time (same model)
    token_time = np.random.normal(8.4, 1.2, n)

    return pd.DataFrame({
        "variant": "B",
        "latency_ms": latency,
        "throughput_rps": throughput,
        "error": errors,
        "cache_hit": cache_hits,
        "token_time_ms": token_time,
        "request_id": range(n)
    })


# ── Statistical Tests ─────────────────────────────────────────────────────────

def test_latency(
    a: pd.DataFrame,
    b: pd.DataFrame
) -> Dict:
    """Two-sample Welch t-test for latency difference"""
    t_stat, p_value = ttest_ind(
        a["latency_ms"],
        b["latency_ms"],
        equal_var=False  # Welch's t-test
    )

    # Effect size (Cohen's d)
    pooled_std = np.sqrt(
        (a["latency_ms"].std()**2 + b["latency_ms"].std()**2) / 2
    )
    cohens_d = (
        a["latency_ms"].mean() - b["latency_ms"].mean()
    ) / pooled_std

    # 95% confidence interval for difference in means
    diff = a["latency_ms"].mean() - b["latency_ms"].mean()
    se = np.sqrt(
        a["latency_ms"].var() / len(a) +
        b["latency_ms"].var() / len(b)
    )
    ci_lower = diff - 1.96 * se
    ci_upper = diff + 1.96 * se

    return {
        "metric": "latency_ms",
        "mean_a": round(a["latency_ms"].mean(), 2),
        "mean_b": round(b["latency_ms"].mean(), 2),
        "mean_diff": round(diff, 2),
        "pct_improvement": round(diff / a["latency_ms"].mean() * 100, 1),
        "t_statistic": round(t_stat, 4),
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
        "cohens_d": round(cohens_d, 3),
        "ci_95": [round(ci_lower, 2), round(ci_upper, 2)],
        "p50_a": round(np.percentile(a["latency_ms"], 50), 2),
        "p95_a": round(np.percentile(a["latency_ms"], 95), 2),
        "p99_a": round(np.percentile(a["latency_ms"], 99), 2),
        "p50_b": round(np.percentile(b["latency_ms"], 50), 2),
        "p95_b": round(np.percentile(b["latency_ms"], 95), 2),
        "p99_b": round(np.percentile(b["latency_ms"], 99), 2),
    }


def test_throughput(
    a: pd.DataFrame,
    b: pd.DataFrame
) -> Dict:
    """Two-sample t-test for throughput difference"""
    t_stat, p_value = ttest_ind(
        a["throughput_rps"],
        b["throughput_rps"],
        equal_var=False
    )

    diff = b["throughput_rps"].mean() - a["throughput_rps"].mean()
    se = np.sqrt(
        a["throughput_rps"].var() / len(a) +
        b["throughput_rps"].var() / len(b)
    )
    ci_lower = diff - 1.96 * se
    ci_upper = diff + 1.96 * se

    return {
        "metric": "throughput_rps",
        "mean_a": round(a["throughput_rps"].mean(), 3),
        "mean_b": round(b["throughput_rps"].mean(), 3),
        "improvement": round(diff, 3),
        "pct_improvement": round(
            diff / a["throughput_rps"].mean() * 100, 1
        ),
        "t_statistic": round(t_stat, 4),
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
        "ci_95": [round(ci_lower, 3), round(ci_upper, 3)]
    }


def test_error_rate(
    a: pd.DataFrame,
    b: pd.DataFrame
) -> Dict:
    """Chi-square test for error rate difference"""
    contingency = np.array([
        [a["error"].sum(), len(a) - a["error"].sum()],
        [b["error"].sum(), len(b) - b["error"].sum()]
    ])
    chi2, p_value, dof, _ = chi2_contingency(contingency)

    return {
        "metric": "error_rate",
        "error_rate_a": round(a["error"].mean() * 100, 3),
        "error_rate_b": round(b["error"].mean() * 100, 3),
        "chi2_statistic": round(chi2, 4),
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
        "dof": dof
    }


def bootstrap_ci(
    data_a: np.ndarray,
    data_b: np.ndarray,
    n_bootstrap: int = 5000,
    ci: float = 0.95
) -> Tuple[float, float]:
    """Bootstrap confidence interval for difference in means"""
    diffs = []
    for _ in range(n_bootstrap):
        sample_a = np.random.choice(data_a, size=len(data_a), replace=True)
        sample_b = np.random.choice(data_b, size=len(data_b), replace=True)
        diffs.append(sample_a.mean() - sample_b.mean())

    alpha = (1 - ci) / 2
    return (
        round(np.percentile(diffs, alpha * 100), 2),
        round(np.percentile(diffs, (1 - alpha) * 100), 2)
    )


# ── Visualization ─────────────────────────────────────────────────────────────

def generate_visualizations(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    results: Dict
) -> None:
    """Generate A/B test result visualizations"""

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle(
        "A/B Test Results: Baseline (A) vs Optimized (B) LLM Server\n"
        "kalam5 | IDS568 Final Project",
        fontsize=14, fontweight="bold"
    )

    # 1. Latency distributions
    ax = axes[0][0]
    ax.hist(df_a["latency_ms"], bins=50, alpha=0.6,
            color="#ef4444", label="A (Baseline)", density=True)
    ax.hist(df_b["latency_ms"], bins=50, alpha=0.6,
            color="#3b82f6", label="B (Optimized)", density=True)
    ax.axvline(df_a["latency_ms"].mean(), color="#ef4444",
               linestyle="--", linewidth=2)
    ax.axvline(df_b["latency_ms"].mean(), color="#3b82f6",
               linestyle="--", linewidth=2)
    ax.set_xlabel("Latency (ms)")
    ax.set_ylabel("Density")
    ax.set_title("Latency Distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Latency percentiles
    ax2 = axes[0][1]
    percentiles = [50, 75, 90, 95, 99]
    p_a = [np.percentile(df_a["latency_ms"], p) for p in percentiles]
    p_b = [np.percentile(df_b["latency_ms"], p) for p in percentiles]
    x = np.arange(len(percentiles))
    width = 0.35
    ax2.bar(x - width/2, p_a, width, label="A (Baseline)",
            color="#ef4444", alpha=0.85)
    ax2.bar(x + width/2, p_b, width, label="B (Optimized)",
            color="#3b82f6", alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"P{p}" for p in percentiles])
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("Latency Percentiles Comparison")
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis="y")

    # 3. Throughput distribution
    ax3 = axes[0][2]
    ax3.hist(df_a["throughput_rps"], bins=30, alpha=0.6,
             color="#ef4444", label="A (Baseline)", density=True)
    ax3.hist(df_b["throughput_rps"], bins=30, alpha=0.6,
             color="#3b82f6", label="B (Optimized)", density=True)
    ax3.axvline(df_a["throughput_rps"].mean(), color="#ef4444",
                linestyle="--", linewidth=2)
    ax3.axvline(df_b["throughput_rps"].mean(), color="#3b82f6",
                linestyle="--", linewidth=2)
    ax3.set_xlabel("Throughput (req/s)")
    ax3.set_ylabel("Density")
    ax3.set_title("Throughput Distribution")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Statistical significance
    ax4 = axes[1][0]
    metrics = ["Latency\nReduction", "Throughput\nIncrease", "Error Rate\nReduction"]
    improvements = [
        results["latency"]["pct_improvement"],
        results["throughput"]["pct_improvement"],
        round(
            (results["error_rate"]["error_rate_a"] -
             results["error_rate"]["error_rate_b"]) /
            results["error_rate"]["error_rate_a"] * 100, 1
        )
    ]
    colors = ["#10b981" if v > 0 else "#ef4444" for v in improvements]
    bars = ax4.bar(metrics, improvements, color=colors, alpha=0.85)
    ax4.axhline(y=0, color="black", linewidth=0.5)
    ax4.set_ylabel("% Improvement (B vs A)")
    ax4.set_title("Performance Improvements: B over A")
    for bar, val in zip(bars, improvements):
        ax4.text(
            bar.get_x() + bar.get_width()/2,
            bar.get_height() + 0.5,
            f"{val:.1f}%",
            ha="center", fontweight="bold"
        )
    ax4.grid(True, alpha=0.3, axis="y")

    # 5. Bootstrap CI
    ax5 = axes[1][1]
    boot_ci = bootstrap_ci(
        df_a["latency_ms"].values,
        df_b["latency_ms"].values
    )
    diff_mean = (
        df_a["latency_ms"].mean() - df_b["latency_ms"].mean()
    )
    ax5.barh(
        ["Latency Diff\n(A - B)"],
        [diff_mean],
        xerr=[[diff_mean - boot_ci[0]], [boot_ci[1] - diff_mean]],
        color="#10b981", alpha=0.85, capsize=8, height=0.4
    )
    ax5.axvline(x=0, color="#ef4444", linestyle="--", linewidth=1.5)
    ax5.set_xlabel("Latency Difference (ms)")
    ax5.set_title(f"Bootstrap 95% CI for Latency Reduction\n"
                  f"CI: [{boot_ci[0]:.1f}, {boot_ci[1]:.1f}]ms")
    ax5.grid(True, alpha=0.3)

    # 6. Summary table
    ax6 = axes[1][2]
    ax6.axis("off")
    table_data = [
        ["Metric", "Variant A", "Variant B", "p-value", "Sig."],
        [
            "Avg Latency",
            f"{results['latency']['mean_a']:.0f}ms",
            f"{results['latency']['mean_b']:.0f}ms",
            f"{results['latency']['p_value']:.4f}",
            "✓" if results['latency']['significant'] else "✗"
        ],
        [
            "P95 Latency",
            f"{results['latency']['p95_a']:.0f}ms",
            f"{results['latency']['p95_b']:.0f}ms",
            "—", "—"
        ],
        [
            "Throughput",
            f"{results['throughput']['mean_a']:.1f} rps",
            f"{results['throughput']['mean_b']:.1f} rps",
            f"{results['throughput']['p_value']:.4f}",
            "✓" if results['throughput']['significant'] else "✗"
        ],
        [
            "Error Rate",
            f"{results['error_rate']['error_rate_a']:.2f}%",
            f"{results['error_rate']['error_rate_b']:.2f}%",
            f"{results['error_rate']['p_value']:.4f}",
            "✓" if results['error_rate']['significant'] else "✗"
        ],
        [
            "Cache Hit Rate",
            "0%",
            "65%",
            "—", "—"
        ],
    ]
    table = ax6.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        loc="center",
        cellLoc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.8)
    ax6.set_title("Statistical Summary", fontweight="bold", pad=20)

    plt.tight_layout()
    path = "visualizations/ab_test_results.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"A/B test visualization saved to {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_simulation(n_per_variant: int = 500) -> Dict:
    """Run full A/B test simulation"""
    logger.info(f"Running A/B simulation with {n_per_variant} per variant")

    # Power analysis
    required_n = compute_sample_size(
        baseline_mean=420,
        baseline_std=45,
        minimum_detectable_effect=30,
        alpha=0.05,
        power=0.80
    )
    logger.info(f"Required sample size per group: {required_n}")

    # Generate data
    df_a = generate_variant_a(n_per_variant)
    df_b = generate_variant_b(n_per_variant)

    # Statistical tests
    latency_result = test_latency(df_a, df_b)
    throughput_result = test_throughput(df_a, df_b)
    error_result = test_error_rate(df_a, df_b)

    # Bootstrap CI
    boot_ci = bootstrap_ci(
        df_a["latency_ms"].values,
        df_b["latency_ms"].values
    )

    results = {
        "simulation_config": {
            "n_per_variant": n_per_variant,
            "required_sample_size": required_n,
            "alpha": 0.05,
            "power": 0.80,
            "mde_latency_ms": 30,
            "timestamp": datetime.now().isoformat()
        },
        "latency": latency_result,
        "throughput": throughput_result,
        "error_rate": error_result,
        "bootstrap_ci_latency_diff": {
            "lower": boot_ci[0],
            "upper": boot_ci[1],
            "interpretation": (
                "95% of bootstrap samples show A-B latency difference "
                f"between {boot_ci[0]:.1f}ms and {boot_ci[1]:.1f}ms"
            )
        },
        "recommendation": (
            "SHIP B"
            if (latency_result["significant"] and
                throughput_result["significant"])
            else "COLLECT MORE DATA"
        )
    }

    # Save results
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    with open("logs/ab_test_results.json", "w") as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)

    # Generate visualizations
    generate_visualizations(df_a, df_b, results)

    # Print summary
    logger.info("=" * 50)
    logger.info("A/B TEST RESULTS SUMMARY")
    logger.info("=" * 50)
    logger.info(
        f"Latency: A={latency_result['mean_a']:.0f}ms "
        f"B={latency_result['mean_b']:.0f}ms "
        f"({latency_result['pct_improvement']:.0f}% improvement) "
        f"p={latency_result['p_value']:.4f}"
    )
    logger.info(
        f"Throughput: A={throughput_result['mean_a']:.1f} "
        f"B={throughput_result['mean_b']:.1f} rps "
        f"({throughput_result['pct_improvement']:.0f}% improvement) "
        f"p={throughput_result['p_value']:.4f}"
    )
    logger.info(
        f"Error Rate: A={error_result['error_rate_a']:.2f}% "
        f"B={error_result['error_rate_b']:.2f}% "
        f"p={error_result['p_value']:.4f}"
    )
    logger.info(f"RECOMMENDATION: {results['recommendation']}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A/B test simulation for LLM inference server"
    )
    parser.add_argument(
        "--n", type=int, default=500,
        help="Number of requests per variant"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate script without running simulation"
    )
    args = parser.parse_args()

    if args.dry_run:
        print("✓ A/B simulation script validated")
    else:
        results = run_simulation(args.n)
        print(f"\nRecommendation: {results['recommendation']}")