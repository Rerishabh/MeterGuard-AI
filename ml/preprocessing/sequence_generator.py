"""
MeterGuard AI: Sequence Generator Module
Converts long-format smart meter tables into 3D sequential arrays (samples, timesteps, 1).
Splits meters by profile group to strictly prevent data leakage across train, val, and test splits.
"""

from typing import Dict, Tuple
import numpy as np
import pandas as pd


def prepare_sequences(
    df: pd.DataFrame,
    dataset_type: str = "daily",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """
    Splits by meter_id into train, val, test splits.
    Train split receives only normal sequences for unsupervised autoencoder training.
    Returns:
        dict with keys 'train', 'val', 'test', each containing:
            (X, y_labels, metadata_dict)
            X shape: (N, timesteps, 1)
            y_labels: 0 or 1
    """
    timesteps = 30 if dataset_type == "daily" else 24
    rng = np.random.default_rng(seed)

    all_meters = np.array(sorted(df["meter_id"].unique()))
    n_total = len(all_meters)
    n_test = max(1, int(n_total * 0.20))
    n_val = max(1, int(n_total * val_ratio))

    # Stratified selection: ensure test meters contain balanced representation of all anomaly scenarios
    seqs_summary = df.groupby("sequence_id").first()
    meter_anom_counts = seqs_summary.groupby(["meter_id", "anomaly_type"]).size().unstack(fill_value=0)
    anom_cols = [c for c in ["sudden_drop", "abnormally_low_night", "flatline", "consumption_spike", "inversion"] if c in meter_anom_counts.columns]

    best_test_meters = None
    best_min = -1
    for _ in range(500):
        candidate = rng.choice(all_meters, n_test, replace=False)
        sums = meter_anom_counts.loc[candidate, anom_cols].sum() if anom_cols else pd.Series([1])
        cur_min = sums.min()
        if cur_min > best_min:
            best_min = cur_min
            best_test_meters = candidate

    test_meters = set(best_test_meters if best_test_meters is not None else all_meters[-n_test:])
    remaining_meters = [m for m in all_meters if m not in test_meters]
    val_meters = set(remaining_meters[:n_val])
    train_meters = set(remaining_meters[n_val:])


    # Extract sequences by grouping on sequence_id
    grouped = df.groupby("sequence_id")
    seq_records = []

    for seq_id, group in grouped:
        if len(group) != timesteps:
            continue
        group_sorted = group.sort_values("timestep")
        meter_id = group_sorted["meter_id"].iloc[0]
        is_anomaly = int(group_sorted["is_anomaly"].iloc[0])
        anomaly_type = group_sorted["anomaly_type"].iloc[0]
        profile_id = group_sorted["profile_id"].iloc[0]
        values = group_sorted["consumption"].to_numpy(dtype=np.float32)

        split = "train" if meter_id in train_meters else ("val" if meter_id in val_meters else "test")

        seq_records.append({
            "sequence_id": seq_id,
            "meter_id": meter_id,
            "profile_id": profile_id,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "split": split,
            "values": values,
        })

    seq_df = pd.DataFrame(seq_records)

    # 1. Train Split: Strictly Normal Sequences only!
    train_df = seq_df[(seq_df["split"] == "train") & (seq_df["is_anomaly"] == 0)]
    X_train = np.stack(train_df["values"].to_numpy())[..., np.newaxis]
    y_train = train_df["is_anomaly"].to_numpy()

    # 2. Val Split: Normal sequences for early stopping + validation anomalies
    val_df = seq_df[seq_df["split"] == "val"]
    X_val = np.stack(val_df["values"].to_numpy())[..., np.newaxis]
    y_val = val_df["is_anomaly"].to_numpy()

    # 3. Test Split: Held-out meters with full spectrum of normal & anomalies
    test_df = seq_df[seq_df["split"] == "test"]
    X_test = np.stack(test_df["values"].to_numpy())[..., np.newaxis]
    y_test = test_df["is_anomaly"].to_numpy()

    return {
        "train": (X_train, y_train, train_df[["sequence_id", "meter_id", "anomaly_type"]].to_dict(orient="records")),
        "val": (X_val, y_val, val_df[["sequence_id", "meter_id", "anomaly_type"]].to_dict(orient="records")),
        "test": (X_test, y_test, test_df[["sequence_id", "meter_id", "anomaly_type"]].to_dict(orient="records")),
    }
