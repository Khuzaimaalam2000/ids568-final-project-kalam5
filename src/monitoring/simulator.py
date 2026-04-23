"""
Traffic simulator for populating monitoring metrics
Generates realistic synthetic traffic patterns including:
- Normal traffic
- High load spikes
- Cache warming patterns
- Error injection
- Drift simulation
"""

import time
import random
import logging
import json
import os
import math
from datetime import datetime
from typing import List, Dict
from src.monitoring.instrumentation import get_collector

logger = logging.getLogger(__name__)

# ── Prompt Templates ──────────────────────────────────────────────────────────

SHORT_PROMPTS = [
    "What is AI",
    "Define ML",
    "Explain NLP",
    "What is GPT",
    "Define neural network",
]

MEDIUM_PROMPTS = [
    "Explain how transformer architecture works in deep learning",
    "What are the main differences between supervised and unsupervised learning",
    "Describe the attention mechanism and why it matters for language models",
    "What is transfer learning and when should you use it",
    "Explain the concept of embeddings in natural language processing",
]

LONG_PROMPTS = [
    "Provide a detailed explanation of how large language models are trained "
    "including pretraining objectives, fine-tuning strategies, and RLHF",
    "Explain the complete pipeline from raw text data to a deployed language "
    "model including tokenization, model architecture, training, and serving",
    "Describe in detail the differences between GPT, BERT, T5, and other "
    "transformer variants including their architectures and use cases",
]

REPEATED_PROMPTS = [
    "What is machine learning",
    "Explain artificial intelligence",
    "What is deep learning",
]


class TrafficSimulator:
    """
    Simulates realistic LLM inference traffic for monitoring.
    Records all metrics via MetricsCollector.
    """

    def __init__(self):
        self.collector = get_collector()
        self.results = []

    def _simulate_request(
        self,
        prompt: str,
        force_cache: bool = False,
        force_error: bool = False,
        base_latency_ms: float = 400.0
    ) -> Dict:
        """Simulate a single inference request"""
        start = self.collector.record_request_start()
        prompt_len = len(prompt.split())

        # Simulate processing time
        if force_error:
            time.sleep(0.01)
            self.collector.record_error("inference_error")
            return {"success": False, "error": True}

        # Determine if cached
        is_cached = force_cache or (prompt in REPEATED_PROMPTS and
                                    random.random() < 0.85)

        if is_cached:
            # Cache hit — very fast
            latency_s = random.uniform(0.001, 0.008)
        else:
            # Cold inference — simulate model latency
            latency_variation = random.uniform(0.85, 1.15)
            latency_s = (base_latency_ms * latency_variation) / 1000.0

        time.sleep(latency_s)

        response_len = random.randint(10, 60)

        self.collector.record_request_end(
            start_time=start,
            endpoint="/infer",
            status="success",
            was_cached=is_cached,
            prompt_length=prompt_len,
            response_length=response_len
        )

        if not is_cached:
            self.collector.record_inference_time(latency_s)

        self.collector.update_system_metrics()

        return {
            "success": True,
            "cached": is_cached,
            "latency_ms": latency_s * 1000,
            "prompt_length": prompt_len,
            "response_length": response_len
        }

    def run_normal_traffic(
        self,
        n_requests: int = 50,
        repeat_ratio: float = 0.4
    ) -> List[Dict]:
        """Simulate normal mixed traffic"""
        logger.info(f"Running normal traffic: {n_requests} requests")
        results = []

        # Set reference distribution first
        ref_lengths = [len(p.split()) for p in
                       MEDIUM_PROMPTS * 10 + SHORT_PROMPTS * 5]
        self.collector.set_reference_distribution(ref_lengths)

        all_prompts = SHORT_PROMPTS + MEDIUM_PROMPTS + LONG_PROMPTS
        repeated = REPEATED_PROMPTS

        for i in range(n_requests):
            if random.random() < repeat_ratio:
                prompt = random.choice(repeated)
            else:
                prompt = random.choice(all_prompts)

            result = self._simulate_request(prompt)
            results.append(result)

            # Small delay between requests
            time.sleep(random.uniform(0.01, 0.05))

        self.results.extend(results)
        logger.info(f"Normal traffic complete: {len(results)} requests")
        return results

    def run_high_load_spike(
        self,
        n_requests: int = 30,
        concurrency: int = 5
    ) -> List[Dict]:
        """Simulate a high-load traffic spike"""
        logger.info(f"Running load spike: {n_requests} requests")
        results = []

        for i in range(n_requests):
            prompt = random.choice(MEDIUM_PROMPTS + SHORT_PROMPTS)
            # Faster requests during spike
            result = self._simulate_request(
                prompt,
                base_latency_ms=300.0
            )
            results.append(result)
            self.collector.update_queue_size(
                max(0, concurrency - (i % concurrency))
            )
            time.sleep(0.005)

        self.results.extend(results)
        logger.info(f"Load spike complete")
        return results

    def run_cache_warming(self, n_requests: int = 20) -> List[Dict]:
        """Simulate cache warming with repeated prompts"""
        logger.info(f"Running cache warming: {n_requests} requests")
        results = []

        for i in range(n_requests):
            prompt = random.choice(REPEATED_PROMPTS)
            result = self._simulate_request(
                prompt,
                force_cache=(i > 5)
            )
            results.append(result)
            self.collector.update_cache_stats(min(i + 1, 50))
            time.sleep(0.02)

        self.results.extend(results)
        return results

    def run_error_injection(self, n_requests: int = 10) -> List[Dict]:
        """Simulate requests with injected errors"""
        logger.info(f"Running error injection: {n_requests} requests")
        results = []

        for i in range(n_requests):
            # 30% error rate during injection
            force_error = random.random() < 0.3
            prompt = random.choice(MEDIUM_PROMPTS)
            result = self._simulate_request(
                prompt,
                force_error=force_error
            )
            results.append(result)
            time.sleep(0.02)

        self.results.extend(results)
        return results

    def run_drift_simulation(self, n_requests: int = 30) -> List[Dict]:
        """
        Simulate input distribution drift.
        Gradually shifts from medium to very long prompts.
        """
        logger.info(f"Running drift simulation: {n_requests} requests")
        results = []

        for i in range(n_requests):
            # Progressively use longer prompts to induce drift
            drift_factor = i / n_requests
            if drift_factor < 0.3:
                prompt = random.choice(SHORT_PROMPTS)
            elif drift_factor < 0.6:
                prompt = random.choice(MEDIUM_PROMPTS)
            else:
                prompt = random.choice(LONG_PROMPTS)

            result = self._simulate_request(prompt, base_latency_ms=500.0)
            results.append(result)

            # Check drift every 10 requests
            if i % 10 == 9:
                drift = self.collector.check_drift()
                if drift:
                    logger.info(f"Drift check at request {i}: {drift}")

            time.sleep(0.03)

        self.results.extend(results)
        return results

    def run_full_simulation(self) -> Dict:
        """Run complete simulation suite"""
        logger.info("=" * 50)
        logger.info("Starting full traffic simulation")
        logger.info("=" * 50)

        start = time.time()
        all_results = {}

        # Phase 1: Normal traffic
        logger.info("Phase 1: Normal traffic")
        all_results["normal"] = self.run_normal_traffic(40, repeat_ratio=0.4)

        # Phase 2: Cache warming
        logger.info("Phase 2: Cache warming")
        all_results["cache_warm"] = self.run_cache_warming(15)

        # Phase 3: High load spike
        logger.info("Phase 3: Load spike")
        all_results["spike"] = self.run_high_load_spike(20)

        # Phase 4: Error injection
        logger.info("Phase 4: Error injection")
        all_results["errors"] = self.run_error_injection(8)

        # Phase 5: Drift simulation
        logger.info("Phase 5: Drift simulation")
        all_results["drift"] = self.run_drift_simulation(25)

        total_time = time.time() - start
        summary = self.collector.get_summary()
        summary["simulation_duration_s"] = round(total_time, 2)
        summary["total_simulated"] = len(self.results)

        # Save results
        os.makedirs("logs", exist_ok=True)
        with open("logs/simulation_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": summary,
                "phases": {
                    k: len(v) for k, v in all_results.items()
                }
            }, f, indent=2)

        logger.info(f"Simulation complete in {total_time:.1f}s")
        logger.info(f"Summary: {summary}")

        return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    sim = TrafficSimulator()
    summary = sim.run_full_simulation()
    print("\nSimulation Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")