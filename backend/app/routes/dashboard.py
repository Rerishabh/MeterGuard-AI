"""
MeterGuard AI: Operations Dashboard & Alerts Routes
Provides GET /api/dashboard, GET /api/meters, GET /api/meter/{meter_id}, and GET /api/alerts.
Retrieves state directly from MySQL when available, with in-memory fallback.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.services.ml_engine import ml_engine
from backend.database.session import SessionLocal
from backend.app.models.db_models import Meter, HardwareReading, ConsumptionSequence, AnomalyAlert

logger = logging.getLogger("meterguard.dashboard")
router = APIRouter(tags=["Dashboard"])


def build_meter_payload_from_db(meter: Meter, db: Session) -> Dict[str, Any]:
    """Reconstructs a comprehensive meter dashboard object from MySQL records."""
    meter_id = meter.meter_id

    # 1. Latest Hardware Reading from MySQL
    latest_hw = (
        db.query(HardwareReading)
        .filter(HardwareReading.meter_id == meter_id)
        .order_by(HardwareReading.timestamp.desc())
        .first()
    )

    # 2. Latest Consumption Sequence from MySQL
    latest_seq = (
        db.query(ConsumptionSequence)
        .filter(ConsumptionSequence.meter_id == meter_id)
        .order_by(ConsumptionSequence.analyzed_at.desc())
        .first()
    )

    # Connection state evaluation (ONLINE, STALE, OFFLINE)
    conn_info = ml_engine.get_meter_connection_info(meter_id)
    online = conn_info["online"]
    connection_state = conn_info["connection_state"]
    last_seen_seconds = conn_info["last_seen_seconds"]
    last_seen = conn_info["last_seen"]

    if connection_state == "OFFLINE":
        ref_time = None
        if latest_hw and latest_hw.timestamp:
            ref_time = latest_hw.timestamp
        elif meter.last_seen:
            ref_time = meter.last_seen

        if ref_time:
            now_utc = datetime.utcnow()
            diff = (now_utc - ref_time).total_seconds()
            if diff <= 10:
                online = True
                connection_state = "ONLINE"
            elif diff <= 60:
                online = False
                connection_state = "STALE"
            else:
                online = False
                connection_state = "OFFLINE"
            last_seen_seconds = round(diff, 1)
            last_seen = ref_time.isoformat()

    # 3. Recent readings history from in-memory stream buffer, falling back to latest MySQL records
    mem_history = list(ml_engine.live_electrical_history.get(meter_id, []))
    if mem_history:
        live_history = mem_history
    else:
        recent_readings = (
            db.query(HardwareReading)
            .filter(HardwareReading.meter_id == meter_id)
            .order_by(HardwareReading.timestamp.desc())
            .limit(60)
            .all()
        )
        recent_readings.reverse()
        live_history = [
            {
                "time": r.id * 100,
                "current_A": r.current_a or 0.0,
                "voltage_V": r.voltage_v or 230.0,
                "power_W": r.power_w or 0.0,
            }
            for r in recent_readings
        ]

    # Reconstruct electrical object
    electrical = {
        "current_A": latest_hw.current_a if latest_hw else 0.0,
        "voltage_V": latest_hw.voltage_v if latest_hw else 230.0,
        "power_W": latest_hw.power_w if latest_hw else 0.0,
        "raw_current_adc": latest_hw.h1_cs if latest_hw else 0.0,
        "raw_voltage_adc": latest_hw.h1_vs if latest_hw else 0.0,
    }

    readings = {
        "T1_CS": latest_hw.t1_cs if latest_hw else 0.0,
        "T1_VS": latest_hw.t1_vs if latest_hw else 0.0,
        "T2_CS": latest_hw.t2_cs if latest_hw else 0.0,
        "T2_VS": latest_hw.t2_vs if latest_hw else 0.0,
        "H1_CS": latest_hw.h1_cs if latest_hw else 0.0,
        "H1_VS": latest_hw.h1_vs if latest_hw else 0.0,
    }

    # Reconstruct LSTM object from MySQL
    if latest_seq:
        lstm = {
            "status": latest_seq.status,
            "sequence_type": latest_seq.sequence_type,
            "sequence_length": latest_seq.sequence_length,
            "reconstruction_error": latest_seq.reconstruction_error,
            "threshold": latest_seq.threshold_used,
            "threshold_99": latest_seq.threshold_99,
            "is_anomaly": latest_seq.is_anomaly,
            "timestamp": latest_seq.analyzed_at.isoformat() if latest_seq.analyzed_at else None,
        }
    else:
        cached_lstm = ml_engine.latest_meter_data.get(meter_id, {}).get("lstm")
        if cached_lstm and cached_lstm.get("status") in ["NORMAL", "SUSPICIOUS"]:
            lstm = cached_lstm
        else:
            lstm = {
                "status": "AWAITING SUFFICIENT HISTORY",
                "message": "Hardware telemetry active. Consumption-based LSTM analysis awaits daily or hourly kWh sequence ingestion.",
                "reconstruction_error": None,
                "threshold": None,
            }

    # Reconstruct authentic consumption sequence history from MySQL
    consumption_history = None
    if latest_seq and latest_seq.consumption_json:
        try:
            raw_seq = json.loads(latest_seq.consumption_json)
            if isinstance(raw_seq, list):
                consumption_history = [round(float(v), 3) for v in raw_seq]
        except Exception:
            pass

    # Model 1 cached details (or evaluated from actual DB 30-day sequence)
    cached_m1 = ml_engine.latest_meter_data.get(meter_id, {}).get("model1")
    if cached_m1 and cached_m1.get("prediction") in ["NORMAL", "SUSPICIOUS"]:
        model1 = cached_m1
        if not consumption_history and cached_m1.get("consumption_history"):
            consumption_history = cached_m1.get("consumption_history")
    elif consumption_history and len(consumption_history) == 30:
        m1_eval = ml_engine.evaluate_consumption_with_model1(consumption_history)
        if m1_eval:
            model1 = m1_eval
        else:
            hist_len = len(ml_engine.meter_history[meter_id])
            pred_state = "WAITING FOR DATA" if hist_len == 0 else "INSUFFICIENT HISTORY"
            model1 = {
                "prediction": pred_state,
                "raw_prediction": None,
                "history_length": hist_len,
                "required_length": 30,
                "features": None,
                "consumption_history": consumption_history,
            }
    else:
        hist_len = len(ml_engine.meter_history[meter_id])
        pred_state = "WAITING FOR DATA" if hist_len == 0 else "INSUFFICIENT HISTORY"
        model1 = cached_m1 or {
            "prediction": pred_state,
            "raw_prediction": None,
            "history_length": hist_len,
            "required_length": 30,
            "features": None,
            "consumption_history": None,
        }

    cached_m2 = ml_engine.latest_meter_data.get(meter_id, {}).get("model2")
    if cached_m2:
        model2 = cached_m2
    elif latest_hw and latest_hw.model2_status:
        model2 = {
            "prediction": latest_hw.model2_status,
            "raw_prediction": latest_hw.model2_status,
            "fault_active": latest_hw.final_status in ["FAULT DETECTED", "HIGH PRIORITY ALERT"],
            "fault_type": None,
            "fault_status": "MONITORING",
            "fault_confidence": 0.0,
            "window_size": 0,
            "normal_count": 0,
            "fault_s1_count": 0,
            "fault_s2_count": 0,
            "smoothing_history_length": 0,
            "features": {},
        }
    else:
        model2 = {
            "prediction": "WAITING FOR DATA",
            "raw_prediction": None,
            "fault_active": False,
            "fault_type": None,
            "fault_status": "WAITING FOR DATA",
            "fault_confidence": 0.0,
            "window_size": 0,
            "normal_count": 0,
            "fault_s1_count": 0,
            "fault_s2_count": 0,
            "smoothing_history_length": 0,
            "features": {},
        }

    decision = {
        "final_status": meter.status or "MONITORING",
        "fault_type": model2.get("fault_type"),
        "priority": meter.priority or "LOW",
        "message": f"Meter status: {meter.status}",
    }

    return {
        "meter_id": meter_id,
        "server_time": datetime.now().isoformat(),
        "online": online,
        "connection_state": connection_state,
        "last_seen_seconds": last_seen_seconds,
        "last_seen": last_seen,
        "is_simulated": meter_id.startswith("M_SIM") or (latest_seq.is_simulated if latest_seq else False),
        "location": {
            "name": meter.location_name or meter_id,
            "latitude": meter.latitude,
            "longitude": meter.longitude,
        },
        "electrical": electrical,
        "readings": readings,
        "live_history": live_history or list(ml_engine.live_electrical_history[meter_id]),
        "consumption_history": consumption_history,
        "model1": model1,
        "model2": model2,
        "lstm": lstm,
        "decision": decision,
    }


@router.get("/api/dashboard")
def get_dashboard():
    """
    Returns operations status for all meters.
    Directly queries MySQL when connected; falls back to in-memory cache.
    """
    meters = []
    if SessionLocal is not None:
        try:
            db: Session = SessionLocal()
            try:
                db_meters = db.query(Meter).all()
                if db_meters:
                    for m in db_meters:
                        meters.append(build_meter_payload_from_db(m, db))
                    return {
                        "status": "online",
                        "source": "mysql",
                        "meter_count": len(meters),
                        "meters": meters,
                    }
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Error querying dashboard from MySQL: %s", exc)

    # In-memory fallback
    for meter_id, meter_data in ml_engine.latest_meter_data.items():
        meter_copy = dict(meter_data)
        meter_copy["online"] = ml_engine.get_meter_online_status(meter_id)
        meter_copy["location"] = ml_engine.get_meter_location(meter_id)
        meters.append(meter_copy)

    return {
        "status": "online",
        "source": "memory",
        "meter_count": len(meters),
        "meters": meters,
    }


@router.get("/api/meters")
def get_meters():
    """Returns list of registered meters with online state and GIS coordinates from MySQL."""
    if SessionLocal is not None:
        try:
            db: Session = SessionLocal()
            try:
                db_meters = db.query(Meter).all()
                if db_meters:
                    return {
                        "status": "online",
                        "source": "mysql",
                        "meters": [
                            {
                                "meter_id": m.meter_id,
                                "online": ml_engine.get_meter_online_status(m.meter_id),
                                "connection_state": ml_engine.get_meter_connection_info(m.meter_id)["connection_state"],
                                "is_simulated": m.meter_id.startswith("M_SIM"),
                                "location": {
                                    "name": m.location_name or m.meter_id,
                                    "latitude": m.latitude,
                                    "longitude": m.longitude,
                                },
                            }
                            for m in db_meters
                        ],
                    }
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Error querying /api/meters from MySQL: %s", exc)

    # In-memory fallback
    meters = [
        {
            "meter_id": meter_id,
            "online": ml_engine.get_meter_online_status(meter_id),
            "location": ml_engine.get_meter_location(meter_id),
        }
        for meter_id in ml_engine.latest_meter_data
    ]

    return {
        "status": "online",
        "source": "memory",
        "meters": meters,
    }


@router.get("/api/meter/{meter_id}")
def get_meter(meter_id: str):
    """Returns detailed telemetry, live history, and model states for a single meter from MySQL."""
    if SessionLocal is not None:
        try:
            db: Session = SessionLocal()
            try:
                meter = db.query(Meter).filter(Meter.meter_id == meter_id).first()
                if meter:
                    return build_meter_payload_from_db(meter, db)
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Error querying /api/meter/%s from MySQL: %s", meter_id, exc)

    # In-memory fallback
    if meter_id not in ml_engine.latest_meter_data:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Meter not found."},
        )

    meter_data = dict(ml_engine.latest_meter_data[meter_id])
    meter_data["online"] = ml_engine.get_meter_online_status(meter_id)
    meter_data["location"] = ml_engine.get_meter_location(meter_id)
    return meter_data


@router.get("/api/alerts")
def get_alerts(
    meter_id: Optional[str] = Query(default=None, description="Filter by meter ID"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of alerts to return"),
):
    """
    Returns audit alerts directly from MySQL with optional filtering by meter and severity.
    """
    alerts_list = []
    if SessionLocal is not None:
        try:
            db: Session = SessionLocal()
            try:
                query = db.query(AnomalyAlert)
                if meter_id:
                    query = query.filter(AnomalyAlert.meter_id == meter_id)
                if severity:
                    query = query.filter(AnomalyAlert.severity == severity.upper())

                results = query.order_by(AnomalyAlert.created_at.desc()).limit(limit).all()
                for a in results:
                    alerts_list.append({
                        "id": a.id,
                        "meter_id": a.meter_id,
                        "source_model": a.source_model,
                        "fault_type": a.fault_type,
                        "severity": a.severity,
                        "message": a.message,
                        "is_resolved": a.is_resolved,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    })
                return {
                    "status": "online",
                    "source": "mysql",
                    "count": len(alerts_list),
                    "alerts": alerts_list,
                }
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Error querying alerts from MySQL: %s", exc)
            return {
                "status": "degraded",
                "database_connected": False,
                "message": f"Database temporarily unavailable: {exc}",
                "count": 0,
                "alerts": [],
            }

    return {
        "status": "online",
        "source": "memory",
        "count": 0,
        "alerts": [],
    }
