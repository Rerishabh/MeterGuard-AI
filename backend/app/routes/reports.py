"""
MeterGuard AI: Investigation Reports & Tampering Simulation Routes (Phase 3B)
Provides:
  - POST /api/reports/generate
  - GET /api/reports/{meter_id}
  - GET /api/reports
  - POST /api/simulate/tamper
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

from backend.database.session import SessionLocal
from backend.app.models.db_models import (
    Meter,
    HardwareReading,
    ConsumptionSequence,
    AnomalyAlert,
    InvestigationReport,
)
from backend.app.schemas.report import (
    ReportGenerateRequest,
    SimulateTamperRequest,
)
from backend.app.services.ml_engine import ml_engine
from backend.app.services.tamper_simulator import tamper_simulator, VALID_SCENARIOS
from backend.app.services.investigation_generator import investigation_generator

logger = logging.getLogger("meterguard.reports")
router = APIRouter(tags=["Investigation Reports & Simulator"])


@router.post("/api/reports/generate")
def generate_investigation_report(payload: ReportGenerateRequest):
    """
    Generates a formal, evidence-grounded forensic investigation report for a meter.
    Uses Gemini 2.5 Flash if available, otherwise deterministic fallback.
    """
    meter_id = payload.meter_id.strip() if payload.meter_id else ""
    if not meter_id:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "'meter_id' must be a non-empty string."},
        )

    db = SessionLocal()
    try:
        meter = db.query(Meter).filter(Meter.meter_id == meter_id).first()
        if not meter:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": f"Meter '{meter_id}' not found in database."},
            )

        report, err = investigation_generator.generate_report(
            db,
            meter_id=meter_id,
            alert_id=payload.alert_id,
            sequence_id=payload.sequence_id,
        )
        if err or not report:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": err or "Failed to generate report."},
            )

        evidence_dict = None
        if report.evidence_json:
            try:
                evidence_dict = json.loads(report.evidence_json)
            except Exception:
                pass

        return {
            "status": "success",
            "report": {
                "id": report.id,
                "meter_id": report.meter_id,
                "alert_id": report.alert_id,
                "sequence_id": payload.sequence_id or (evidence_dict.get("consumption", {}).get("sequence_id") if evidence_dict else None),
                "model_used": report.model_used,
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "report_markdown": report.report_markdown,
                "evidence": evidence_dict,
            },
        }
    finally:
        db.close()


@router.get("/api/reports/{meter_id}")
def get_meter_reports(meter_id: str):
    """
    Retrieves all forensic investigation reports for a specific meter, ordered newest first.
    """
    clean_id = meter_id.strip()
    if not clean_id:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "'meter_id' cannot be empty."},
        )

    db = SessionLocal()
    try:
        records = (
            db.query(InvestigationReport)
            .filter(InvestigationReport.meter_id == clean_id)
            .order_by(InvestigationReport.created_at.desc())
            .all()
        )

        reports_list = []
        for r in records:
            ev = None
            if r.evidence_json:
                try:
                    ev = json.loads(r.evidence_json)
                except Exception:
                    pass
            reports_list.append({
                "id": r.id,
                "meter_id": r.meter_id,
                "alert_id": r.alert_id,
                "sequence_id": ev.get("consumption", {}).get("sequence_id") if ev else None,
                "model_used": r.model_used,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "report_markdown": r.report_markdown,
                "evidence": ev,
            })

        return {
            "status": "success",
            "meter_id": clean_id,
            "count": len(reports_list),
            "reports": reports_list,
        }
    finally:
        db.close()


@router.get("/api/reports")
def get_recent_reports(limit: int = Query(default=20, ge=1, le=100)):
    """
    Retrieves recent forensic investigation reports across all meters.
    """
    db = SessionLocal()
    try:
        records = (
            db.query(InvestigationReport)
            .order_by(InvestigationReport.created_at.desc())
            .limit(limit)
            .all()
        )

        reports_list = []
        for r in records:
            reports_list.append({
                "id": r.id,
                "meter_id": r.meter_id,
                "alert_id": r.alert_id,
                "model_used": r.model_used,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "report_markdown": r.report_markdown[:300] + "..." if len(r.report_markdown) > 300 else r.report_markdown,
            })

        return {
            "status": "success",
            "count": len(reports_list),
            "limit": limit,
            "reports": reports_list,
        }
    finally:
        db.close()


@router.post("/api/simulate-tampering")
@router.post("/api/simulate/tamper")
def simulate_tampering(payload: SimulateTamperRequest):
    """
    Simulates a 30-day smart meter consumption profile under one of six realistic scenarios.
    Passes sequence to the Daily LSTM Autoencoder, persists sequence to MySQL with is_simulated=True,
    creates/updates deduplicated alerts on anomaly, and optionally auto-generates a forensic report.
    """
    meter_id = payload.meter_id.strip() if payload.meter_id else ""
    if not meter_id:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "'meter_id' must be a non-empty string."},
        )

    scenario = payload.scenario.strip().lower() if payload.scenario else ""
    if scenario not in VALID_SCENARIOS:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"Unknown scenario '{scenario}'. Valid scenarios: {list(VALID_SCENARIOS.keys())}",
            },
        )

    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # 1. Ensure target meter exists in MySQL
        meter = db.query(Meter).filter(Meter.meter_id == meter_id).first()
        if not meter:
            meter = Meter(
                meter_id=meter_id,
                location_name=f"Sector-{meter_id}",
                status="MONITORING",
                priority="LOW",
                is_online=True,
                last_seen=now,
            )
            db.add(meter)
            db.flush()
        else:
            meter.last_seen = now
            meter.is_online = True

        ml_engine.meter_last_seen[meter_id] = datetime.now()

        # 2. Run simulation and honest LSTM evaluation
        sim = tamper_simulator.simulate_and_evaluate(meter_id, scenario)
        lstm = sim["lstm_result"]
        is_anomaly = lstm.get("is_anomaly", False)

        # 3. Persist ConsumptionSequence with is_simulated=True and scenario
        seq_record = ConsumptionSequence(
            meter_id=meter_id,
            sequence_type="daily",
            sequence_length=30,
            consumption_json=json.dumps(sim["consumption"]),
            reconstruction_error=lstm.get("reconstruction_error"),
            threshold_used=lstm.get("threshold"),
            threshold_99=lstm.get("threshold_99"),
            is_anomaly=is_anomaly,
            status=lstm.get("status", "NORMAL"),
            is_simulated=True,
            scenario=scenario,
            analyzed_at=now,
        )
        db.add(seq_record)

        # 4. Synchronize in-memory ML Engine state for immediate dashboard reactivity
        if meter_id not in ml_engine.latest_meter_data:
            ml_engine.latest_meter_data[meter_id] = {
                "meter_id": meter_id,
                "online": True,
                "status": "received",
                "server_time": datetime.now().isoformat(),
            }
        ml_engine.latest_meter_data[meter_id]["lstm"] = {
            "status": lstm.get("status", "NORMAL"),
            "sequence_type": "daily",
            "sequence_length": 30,
            "reconstruction_error": lstm.get("reconstruction_error"),
            "threshold": lstm.get("threshold"),
            "threshold_99": lstm.get("threshold_99"),
            "is_anomaly": is_anomaly,
            "is_simulated": True,
            "scenario": scenario,
            "timestamp": datetime.now().isoformat(),
        }

        # 5. Alert Deduplication & Status Update
        alert_info = None
        if is_anomaly:
            meter.status = "SUSPICIOUS"
            if meter.priority not in ["HIGH", "CRITICAL"]:
                meter.priority = "MEDIUM"

            fault_tag = f"SIMULATED_{scenario.upper()}"
            existing_alert = (
                db.query(AnomalyAlert)
                .filter(
                    AnomalyAlert.meter_id == meter_id,
                    AnomalyAlert.source_model == "LSTM_Autoencoder",
                    AnomalyAlert.fault_type == fault_tag,
                    AnomalyAlert.is_resolved == False,  # noqa: E712
                )
                .first()
            )

            if existing_alert:
                existing_alert.fault_type = fault_tag
                existing_alert.message = (
                    f"Simulated anomaly '{scenario}' active. "
                    f"Reconstruction MSE: {lstm.get('reconstruction_error')} (Threshold: {lstm.get('threshold')})."
                )
                existing_alert.created_at = now
                alert_obj = existing_alert
            else:
                alert_obj = AnomalyAlert(
                    meter_id=meter_id,
                    source_model="LSTM_Autoencoder",
                    fault_type=fault_tag,
                    severity="HIGH" if scenario in ["consumption_spike", "sudden_drop"] else "MEDIUM",
                    message=(
                        f"Simulated anomaly '{scenario}' detected. "
                        f"Reconstruction MSE: {lstm.get('reconstruction_error')} (Threshold: {lstm.get('threshold')})."
                    ),
                    is_resolved=False,
                    created_at=now,
                )
                db.add(alert_obj)
                db.flush()

            alert_info = {
                "id": alert_obj.id,
                "source_model": alert_obj.source_model,
                "fault_type": alert_obj.fault_type,
                "severity": alert_obj.severity,
                "message": alert_obj.message,
                "is_resolved": alert_obj.is_resolved,
            }
        elif scenario == "normal":
            # If simulated normal, resolve any lingering active simulated LSTM alerts
            existing_sim_alerts = (
                db.query(AnomalyAlert)
                .filter(
                    AnomalyAlert.meter_id == meter_id,
                    AnomalyAlert.source_model == "LSTM_Autoencoder",
                    AnomalyAlert.is_resolved == False,  # noqa: E712
                )
                .all()
            )
            for sa in existing_sim_alerts:
                sa.is_resolved = True

            # If no hardware fault, ensure meter status returns to NORMAL
            hw_reading = (
                db.query(HardwareReading)
                .filter(HardwareReading.meter_id == meter_id)
                .order_by(HardwareReading.id.desc())
                .first()
            )
            if not hw_reading or hw_reading.final_status in ["NORMAL", None]:
                meter.status = "NORMAL"
                meter.priority = "LOW"

        # Commit sequence, meter updates, and alert
        db.commit()

        # 6. Auto-generate report if requested
        report_info = None
        if payload.auto_generate_report:
            report_obj, r_err = investigation_generator.generate_report(
                db,
                meter_id=meter_id,
                alert_id=alert_info["id"] if alert_info else None,
                sequence_id=seq_record.id,
            )
            if report_obj:
                ev_data = None
                if report_obj.evidence_json:
                    try:
                        ev_data = json.loads(report_obj.evidence_json)
                    except Exception:
                        pass
                report_info = {
                    "id": report_obj.id,
                    "meter_id": report_obj.meter_id,
                    "alert_id": report_obj.alert_id,
                    "sequence_id": seq_record.id,
                    "model_used": report_obj.model_used,
                    "created_at": report_obj.created_at.isoformat() if report_obj.created_at else None,
                    "report_markdown": report_obj.report_markdown,
                    "evidence": ev_data,
                }

        return {
            "status": "success",
            "meter_id": meter_id,
            "scenario": scenario,
            "scenario_name": sim["scenario_name"],
            "sequence_id": seq_record.id,
            "is_simulated": True,
            "simulated_at": sim["simulated_at"],
            "sequence_length": 30,
            "consumption": sim["consumption"],
            "stats": sim["stats"],
            "lstm_result": lstm,
            "alert": alert_info,
            "report": report_info,
        }
    except Exception as exc:
        db.rollback()
        logger.error("Simulation failed for meter %s: %s", meter_id, exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Simulation failed: {exc}"},
        )
    finally:
        db.close()
