"""
MeterGuard AI: Hardware Dataset Replay Simulator
Streams recorded sensor readings from data/hardware_dataset.csv to the
MeterGuard AI backend (POST /api/meter-data) to demonstrate real-time
telemetry, ML inference, and dashboard reactivity without an ESP32 hardware rig.
"""

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

# Resolve default paths relative to repository root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_DATASET = PROJECT_ROOT / "data" / "hardware_dataset.csv"
DEFAULT_API_URL = "http://localhost:5000/api/meter-data"


def parse_args():
    parser = argparse.ArgumentParser(
        description="MeterGuard AI: Hardware Dataset Replay Simulator"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(DEFAULT_DATASET),
        help=f"Path to dataset CSV (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=DEFAULT_API_URL,
        help=f"Backend ingestion URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between successive readings (default: 1.0)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Continuously loop dataset replay until stopped",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to replay the dataset (default: 1; ignored if --loop is set)",
    )
    parser.add_argument(
        "--meter-id",
        type=str,
        default="M001",
        help="Meter ID to send telemetry for (default: M001)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of readings to send per iteration (default: all)",
    )
    return parser.parse_args()


def load_dataset(dataset_path: str) -> pd.DataFrame:
    path = Path(dataset_path)
    if not path.is_file():
        print(f"[ERROR] Dataset file not found at: {path}")
        sys.exit(1)

    df = pd.read_csv(path)
    required_cols = ["T1_CS", "T1_VS", "T2_CS", "T2_VS", "H1_CS", "H1_VS"]
    for col in required_cols:
        if col not in df.columns:
            print(f"[ERROR] Required column '{col}' missing from {path}")
            sys.exit(1)

    print(f"[INFO] Loaded {len(df)} readings from {path.name}")
    return df


def replay_iteration(df: pd.DataFrame, api_url: str, meter_id: str, delay: float, iteration: int, limit: int = None):
    slice_df = df.iloc[:limit] if limit is not None else df
    total = len(slice_df)
    print(f"\n--- Starting Replay Iteration {iteration} ({total} readings, delay={delay}s) ---")

    for idx, (_, row) in enumerate(slice_df.iterrows()):
        payload = {
            "meter_id": meter_id,
            "time_ms": int(row.get("time_ms", int(time.time() * 1000))),
            "T1_CS": float(row["T1_CS"]),
            "T1_VS": float(row["T1_VS"]),
            "T2_CS": float(row["T2_CS"]),
            "T2_VS": float(row["T2_VS"]),
            "H1_CS": float(row["H1_CS"]),
            "H1_VS": float(row["H1_VS"]),
        }
        ground_truth = row.get("label", "unknown")

        try:
            response = requests.post(api_url, json=payload, timeout=5)
            if response.status_code == 200:
                res_data = response.json()
                decision = res_data.get("decision", {})
                final_status = decision.get("final_status", "N/A")
                priority = decision.get("priority", "N/A")
                m1_pred = res_data.get("model1", {}).get("prediction", "N/A")
                m2_pred = res_data.get("model2", {}).get("prediction", "N/A")

                print(
                    f"[{idx + 1:03d}/{total:03d}] "
                    f"time_ms={payload['time_ms']:<6} | "
                    f"Truth: {ground_truth:<9} | "
                    f"M1: {m1_pred:<10} | M2: {m2_pred:<10} | "
                    f"Status: {final_status} ({priority})"
                )
            else:
                print(
                    f"[{idx + 1:03d}/{total:03d}] Server returned HTTP {response.status_code}: {response.text[:100]}"
                )
        except requests.exceptions.RequestException as exc:
            print(
                f"[{idx + 1:03d}/{total:03d}] Connection error to {api_url}: {exc}"
            )
            print("[HINT] Ensure the backend server is running: python backend/app.py")

        if delay > 0:
            time.sleep(delay)


def main():
    args = parse_args()
    print("==========================================================")
    print("      MeterGuard AI: Hardware Telemetry Replay Simulator  ")
    print("==========================================================")
    print(f"Target API   : {args.api_url}")
    print(f"Meter ID     : {args.meter_id}")
    print(f"Dataset      : {args.dataset}")
    print(f"Delay        : {args.delay}s per reading")
    print(f"Loop Mode    : {'Continuous' if args.loop else f'{args.repeat} repetition(s)'}")
    print("Press Ctrl+C to abort at any time.\n")

    df = load_dataset(args.dataset)

    iteration = 1
    try:
        if args.loop:
            while True:
                replay_iteration(df, args.api_url, args.meter_id, args.delay, iteration, args.limit)
                iteration += 1
        else:
            for it in range(1, args.repeat + 1):
                replay_iteration(df, args.api_url, args.meter_id, args.delay, it, args.limit)

        print("\n[INFO] Replay completed successfully.")
    except KeyboardInterrupt:
        print("\n[INFO] Simulation interrupted by user. Exiting cleanly.")
        sys.exit(0)


if __name__ == "__main__":
    main()
