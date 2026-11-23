"""
MeterGuard AI: Managed Dataset Replay Simulation Service
Provides automatic, continuous replay of historical hardware datasets
into the telemetry processing and ML inference pipeline.
Fully integrated into FastAPI application lifecycle with graceful shutdown,
duplicate-worker prevention, and status telemetry.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

from backend.app.config import PROJECT_ROOT

logger = logging.getLogger("meterguard.simulation")

DEFAULT_DATASET_PATH = PROJECT_ROOT / "data" / "hardware_dataset.csv"
DEFAULT_DELAY_SECONDS = 1.0


class SimulationManager:
    """
    Manages background continuous replay of the hardware dataset.
    Ensures strictly one managed worker task per application instance.
    """

    def __init__(self):
        self._dataset_path = DEFAULT_DATASET_PATH
        self._active_meter = "M001"
        self._delay = DEFAULT_DELAY_SECONDS
        self._state: str = "SIMULATION PAUSED"  # INITIALIZING, SIMULATED, SIMULATION PAUSED, SIMULATION ERROR
        self._error_message: Optional[str] = None
        self._readings_count: int = 0
        self._current_iteration: int = 0
        self._last_reading_time: Optional[str] = None

        self._worker_task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._pause_event: asyncio.Event = asyncio.Event()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._df: Optional[pd.DataFrame] = None

    def _load_dataset(self) -> bool:
        if self._df is not None and not self._df.empty:
            return True

        if not self._dataset_path.is_file():
            self._error_message = f"Dataset file not found at {self._dataset_path}"
            logger.error(self._error_message)
            self._state = "SIMULATION ERROR"
            return False

        try:
            df = pd.read_csv(self._dataset_path)
            required_cols = ["T1_CS", "T1_VS", "T2_CS", "T2_VS", "H1_CS", "H1_VS"]
            for col in required_cols:
                if col not in df.columns:
                    self._error_message = f"Missing required column '{col}' in {self._dataset_path}"
                    logger.error(self._error_message)
                    self._state = "SIMULATION ERROR"
                    return False

            self._df = df
            logger.info("SimulationManager loaded %d readings from %s", len(df), self._dataset_path.name)
            return True
        except Exception as exc:
            self._error_message = f"Failed to parse dataset CSV: {exc}"
            logger.error(self._error_message)
            self._state = "SIMULATION ERROR"
            return False

    async def start_default_simulation(self, meter_id: str = "M001", delay: float = 1.0) -> bool:
        """
        Initializes and starts automatic dataset replay.
        Idempotent: Prevents duplicate replay workers if already running.
        """
        async with self._lock:
            if self._worker_task is not None and not self._worker_task.done():
                logger.info("Simulation worker is already running (Task: %s)", self._worker_task)
                return True

            self._state = "INITIALIZING"
            self._active_meter = meter_id
            self._delay = max(0.1, float(delay))
            self._stop_event.clear()
            self._pause_event.set()  # Not paused

            if not self._load_dataset():
                return False

            # Spawn background replay task
            self._worker_task = asyncio.create_task(self._replay_loop(), name="meterguard-simulation-worker")
            logger.info(
                "[SIMULATOR] Automatic dataset replay started for meter '%s' (delay: %.1fs).",
                self._active_meter,
                self._delay,
            )
            return True

    async def _replay_loop(self):
        """Continuous dataset streaming loop."""
        # Late import to prevent circular import
        from backend.app.routes.telemetry import ingest_telemetry_reading

        try:
            total_records = len(self._df)
            while not self._stop_event.is_set():
                self._current_iteration += 1
                logger.info(
                    "[SIMULATOR] Starting iteration %d of hardware dataset (%d records)",
                    self._current_iteration,
                    total_records,
                )

                for _, row in self._df.iterrows():
                    if self._stop_event.is_set():
                        break

                    # Handle pause state
                    await self._pause_event.wait()
                    if self._stop_event.is_set():
                        break

                    payload = {
                        "meter_id": self._active_meter,
                        "time_ms": int(row.get("time_ms", int(time.time() * 1000))),
                        "T1_CS": float(row["T1_CS"]),
                        "T1_VS": float(row["T1_VS"]),
                        "T2_CS": float(row["T2_CS"]),
                        "T2_VS": float(row["T2_VS"]),
                        "H1_CS": float(row["H1_CS"]),
                        "H1_VS": float(row["H1_VS"]),
                    }

                    try:
                        status_code, _ = ingest_telemetry_reading(payload)
                        if status_code == 200:
                            self._state = "SIMULATED"
                            self._readings_count += 1
                            self._last_reading_time = datetime.now().isoformat()
                            self._error_message = None
                    except Exception as exc:
                        logger.warning("[SIMULATOR] Error streaming telemetry record: %s", exc)

                    try:
                        await asyncio.sleep(self._delay)
                    except asyncio.CancelledError:
                        break

        except asyncio.CancelledError:
            logger.info("[SIMULATOR] Replay loop cancelled.")
        except Exception as exc:
            self._state = "SIMULATION ERROR"
            self._error_message = str(exc)
            logger.error("[SIMULATOR ERROR] Unhandled exception in replay loop: %s", exc, exc_info=True)
        finally:
            if not self._stop_event.is_set():
                self._state = "SIMULATION PAUSED"

    async def pause_simulation(self):
        """Pauses the stream without stopping the background worker."""
        self._pause_event.clear()
        self._state = "SIMULATION PAUSED"
        logger.info("[SIMULATOR] Simulation stream paused.")

    async def resume_simulation(self):
        """Resumes the paused stream."""
        self._pause_event.set()
        self._state = "SIMULATED"
        logger.info("[SIMULATOR] Simulation stream resumed.")

    async def stop_simulation(self):
        """Gracefully terminates the background replay worker."""
        async with self._lock:
            self._stop_event.set()
            self._pause_event.set()  # Unblock if paused
            if self._worker_task is not None:
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except (asyncio.CancelledError, Exception):
                    pass
                self._worker_task = None
            self._state = "SIMULATION PAUSED"
            logger.info("[SIMULATOR] Replay worker cleanly terminated.")

    def get_status(self) -> Dict[str, Any]:
        """Returns the single source of truth for simulation status."""
        is_worker_active = (
            self._worker_task is not None
            and not self._worker_task.done()
            and not self._stop_event.is_set()
            and self._pause_event.is_set()
        )

        effective_state = self._state
        if self._state == "SIMULATED" and not is_worker_active:
            effective_state = "SIMULATION PAUSED"

        return {
            "status": effective_state,
            "is_running": is_worker_active,
            "active_meter": self._active_meter,
            "readings_count": self._readings_count,
            "iteration": self._current_iteration,
            "delay_seconds": self._delay,
            "dataset": self._dataset_path.name if self._dataset_path else None,
            "last_reading_time": self._last_reading_time,
            "error": self._error_message,
        }


# Global singleton instance
simulation_manager = SimulationManager()
