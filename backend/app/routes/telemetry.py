"""
MeterGuard AI: Hardware Telemetry Routes
Handles POST /api/meter-data with Model 1, Model 2, temporal filtering,
decision arbitration, database persistence, and alert deduplication.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.services.ml_engine import ml_engine
from backend.model2_features import create_model2_features
from backend.decision_logic import get_final_status
from backend.database.session import SessionLocal
from backend.app.models.db_models import Meter, HardwareReading, AnomalyAlert

logger = logging.getLogger("meterguard.telemetry")
router = APIRouter(tags=["Telemetry"])


@router.post("/api/meter-data")
async def receive_meter_data(request: Request):
    """
    Ingests high-frequency ESP32 sensor telemetry (~100ms intervals),
    executes electrical calculations, runs Model 2 & temporal filter,
    runs Model 1 rolling consumption, applies decision arbitration,
    and persists records to MySQL with alert deduplication.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No JSON data received."})

    if not data or not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"status": "error", "message": "No JSON data received."})

    meter_id = str(data.get("meter_id", "M001"))

    required_fields = ["T1_CS", "T1_VS", "T2_CS", "T2_VS", "H1_CS", "H1_VS"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Missing sensor values.",
                "missing": missing,
            },
        )

    try:
        t1_cs = float(data["T1_CS"])
        t1_vs = float(data["T1_VS"])
        t2_cs = float(data["T2_CS"])
        t2_vs = float(data["T2_VS"])
        h1_cs = float(data["H1_CS"])
        h1_vs = float(data["H1_VS"])
    except (ValueError, TypeError) as exc:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Sensor values must be numeric: {exc}"},
        )

    now = datetime.now()
    ml_engine.meter_last_seen[meter_id] = now

    # 1. Electrical calculations
    electrical = ml_engine.calculate_electrical_values(h1_cs, h1_vs)

    # 2. History buffer updates
    ml_engine.meter_history[meter_id].append(h1_cs)
    ml_engine.live_electrical_history[meter_id].append({
        "time": data.get("time_ms", 0),
        "current_A": electrical["current_A"],
        "voltage_V": electrical["voltage_V"],
        "power_W": electrical["power_W"],
    })

    # 3. Model 2 Features & Prediction
    model2_feature_dict = {}
    if ml_engine.model2 is not None:
        try:
            model2_features = create_model2_features(data)
            raw_pred = ml_engine.model2.predict(model2_features)[0]
            raw_model2 = ml_engine.normalize_model2_prediction(raw_pred)
            for col in model2_features.columns:
                model2_feature_dict[col] = float(model2_features.iloc[0][col])
        except Exception as exc:
            logger.error("Error evaluating Model 2: %s", exc)
            raw_model2 = "NORMAL"
    else:
        raw_model2 = "NORMAL"

    # 4. Temporal Fault Filtering
    filtered_model2 = ml_engine.update_fault_filter(meter_id, raw_model2)
    model2_result = filtered_model2["prediction"]

    # 5. Model 1 (Isolation Forest)
    model1_result = ml_engine.run_model1(meter_id)

    # 6. Model 3: Preserved LSTM Result
    existing_lstm = ml_engine.latest_meter_data.get(meter_id, {}).get("lstm")
    if existing_lstm and existing_lstm.get("status") in ["NORMAL", "SUSPICIOUS"]:
        lstm_result = existing_lstm
    else:
        lstm_result = {
            "status": "AWAITING SUFFICIENT HISTORY",
            "message": "Hardware telemetry active. Consumption-based LSTM analysis awaits daily (30-day) or hourly (24-hour) kWh sequence ingestion via /api/anomaly/analyze.",
            "reconstruction_error": None,
            "threshold": None,
        }

    # 7. Final Decision Arbitration
    if model1_result["prediction"] == "WAITING":
        decision = {
            "final_status": "MONITORING",
            "fault_type": filtered_model2["fault_type"],
            "priority": "LOW",
            "message": "Collecting consumption history for Model 1.",
        }
    else:
        decision = get_final_status(model1_result["prediction"], model2_result)

    location = ml_engine.get_meter_location(meter_id)
    online = ml_engine.get_meter_online_status(meter_id)

    response_payload = {
        "status": "received",
        "meter_id": meter_id,
        "timestamp": data.get("time_ms"),
        "server_time": now.isoformat(),
        "online": online,
        "location": location,
        "electrical": electrical,
        "readings": {
            "T1_CS": t1_cs,
            "T1_VS": t1_vs,
            "T2_CS": t2_cs,
            "T2_VS": t2_vs,
            "H1_CS": h1_cs,
            "H1_VS": h1_vs,
        },
        "live_history": list(ml_engine.live_electrical_history[meter_id]),
        "model1": model1_result,
        "lstm": lstm_result,
        "model2": {
            "prediction": model2_result,
            "raw_prediction": raw_model2,
            "fault_active": filtered_model2["fault_active"],
            "fault_type": filtered_model2["fault_type"],
            "fault_status": filtered_model2["fault_status"],
            "fault_confidence": filtered_model2["fault_confidence"],
            "window_size": filtered_model2["window_size"],
            "normal_count": filtered_model2["normal_count"],
            "fault_s1_count": filtered_model2["fault_s1_count"],
            "fault_s2_count": filtered_model2["fault_s2_count"],
            "smoothing_history_length": len(ml_engine.model2_prediction_history[meter_id]),
            "features": model2_feature_dict,
        },
        "decision": decision,
    }

    # Cache in memory for instant reactivity
    ml_engine.latest_meter_data[meter_id] = response_payload

    # 8. MySQL Database Persistence with Deduplication
    persist_telemetry_to_db(
        meter_id=meter_id,
        location=location,
        electrical=electrical,
        readings_dict={"t1_cs": t1_cs, "t1_vs": t1_vs, "t2_cs": t2_cs, "t2_vs": t2_vs, "h1_cs": h1_cs, "h1_vs": h1_vs},
        model1_result=model1_result,
        model2_result=model2_result,
        filtered_model2=filtered_model2,
        decision=decision,
        now=now,
    )

    # Console logging matching Flask output
    print()
    print("==========================================")
    print("Meter:", meter_id)
    print("H1:", int(h1_cs), int(h1_vs))
    print("Raw Model 2:", raw_model2)
    print("Model 2:", model2_result)
    print("Fault active:", filtered_model2["fault_active"])
    print("Fault type:", filtered_model2["fault_type"])
    print(f"Fault confidence: {filtered_model2['fault_confidence']} %")
    print("Model 1:", model1_result["prediction"])
    print(f"LSTM AE: {lstm_result.get('status')} (error: {lstm_result.get('reconstruction_error')}, thresh: {lstm_result.get('threshold')})")
    print("FINAL:", decision["final_status"])
    print("PRIORITY:", decision["priority"])
    print("==========================================")

    return response_payload


def persist_telemetry_to_db(
    meter_id: str,
    location: Dict[str, Any],
    electrical: Dict[str, Any],
    readings_dict: Dict[str, float],
    model1_result: Dict[str, Any],
    model2_result: str,
    filtered_model2: Dict[str, Any],
    decision: Dict[str, Any],
    now: datetime,
):
    """
    Safely commits readings and manages alert deduplication.
    Never crashes the HTTP handler if the database is disconnected.
    """
    if SessionLocal is None:
        return

    try:
        db: Session = SessionLocal()
        try:
            # Upsert Meter record
            meter = db.query(Meter).filter(Meter.meter_id == meter_id).first()
            if not meter:
                meter = Meter(
                    meter_id=meter_id,
                    location_name=location.get("name", meter_id),
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                    status=decision.get("final_status", "MONITORING"),
                    priority=decision.get("priority", "LOW"),
                    is_online=True,
                    last_seen=now,
                )
                db.add(meter)
                db.flush()
            else:
                meter.status = decision.get("final_status", meter.status)
                meter.priority = decision.get("priority", meter.priority)
                meter.is_online = True
                meter.last_seen = now

            # Insert HardwareReading record
            reading = HardwareReading(
                meter_id=meter_id,
                timestamp=now,
                t1_cs=readings_dict.get("t1_cs"),
                t1_vs=readings_dict.get("t1_vs"),
                t2_cs=readings_dict.get("t2_cs"),
                t2_vs=readings_dict.get("t2_vs"),
                h1_cs=readings_dict.get("h1_cs"),
                h1_vs=readings_dict.get("h1_vs"),
                voltage_v=electrical.get("voltage_V"),
                current_a=electrical.get("current_A"),
                power_w=electrical.get("power_W"),
                model1_status=model1_result.get("prediction"),
                model2_status=model2_result,
                final_status=decision.get("final_status"),
                priority=decision.get("priority"),
            )
            db.add(reading)

            # Alert Deduplication Logic
            # Only create an alert when fault is active and confirmed
            if filtered_model2.get("fault_active") and filtered_model2.get("fault_type"):
                fault_type = filtered_model2["fault_type"]
                severity = "HIGH" if fault_type in ["FAULT_S1", "FAULT_S2"] else "MEDIUM"
                
                # Check for existing unresolved alert for this meter & fault
                existing_alert = (
                    db.query(AnomalyAlert)
                    .filter(
                        AnomalyAlert.meter_id == meter_id,
                        AnomalyAlert.fault_type == fault_type,
                        AnomalyAlert.is_resolved == False,  # noqa: E712
                    )
                    .first()
                )

                if existing_alert:
                    # Deduplicated: Update message and timestamp without spawning duplicate rows
                    existing_alert.message = (
                        f"Active tampering alert {fault_type} ongoing. "
                        f"Confidence: {filtered_model2.get('fault_confidence', 0)}%."
                    )
                else:
                    # New active fault detected: create alert
                    new_alert = AnomalyAlert(
                        meter_id=meter_id,
                        source_model="RandomForest",
                        fault_type=fault_type,
                        severity=severity,
                        message=f"Hardware tampering {fault_type} confirmed with {filtered_model2.get('fault_confidence', 0)}% confidence.",
                        is_resolved=False,
                        created_at=now,
                    )
                    db.add(new_alert)

            elif filtered_model2.get("fault_status") == "CLEARED":
                # Auto-resolve previously open alerts when normal clear threshold is reached
                open_alerts = (
                    db.query(AnomalyAlert)
                    .filter(
                        AnomalyAlert.meter_id == meter_id,
                        AnomalyAlert.is_resolved == False,  # noqa: E712
                    )
                    .all()
                )
                for alert in open_alerts:
                    alert.is_resolved = True

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to commit telemetry to MySQL: %s", exc)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Database unavailable during telemetry write: %s", exc)
