"""
MeterGuard AI: LSTM Autoencoder Training Pipeline
Trains Daily (30-step) and Hourly (24-step) LSTM Autoencoders exclusively on normal sequences.
Computes reconstruction MSE on validation data and determines 95th/99th percentile anomaly thresholds.
Saves model (.keras), scaler (.pkl), and threshold metadata (.json) to ml/artifacts/.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

# Resolve project paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "ml"))

from preprocessing.data_loader import load_dataset
from preprocessing.preprocessing import SequenceScaler
from preprocessing.sequence_generator import prepare_sequences
from models.lstm_autoencoder import build_lstm_autoencoder

ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"
RESULTS_DIR = PROJECT_ROOT / "ml" / "evaluation" / "results"


def parse_args():
    parser = argparse.ArgumentParser(description="MeterGuard AI: Train LSTM Autoencoder")
    parser.add_argument(
        "--model-type",
        type=str,
        default="both",
        choices=["daily", "hourly", "both"],
        help="Model experiment to train (default: both)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=35,
        help="Maximum training epochs (default: 35)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size (default: 32)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.001,
        help="Adam learning rate (default: 0.001)",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=5,
        help="Early stopping patience (default: 5)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    return parser.parse_args()


def set_reproducibility(seed: int = 42):
    np.random.seed(seed)
    tf.random.set_seed(seed)


def train_single_experiment(dataset_type: str, epochs: int, batch_size: int, learning_rate: float, patience: int, seed: int):
    print(f"\n==================================================================")
    print(f"   TRAINING LSTM AUTOENCODER: {dataset_type.upper()} EXPERIMENT   ")
    print(f"==================================================================")
    timesteps = 30 if dataset_type == "daily" else 24

    # 1. Load Data & Prepare Sequences
    print(f"[1/6] Loading {dataset_type} dataset and generating sequences...")
    df = load_dataset(dataset_type)
    splits = prepare_sequences(df, dataset_type=dataset_type, seed=seed)

    X_train, y_train, _ = splits["train"]
    X_val, y_val, _ = splits["val"]
    X_test, y_test, _ = splits["test"]

    # Filter val to normal sequences only for reconstruction evaluation & thresholding
    val_normal_mask = (y_val == 0)
    X_val_normal = X_val[val_normal_mask]

    print(f"      Train Normal Samples      : {len(X_train)} sequences of shape ({timesteps}, 1)")
    print(f"      Val Normal Samples        : {len(X_val_normal)} sequences (total val: {len(X_val)})")
    print(f"      Test Samples (Held-out)   : {len(X_test)} sequences (anomalies: {sum(y_test)})")

    # 2. Fit Scaler Exclusively on Normal Training Data
    print(f"[2/6] Normalizing data with MinMaxScaler (fitted strictly on train)...")
    scaler = SequenceScaler(feature_range=(0, 1))
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_normal_scaled = scaler.transform(X_val_normal)

    scaler_path = ARTIFACTS_DIR / f"{dataset_type}_scaler.pkl"
    scaler.save(scaler_path)
    print(f"      Saved scaler to: {scaler_path.name}")

    # 3. Build LSTM Autoencoder Architecture
    print(f"[3/6] Building LSTM Autoencoder model (intermediate=64, bottleneck=32)...")
    model = build_lstm_autoencoder(
        timesteps=timesteps,
        n_features=1,
        intermediate_dim=64,
        latent_dim=32,
        learning_rate=learning_rate,
    )
    model.summary(print_fn=lambda x: print(f"      {x}"))

    # 4. Train with EarlyStopping
    print(f"[4/6] Training model for up to {epochs} epochs (patience={patience})...")
    model_save_path = ARTIFACTS_DIR / f"{dataset_type}_lstm_autoencoder.keras"

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=patience,
            restore_best_weights=True,
            verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(model_save_path),
            monitor="val_loss",
            save_best_only=True,
            verbose=0
        )
    ]

    start_time = time.time()
    history = model.fit(
        X_train_scaled,
        X_train_scaled,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_val_normal_scaled, X_val_normal_scaled),
        callbacks=callbacks,
        verbose=1,
    )
    training_duration = round(time.time() - start_time, 2)
    print(f"      Training completed in {training_duration} seconds.")

    # 5. Plot & Save Training History
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    history_plot_path = RESULTS_DIR / f"training_history_{dataset_type}.png"

    plt.figure(figsize=(8, 4.5))
    plt.plot(history.history["loss"], label="Train Loss (MSE)", color="#0A2947", linewidth=2)
    plt.plot(history.history["val_loss"], label="Val Loss (MSE)", color="#22C55E", linewidth=2, linestyle="--")
    plt.title(f"LSTM Autoencoder Training History ({dataset_type.capitalize()} 30/24-step)", fontsize=12, fontweight="bold")
    plt.xlabel("Epoch")
    plt.ylabel("Reconstruction Loss (MSE)")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(history_plot_path, dpi=200)
    plt.close()
    print(f"      Saved training curve to: {history_plot_path.name}")

    # 6. Verify Model Reload from .keras format
    print(f"[5/6] Verifying serialization and calculating anomaly thresholds...")
    reloaded_model = tf.keras.models.load_model(str(model_save_path))
    dummy_input = np.ones((1, timesteps, 1), dtype=np.float32)
    dummy_output = reloaded_model.predict(dummy_input, verbose=0)
    assert dummy_output.shape == (1, timesteps, 1), f"Unexpected output shape: {dummy_output.shape}"
    print(f"      Model reloaded cleanly from .keras format (verification output shape: {dummy_output.shape})")

    # 7. Calculate Reconstruction Error on Normal Validation Sequences
    val_pred = reloaded_model.predict(X_val_normal_scaled, verbose=0)
    # MSE per sample
    val_mse = np.mean(np.square(X_val_normal_scaled - val_pred), axis=(1, 2))

    threshold_95 = float(np.percentile(val_mse, 95))
    threshold_99 = float(np.percentile(val_mse, 99))

    threshold_meta = {
        "model_type": "LSTM_Autoencoder",
        "sequence_type": dataset_type,
        "sequence_length": timesteps,
        "threshold_95": round(threshold_95, 6),
        "threshold_99": round(threshold_99, 6),
        "active_threshold": "threshold_95",
        "active_threshold_value": round(threshold_95, 6),
        "validation_samples": int(len(val_mse)),
        "mean_val_reconstruction_error": round(float(np.mean(val_mse)), 6),
        "std_val_reconstruction_error": round(float(np.std(val_mse)), 6),
        "min_val_reconstruction_error": round(float(np.min(val_mse)), 6),
        "max_val_reconstruction_error": round(float(np.max(val_mse)), 6),
        "final_train_loss": round(float(history.history["loss"][-1]), 6),
        "final_val_loss": round(float(history.history["val_loss"][-1]), 6),
        "epochs_completed": len(history.history["loss"]),
        "training_duration_seconds": training_duration,
        "training_date": datetime.now().isoformat(),
    }

    thresh_path = ARTIFACTS_DIR / f"{dataset_type}_threshold.json"
    with open(thresh_path, "w") as f:
        json.dump(threshold_meta, f, indent=2)

    print(f"[6/6] Saved anomaly threshold metadata to: {thresh_path.name}")
    print(f"      Mean Val Reconstruction Error : {threshold_meta['mean_val_reconstruction_error']}")
    print(f"      95th Percentile Threshold    : {threshold_95:.6f}")
    print(f"      99th Percentile Threshold    : {threshold_99:.6f}")
    return threshold_meta


def main():
    args = parse_args()
    set_reproducibility(args.seed)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================================")
    print("        MeterGuard AI: LSTM Autoencoder Training (Phase 2)        ")
    print("==================================================================")

    if args.model_type in ["daily", "both"]:
        train_single_experiment(
            dataset_type="daily",
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            patience=args.patience,
            seed=args.seed,
        )

    if args.model_type in ["hourly", "both"]:
        train_single_experiment(
            dataset_type="hourly",
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            patience=args.patience,
            seed=args.seed,
        )

    print("\n[COMPLETE] All requested LSTM Autoencoder models trained and saved.")


if __name__ == "__main__":
    main()
