"""
MeterGuard AI: LSTM Autoencoder Model Definition
Implements an LSTM Autoencoder using standard built-in Keras layers:
  Encoder: LSTM(..., return_sequences=False)
  Decoder: RepeatVector(timesteps) -> LSTM(..., return_sequences=True) -> TimeDistributed(Dense(1))

Trained exclusively on normal sequences for time-series reconstruction-error anomaly detection.
"""

from typing import Tuple
import tensorflow as tf
from tensorflow.keras import layers, models


def build_lstm_autoencoder(
    timesteps: int,
    n_features: int = 1,
    intermediate_dim: int = 64,
    latent_dim: int = 32,
    learning_rate: float = 0.001,
) -> tf.keras.Model:
    """
    Constructs an LSTM Autoencoder strictly using standard Keras layers.
    Args:
        timesteps: Sequence length (30 for daily, 24 for hourly)
        n_features: Number of features per timestep (1 for univariate kWh)
        intermediate_dim: Dimension of outer LSTM layers
        latent_dim: Compressed bottleneck dimension
        learning_rate: Learning rate for Adam optimizer
    Returns:
        Compiled Keras Model
    """
    inputs = layers.Input(shape=(timesteps, n_features), name="encoder_input")

    # Encoder
    x = layers.LSTM(
        intermediate_dim,
        activation="tanh",
        recurrent_activation="sigmoid",
        return_sequences=True,
        name="encoder_lstm_1"
    )(inputs)

    bottleneck = layers.LSTM(
        latent_dim,
        activation="tanh",
        recurrent_activation="sigmoid",
        return_sequences=False,
        name="encoder_bottleneck"
    )(x)

    # Decoder
    repeat = layers.RepeatVector(timesteps, name="decoder_repeat")(bottleneck)

    x = layers.LSTM(
        intermediate_dim,
        activation="tanh",
        recurrent_activation="sigmoid",
        return_sequences=True,
        name="decoder_lstm_1"
    )(repeat)

    outputs = layers.TimeDistributed(
        layers.Dense(n_features, activation="linear"),
        name="decoder_output"
    )(x)

    model = models.Model(inputs=inputs, outputs=outputs, name=f"lstm_autoencoder_{timesteps}t")

    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(optimizer=optimizer, loss="mse", metrics=["mae"])

    return model
