"""
MeterGuard AI: Consumption Sequence Anomaly Routes
Handles POST /api/anomaly/analyze with Daily/Hourly LSTM Autoencoder inference,
strict input validation, and database persistence.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.services.ml_engine import ml_engine
from backend.database.session import SessionLocal
from backend.app.models.db_models import Meter, ConsumptionSequence, AnomalyAlert

logger = logging.getLogger("meterguard.anomaly")
router = APIRouter(tags=["Anomaly"])


@router.post("/api/evaluate-sequence")
@router.post("/api/anomaly/analyze")
async def analyze_anomaly(request: Request):
    """
    Ingests daily (30-day) or hourly (24-hour) consumption sequences,
    evaluates reconstruction error against calibrated thresholds,
    and records results in MySQL.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Malformed or empty JSON payload. Expected a JSON object with 'meter_id', 'sequence_type', and 'consumption'.",
            },
        )

    if not data or not isinstance(data, dict):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Malformed or empty JSON payload. Expected a JSON object with 'meter_id', 'sequence_type', and 'consumption'.",
            },
        )

    meter_id = data.get("meter_id")
    if not meter_id or not isinstance(meter_id, str) or not meter_id.strip():
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "'meter_id' must be a non-empty string."},
        )
    meter_id = meter_id.strip()

    sequence_type_raw = data.get("sequence_type")
    if not sequence_type_raw or not isinstance(sequence_type_raw, str):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "'sequence_type' is required and must be 'daily' or 'hourly'."},
        )
    sequence_type = sequence_type_raw.strip().lower()

    if "consumption" not in data:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing required field 'consumption'."},
        )

    consumption = data["consumption"]
    is_simulated = bool(data.get("is_simulated", False))

    is_valid, err_msg = ml_engine.validate_consumption_sequence(sequence_type, consumption)
    if not is_valid:
        return JSONResponse(status_code=400, content={"status": "error", "message": err_msg})

    # Run inference
    result = ml_engine.predict_sequence(sequence_type, consumption, meter_id=meter_id)
    if result.get("status") == "error":
        return JSONResponse(status_code=400, content=result)

    now = datetime.now()

    # Update in-memory meter state for dashboard reactivity
    if meter_id in ml_engine.latest_meter_data:
        ml_engine.latest_meter_data[meter_id]["lstm"] = result
    else:
        location = ml_engine.get_meter_location(meter_id)
        ml_engine.latest_meter_data[meter_id] = {
            "meter_id": meter_id,
            "server_time": now.isoformat(),
            "online": True,
            "location": location,
            "electrical": {"current_A": 0.0, "voltage_V": 230.0, "power_W": 0.0, "raw_current_adc": 0.0, "raw_voltage_adc": 0.0},
            "readings": {"T1_CS": 0.0, "T1_VS": 0.0, "T2_CS": 0.0, "T2_VS": 0.0, "H1_CS": 0.0, "H1_VS": 0.0},
            "live_history": [],
            "model1": {"prediction": "WAITING", "raw_prediction": None, "history_length": 0, "features": None, "consumption_history": None},
            "model2": {
                "prediction": "NORMAL", "raw_prediction": "NORMAL", "fault_active": False,
                "fault_type": None, "fault_status": "MONITORING", "fault_confidence": 0.0,
                "window_size": 0, "normal_count": 0, "fault_s1_count": 0, "fault_s2_count": 0,
                "smoothing_history_length": 0, "features": {},
            },
            "decision": {
                "final_status": "MONITORING",
                "fault_type": None,
                "priority": "LOW",
                "message": f"Consumption sequence analyzed via {sequence_type} LSTM Autoencoder.",
            },
            "lstm": result,
        }

    # Persist sequence and alert to MySQL
    persist_sequence_to_db(meter_id, sequence_type, consumption, result, is_simulated, now)

    return JSONResponse(status_code=200, content=result)


def persist_sequence_to_db(
    meter_id: str,
    sequence_type: str,
    consumption: List[float],
    result: Dict[str, Any],
    is_simulated: bool,
    now: datetime,
):
    """Saves consumption sequence and any resulting anomaly alert."""
    if SessionLocal is None:
        return

    try:
        db: Session = SessionLocal()
        try:
            # Ensure Meter exists
            meter = db.query(Meter).filter(Meter.meter_id == meter_id).first()
            if not meter:
                loc = ml_engine.get_meter_location(meter_id)
                meter = Meter(
                    meter_id=meter_id,
                    location_name=loc.get("name", meter_id),
                    latitude=loc.get("latitude"),
                    longitude=loc.get("longitude"),
                    status="MONITORING",
                    priority="LOW",
                    is_online=True,
                    last_seen=now,
                )
                db.add(meter)
                db.flush()

            # Record sequence
            seq_record = ConsumptionSequence(
                meter_id=meter_id,
                sequence_type=sequence_type,
                sequence_length=len(consumption),
                consumption_json=json.dumps(consumption),
                reconstruction_error=result.get("reconstruction_error"),
                threshold_used=result.get("threshold"),
                threshold_99=result.get("threshold_99"),
                is_anomaly=bool(result.get("is_anomaly")),
                status=result.get("status", "NORMAL"),
                is_simulated=is_simulated,
                analyzed_at=now,
            )
            db.add(seq_record)

            # If anomaly, create alert (with deduplication)
            source_model = "Daily_LSTM_AE" if sequence_type == "daily" else "Hourly_LSTM_AE"
            if result.get("is_anomaly"):
                error = result.get("reconstruction_error", 0.0)
                thresh_99 = result.get("threshold_99", 0.0)
                severity = "HIGH" if (thresh_99 and error >= thresh_99) else "MEDIUM"

                existing_alert = (
                    db.query(AnomalyAlert)
                    .filter(
                        AnomalyAlert.meter_id == meter_id,
                        AnomalyAlert.source_model == source_model,
                        AnomalyAlert.fault_type == "CONSUMPTION_ANOMALY",
                        AnomalyAlert.is_resolved == False,  # noqa: E712
                    )
                    .first()
                )

                if existing_alert:
                    existing_alert.message = (
                        f"{sequence_type.capitalize()} consumption anomaly detected "
                        f"(MSE: {error}, threshold: {result.get('threshold')})."
                    )
                    existing_alert.severity = severity
                else:
                    alert = AnomalyAlert(
                        meter_id=meter_id,
                        source_model=source_model,
                        fault_type="CONSUMPTION_ANOMALY",
                        severity=severity,
                        message=f"{sequence_type.capitalize()} consumption anomaly detected (MSE: {error}, threshold: {result.get('threshold')}).",
                        is_resolved=False,
                        created_at=now,
                    )
                    db.add(alert)
            elif result.get("status") == "NORMAL" and not result.get("is_anomaly"):
                # Auto-resolve only this sequence model's open alerts for this meter
                open_seq_alerts = (
                    db.query(AnomalyAlert)
                    .filter(
                        AnomalyAlert.meter_id == meter_id,
                        AnomalyAlert.source_model == source_model,
                        AnomalyAlert.fault_type == "CONSUMPTION_ANOMALY",
                        AnomalyAlert.is_resolved == False,  # noqa: E712
                    )
                    .all()
                )
                for alert in open_seq_alerts:
                    alert.is_resolved = True

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to persist consumption sequence to MySQL: %s", exc)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Database unavailable during sequence persist: %s", exc)
