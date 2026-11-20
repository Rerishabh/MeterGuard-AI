"""
MeterGuard AI: Visualization Utilities for Model Evaluation
Generates publication-quality charts for:
1. Confusion Matrices
2. ROC Curves (continuous anomaly scores)
3. Precision-Recall Curves
4. Reconstruction Error Distributions (Normal vs. Anomalous)
"""

from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve, auc

# Style setup
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
PALETTE = ["#0A2947", "#22C55E", "#EF4444", "#8B5E3C", "#6366F1"]


def plot_confusion_matrices(cms: Dict[str, np.ndarray], output_path: Path):
    """Plot side-by-side confusion matrices for evaluated models."""
    n_models = len(cms)
    fig, axes = plt.subplots(1, n_models, figsize=(5 * n_models, 4.5))
    if n_models == 1:
        axes = [axes]

    for ax, (model_name, cm) in zip(axes, cms.items()):
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar=False,
            ax=ax,
            xticklabels=["Normal (0)", "Tamper (1)"],
            yticklabels=["Normal (0)", "Tamper (1)"],
            annot_kws={"size": 13, "weight": "bold"},
        )
        ax.set_title(f"{model_name}", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Predicted Label", fontsize=10)
        ax.set_ylabel("True Label", fontsize=10)

    plt.suptitle("Confusion Matrix Comparison (Held-Out Test Set)", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_roc_curves(roc_data: Dict[str, tuple], output_path: Path):
    """Plot ROC curves comparing continuous anomaly scores."""
    plt.figure(figsize=(7, 5.5))

    for idx, (model_name, (y_true, scores)) in enumerate(roc_data.items()):
        fpr, tpr, _ = roc_curve(y_true, scores)
        roc_auc = auc(fpr, tpr)
        color = PALETTE[idx % len(PALETTE)]
        plt.plot(fpr, tpr, label=f"{model_name} (AUC = {roc_auc:.3f})", color=color, linewidth=2.5)

    plt.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Guess (AUC = 0.500)")
    plt.xlim([-0.02, 1.02])
    plt.ylim([-0.02, 1.05])
    plt.xlabel("False Positive Rate (FPR)", fontsize=11)
    plt.ylabel("True Positive Rate (TPR / Recall)", fontsize=11)
    plt.title("Receiver Operating Characteristic (ROC) Comparison", fontsize=13, fontweight="bold")
    plt.legend(loc="lower right", frameon=True, fontsize=10)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()


def plot_pr_curves(pr_data: Dict[str, tuple], output_path: Path):
    """Plot Precision-Recall curves comparing continuous scores."""
    plt.figure(figsize=(7, 5.5))

    for idx, (model_name, (y_true, scores)) in enumerate(pr_data.items()):
        precision, recall, _ = precision_recall_curve(y_true, scores)
        pr_auc = auc(recall, precision)
        color = PALETTE[idx % len(PALETTE)]
        plt.plot(recall, precision, label=f"{model_name} (PR-AUC = {pr_auc:.3f})", color=color, linewidth=2.5)

    plt.xlim([-0.02, 1.02])
    plt.ylim([-0.02, 1.05])
    plt.xlabel("Recall", fontsize=11)
    plt.ylabel("Precision", fontsize=11)
    plt.title("Precision-Recall Curve Comparison", fontsize=13, fontweight="bold")
    plt.legend(loc="lower left", frameon=True, fontsize=10)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()


def plot_error_distribution(
    normal_errors: np.ndarray,
    anomaly_errors: np.ndarray,
    threshold: float,
    model_name: str,
    output_path: Path
):
    """Plot histogram / KDE of reconstruction error separating normal vs anomalies."""
    plt.figure(figsize=(8, 4.5))

    sns.kdeplot(normal_errors, fill=True, color="#22C55E", alpha=0.4, label=f"Normal (N={len(normal_errors)})")
    sns.kdeplot(anomaly_errors, fill=True, color="#EF4444", alpha=0.4, label=f"Anomalous (N={len(anomaly_errors)})")
    plt.axvline(threshold, color="#0A2947", linestyle="--", linewidth=2, label=f"95th Pct Threshold ({threshold:.4f})")

    plt.xlabel("Reconstruction MSE", fontsize=11)
    plt.ylabel("Density", fontsize=11)
    plt.title(f"{model_name}: Reconstruction Error Distribution", fontsize=13, fontweight="bold")
    plt.legend(loc="upper right", frameon=True, fontsize=10)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()
