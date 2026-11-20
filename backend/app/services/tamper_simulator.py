"""
MeterGuard AI: Tampering Simulator Service (Phase 3B)
Generates realistic 30-day daily consumption sequences across 6 operational scenarios
and evaluates them against the trained Daily LSTM Autoencoder without forcing results.
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.app.services.ml_engine import ml_engine


VALID_SCENARIOS = {
    "normal": "Normal Baseline Profile (~5.0 kWh/day with natural daily variance)",
    "sudden_drop": "Sudden Consumption Drop (55-65% abrupt reduction in second half of month)",
    "abnormally_low_night": "Abnormally Low Nighttime / Basal Suppression (Systematic baseline drop)",
    "flatline": "Flatline Consumption (~0.4 kWh/day nearly constant shunt/stuck meter)",
    "consumption_spike": "Consumption Spike (Severe surges exceeding 14.0 kWh/day)",
    "inversion": "Weekday/Weekend Inversion (Suppressed weekend, elevated weekday profile)",
}


class TamperSimulator:
    """
    Simulates realistic 30-day smart meter electricity consumption profiles.
    Strictly guarantees all values are finite, non-negative, and physically constrained.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def generate_sequence(self, scenario: str) -> List[float]:
        """
        Generates exactly 30 daily consumption values (in kWh) for the specified scenario.
        """
        if scenario not in VALID_SCENARIOS:
            raise ValueError(
                f"Unknown scenario '{scenario}'. Valid options: {list(VALID_SCENARIOS.keys())}"
            )

        days = np.arange(30)

        # Baseline: ~5.0 kWh/day with standard weekly rhythm (slight weekend elevation)
        # Weekends occur roughly at day 5, 6, 12, 13, 19, 20, 26, 27
        weekly_pattern = np.array([
            1.15 if (d % 7) in (5, 6) else 0.95 for d in range(30)
        ])
        noise = self.rng.normal(0.0, 0.25, size=30)
        base = 5.0 * weekly_pattern + noise
        base = np.clip(base, 2.5, 8.5)

        if scenario == "normal":
            tampered = base.copy()

        elif scenario == "sudden_drop":
            # Days 0-14: Normal baseline (~5.0 kWh)
            # Days 15-29: Abrupt 55-65% drop (retaining 35-45% of consumption)
            tampered = base.copy()
            drop_factor = self.rng.uniform(0.35, 0.45)  # 55-65% reduction
            tampered[15:] = tampered[15:] * drop_factor

        elif scenario == "abnormally_low_night":
            # Depressed off-peak/nighttime consumption profile.
            # Nighttime baseload typically accounts for ~35-45% of daily kWh.
            # In daily aggregation, systematic nighttime diversion manifests as a
            # sustained ~40% reduction in daily energy on alternate/working days.
            tampered = base.copy()
            # Suppress baseline on 18 out of 30 days
            suppression_mask = (days % 2 == 0) | (days % 3 == 0)
            tampered[suppression_mask] *= 0.55

        elif scenario == "flatline":
            # Meter shunt or stuck ADC: nearly constant low reading ~0.4 kWh/day
            stuck_level = self.rng.uniform(0.38, 0.42)
            micro_noise = self.rng.normal(0.0, 0.015, size=30)
            tampered = np.full(30, stuck_level) + micro_noise

        elif scenario == "consumption_spike":
            # Baseline consumption with several severe surges exceeding 14.0 kWh/day
            tampered = base.copy()
            # Select 4 to 6 random days for massive surges
            spike_days = self.rng.choice(np.arange(3, 28), size=self.rng.integers(4, 7), replace=False)
            tampered[spike_days] = self.rng.uniform(16.0, 24.0, size=len(spike_days))

        elif scenario == "inversion":
            # Inverted weekday/weekend profile:
            # Weekends suppressed to 40%, weekdays elevated by 35%
            tampered = np.zeros(30, dtype=np.float32)
            for d in range(30):
                if (d % 7) in (5, 6):
                    tampered[d] = base[d] * 0.40  # Suppressed weekend
                else:
                    tampered[d] = base[d] * 1.35  # Elevated weekday

        # Enforce non-negativity and finite constraints
        tampered = np.clip(tampered, 0.0, None)
        tampered = np.nan_to_num(tampered, nan=0.0, posinf=20.0, neginf=0.0)

        # Return rounded list of 30 floats
        return [round(float(val), 3) for val in tampered]

    def simulate_and_evaluate(self, meter_id: str, scenario: str) -> Dict[str, Any]:
        """
        Executes sequence generation and honest ML evaluation via the Daily LSTM Autoencoder.
        Does NOT force or fake detection results.
        """
        consumption = self.generate_sequence(scenario)

        # Pass strictly through the verified Daily LSTM Autoencoder
        lstm_result = ml_engine.predict_sequence("daily", consumption, meter_id=meter_id)

        arr = np.array(consumption)
        stats = {
            "min_kwh": round(float(np.min(arr)), 3),
            "max_kwh": round(float(np.max(arr)), 3),
            "mean_kwh": round(float(np.mean(arr)), 3),
            "std_kwh": round(float(np.std(arr)), 3),
            "drop_percentage": round(float((1.0 - (np.mean(arr[15:]) / (np.mean(arr[:15]) + 1e-6))) * 100), 1)
            if scenario == "sudden_drop" else None,
        }

        return {
            "meter_id": meter_id,
            "scenario": scenario,
            "scenario_name": VALID_SCENARIOS.get(scenario, scenario),
            "is_simulated": True,
            "simulated_at": datetime.utcnow().isoformat(),
            "sequence_length": len(consumption),
            "consumption": consumption,
            "stats": stats,
            "lstm_result": lstm_result,
        }


# Global singleton instance
tamper_simulator = TamperSimulator()
