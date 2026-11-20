"""
MeterGuard AI: Synthetic Smart-Meter Data Generator
Generates realistic electricity consumption profiles and 5 controlled tampering/anomaly scenarios:
1. Sudden Consumption Drop (40-70% reduction)
2. Abnormally Low Nighttime Usage
3. Flatline Consumption (stuck meter / fixed shunt)
4. Consumption Spikes (unusual surging)
5. Weekday/Weekend Pattern Inversion

Produces separate Daily (30 timesteps) and Hourly (24 timesteps) datasets.
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Default paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_DIR = SCRIPT_DIR / "synthetic"
RAW_DIR = SCRIPT_DIR / "raw"


def parse_args():
    parser = argparse.ArgumentParser(
        description="MeterGuard AI: Synthetic Smart-Meter Data Generator"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help=f"Directory to save generated CSVs (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--num-meters",
        type=int,
        default=50,
        help="Number of distinct smart meter profiles to generate (default: 50)",
    )
    parser.add_argument(
        "--daily-samples-per-meter",
        type=int,
        default=20,
        help="Number of 30-day sequences per meter (default: 20)",
    )
    parser.add_argument(
        "--hourly-samples-per-meter",
        type=int,
        default=25,
        help="Number of 24-hour sequences per meter (default: 25)",
    )
    parser.add_argument(
        "--anomaly-ratio",
        type=float,
        default=0.20,
        help="Proportion of sequences to inject with anomalies (default: 0.20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    return parser.parse_args()


# =====================================================================
# 1. BASE PROFILE DEFINITIONS
# =====================================================================

PROFILE_TEMPLATES = [
    {"type": "low_residential", "base_daily": 4.5, "base_hourly_peak": 0.45, "base_hourly_night": 0.08},
    {"type": "medium_residential", "base_daily": 9.0, "base_hourly_peak": 0.90, "base_hourly_night": 0.15},
    {"type": "high_residential", "base_daily": 16.0, "base_hourly_peak": 1.60, "base_hourly_night": 0.30},
    {"type": "solar_residential", "base_daily": 7.0, "base_hourly_peak": 0.70, "base_hourly_night": 0.18},
    {"type": "commercial_light", "base_daily": 22.0, "base_hourly_peak": 2.20, "base_hourly_night": 0.40},
]

ANOMALY_TYPES = [
    "sudden_drop",
    "abnormally_low_night",
    "flatline",
    "consumption_spike",
    "inversion",
]


# =====================================================================
# 2. ANOMALY INJECTION LOGIC
# =====================================================================

def inject_daily_anomaly(sequence: np.ndarray, anomaly_type: str, rng: np.random.Generator) -> np.ndarray:
    """Inject one of the 5 anomaly patterns into a 30-day consumption array."""
    tampered = sequence.copy()
    length = len(sequence)

    if anomaly_type == "sudden_drop":
        # Drop 40% to 70% from day 10 onward
        drop_factor = rng.uniform(0.30, 0.60)
        start_idx = rng.integers(5, 15)
        tampered[start_idx:] *= drop_factor

    elif anomaly_type == "abnormally_low_night":
        # For daily, simulate systematic baseline degradation across alternate days
        drop_factor = rng.uniform(0.35, 0.55)
        tampered[::2] *= drop_factor

    elif anomaly_type == "flatline":
        # Meter freezes or stuck on fixed constant reading
        start_idx = rng.integers(5, 12)
        flat_val = float(np.mean(tampered[:start_idx])) * rng.uniform(0.15, 0.35)
        tampered[start_idx:] = flat_val + rng.normal(0, 0.02 * flat_val, length - start_idx)

    elif anomaly_type == "consumption_spike":
        # Sudden massive surge of 2.5x to 4x on multiple days
        spike_indices = rng.choice(np.arange(length), size=rng.integers(2, 5), replace=False)
        tampered[spike_indices] *= rng.uniform(2.5, 4.0)

    elif anomaly_type == "inversion":
        # Reverse weekday/weekend pattern: weekday consumption suppressed, weekend elevated
        # Days 5,6, 12,13, 19,20, 26,27 are weekends
        for day in range(length):
            if (day % 7) in [5, 6]:
                tampered[day] *= 0.40  # Weekend suppressed
            else:
                tampered[day] *= 1.35  # Weekday elevated

    # Physical constraint: consumption cannot be negative
    return np.clip(tampered, 0.0, None)


def inject_hourly_anomaly(sequence: np.ndarray, anomaly_type: str, rng: np.random.Generator) -> np.ndarray:
    """Inject one of the 5 anomaly patterns into a 24-hour consumption array."""
    tampered = sequence.copy()

    if anomaly_type == "sudden_drop":
        # Abrupt drop during peak evening hours (hours 17 to 23)
        drop_factor = rng.uniform(0.25, 0.50)
        tampered[17:] *= drop_factor

    elif anomaly_type == "abnormally_low_night":
        # Nighttime (hours 0 to 6) dropped close to 0
        tampered[0:6] = rng.uniform(0.005, 0.02, size=6)

    elif anomaly_type == "flatline":
        # Meter stuck on constant shunt value all day
        flat_val = float(np.mean(sequence)) * rng.uniform(0.20, 0.40)
        tampered[:] = flat_val + rng.normal(0, 0.005, size=24)

    elif anomaly_type == "consumption_spike":
        # Huge spike during unusual late-night hours (e.g. 2-4 AM)
        spike_hour = rng.integers(1, 5)
        tampered[spike_hour:spike_hour + 2] *= rng.uniform(3.5, 6.0)

    elif anomaly_type == "inversion":
        # Inverted daily curve: peak during night, trough during day
        tampered = np.roll(tampered, 12)

    return np.clip(tampered, 0.0, None)


# =====================================================================
# 3. SYNTHETIC GENERATORS
# =====================================================================

def generate_daily_dataset(num_meters: int, samples_per_meter: int, anomaly_ratio: float, seed: int):
    rng = np.random.default_rng(seed)
    records = []

    print(f"[INFO] Generating Daily Dataset: {num_meters} meters x {samples_per_meter} sequences = {num_meters * samples_per_meter} sequences...")

    for m_idx in range(num_meters):
        meter_id = f"M{m_idx + 1:04d}"
        tpl = PROFILE_TEMPLATES[m_idx % len(PROFILE_TEMPLATES)]
        base_kwh = tpl["base_daily"] * rng.uniform(0.85, 1.15)
        profile_id = f"{tpl['type']}_{m_idx % 5:02d}"

        for s_idx in range(samples_per_meter):
            # Generate 30 days
            sequence = np.zeros(30, dtype=np.float64)
            trend_slope = rng.uniform(-0.015, 0.015)

            for d in range(30):
                is_weekend = (d % 7) in [5, 6]
                day_factor = 1.25 if is_weekend else 0.95
                noise = rng.normal(0, base_kwh * 0.08)
                drift = trend_slope * d
                val = base_kwh * day_factor + noise + drift
                sequence[d] = max(0.2, val)

            # Determine whether this sample is anomalous
            is_anomaly = 1 if (rng.uniform(0, 1) < anomaly_ratio) else 0
            if is_anomaly:
                chosen_anomaly = str(rng.choice(ANOMALY_TYPES))
                sequence = inject_daily_anomaly(sequence, chosen_anomaly, rng)
            else:
                chosen_anomaly = "normal"

            seq_id = f"{meter_id}_D{s_idx + 1:03d}"
            for step in range(30):
                records.append({
                    "sequence_id": seq_id,
                    "meter_id": meter_id,
                    "profile_id": profile_id,
                    "dataset_type": "daily",
                    "timestep": step + 1,
                    "consumption": round(float(sequence[step]), 4),
                    "is_anomaly": is_anomaly,
                    "anomaly_type": chosen_anomaly,
                })

    df = pd.DataFrame(records)
    return df


def generate_hourly_dataset(num_meters: int, samples_per_meter: int, anomaly_ratio: float, seed: int):
    rng = np.random.default_rng(seed + 100)
    records = []

    print(f"[INFO] Generating Hourly Dataset: {num_meters} meters x {samples_per_meter} sequences = {num_meters * samples_per_meter} sequences...")

    # Standard residential hourly usage profile curve (sum normalized)
    # Peak at 8-9 AM and 7-9 PM; trough at 2-5 AM
    diurnal_curve = np.array([
        0.02, 0.015, 0.01, 0.01, 0.015, 0.03,  # 00 - 05
        0.05, 0.07, 0.08, 0.06, 0.045, 0.04,   # 06 - 11
        0.04, 0.04, 0.045, 0.05, 0.065, 0.08,  # 12 - 17
        0.09, 0.085, 0.06, 0.045, 0.03, 0.025  # 18 - 23
    ])
    diurnal_curve = diurnal_curve / diurnal_curve.sum()

    for m_idx in range(num_meters):
        meter_id = f"M{m_idx + 1:04d}"
        tpl = PROFILE_TEMPLATES[m_idx % len(PROFILE_TEMPLATES)]
        daily_kwh = tpl["base_daily"] * rng.uniform(0.85, 1.15)
        profile_id = f"{tpl['type']}_{m_idx % 5:02d}"

        for s_idx in range(samples_per_meter):
            # Base 24 hours
            noise = rng.normal(0, 0.015 * daily_kwh, size=24)
            sequence = daily_kwh * diurnal_curve + noise
            sequence = np.clip(sequence, 0.01, None)

            is_anomaly = 1 if (rng.uniform(0, 1) < anomaly_ratio) else 0
            if is_anomaly:
                chosen_anomaly = str(rng.choice(ANOMALY_TYPES))
                sequence = inject_hourly_anomaly(sequence, chosen_anomaly, rng)
            else:
                chosen_anomaly = "normal"

            seq_id = f"{meter_id}_H{s_idx + 1:03d}"
            for step in range(24):
                records.append({
                    "sequence_id": seq_id,
                    "meter_id": meter_id,
                    "profile_id": profile_id,
                    "dataset_type": "hourly",
                    "timestep": step,
                    "consumption": round(float(sequence[step]), 4),
                    "is_anomaly": is_anomaly,
                    "anomaly_type": chosen_anomaly,
                })

    df = pd.DataFrame(records)
    return df


# =====================================================================
# 4. OPTIONAL SGCC DATASET LOADER
# =====================================================================

def load_sgcc_raw(raw_path: Path = None):
    """
    Safely inspect and parse SGCC smart meter dataset if manually placed in ml/dataset/raw/.
    Does not require external download; handles missing files gracefully.
    """
    if raw_path is None:
        raw_path = RAW_DIR / "sgcc_data.csv"

    if not raw_path.is_file():
        return None, f"SGCC raw dataset not found at {raw_path}. Using synthetic data pipeline."

    try:
        df = pd.read_csv(raw_path, nrows=50)
        return df, f"SGCC dataset found with {df.shape[1]} columns. Schema detected: {list(df.columns[:5])}..."
    except Exception as exc:
        return None, f"Error inspecting SGCC file: {exc}"


# =====================================================================
# 5. MAIN EXECUTION
# =====================================================================

def main():
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================================")
    print("      MeterGuard AI: Synthetic Dataset Generator (Phase 2)        ")
    print("==================================================================")
    print(f"Random Seed        : {args.seed}")
    print(f"Number of Meters   : {args.num_meters}")
    print(f"Anomaly Ratio      : {args.anomaly_ratio * 100:.1f}%")
    print(f"Output Directory   : {out_dir}\n")

    # Generate Daily Dataset
    daily_df = generate_daily_dataset(
        num_meters=args.num_meters,
        samples_per_meter=args.daily_samples_per_meter,
        anomaly_ratio=args.anomaly_ratio,
        seed=args.seed,
    )
    daily_path = out_dir / "synthetic_daily_consumption.csv"
    daily_df.to_csv(daily_path, index=False)

    daily_seq_count = daily_df["sequence_id"].nunique()
    daily_anomaly_count = daily_df[daily_df["timestep"] == 1]["is_anomaly"].sum()
    print(f"[SUCCESS] Saved Daily Dataset: {len(daily_df)} rows | {daily_seq_count} sequences ({daily_seq_count - daily_anomaly_count} normal, {daily_anomaly_count} anomalous) -> {daily_path.name}")

    # Generate Hourly Dataset
    hourly_df = generate_hourly_dataset(
        num_meters=args.num_meters,
        samples_per_meter=args.hourly_samples_per_meter,
        anomaly_ratio=args.anomaly_ratio,
        seed=args.seed,
    )
    hourly_path = out_dir / "synthetic_hourly_consumption.csv"
    hourly_df.to_csv(hourly_path, index=False)

    hourly_seq_count = hourly_df["sequence_id"].nunique()
    hourly_anomaly_count = hourly_df[hourly_df["timestep"] == 0]["is_anomaly"].sum()
    print(f"[SUCCESS] Saved Hourly Dataset: {len(hourly_df)} rows | {hourly_seq_count} sequences ({hourly_seq_count - hourly_anomaly_count} normal, {hourly_anomaly_count} anomalous) -> {hourly_path.name}")

    # Check optional SGCC
    _, msg = load_sgcc_raw()
    print(f"[INFO] SGCC Check: {msg}")

    print("\n[COMPLETE] Synthetic datasets generated successfully.")


if __name__ == "__main__":
    main()
