"""
MeterGuard AI: Investigation Report Generator Service (Phase 3B)
Gathers structured MySQL evidence and generates evidence-grounded forensic investigation reports
using Gemini 2.5 Flash with a robust, deterministic fallback.
"""

import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.db_models import (
    Meter,
    HardwareReading,
    ConsumptionSequence,
    AnomalyAlert,
    InvestigationReport,
)

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "You are an electricity utility forensic investigation assistant. "
    "Analyze only the structured telemetry and ML evidence supplied to you. "
    "Never invent sensor readings, reconstruction errors, dates, customer identities, or model predictions. "
    "Do not override the ML system's anomaly classification. "
    "Ensure complete internal consistency: all numerical metrics (Reconstruction MSE, thresholds, sensor ADCs) "
    "cited in Executive Summary must match Observed Evidence exactly. "
    "Distinguish measured evidence from possible explanations. "
    "Treat all root causes as hypotheses requiring field verification."
)


class InvestigationGenerator:
    """
    Evidence-grounded forensic report generator for electricity utility tampering investigations.
    """

    def collect_evidence(
        self,
        db: Session,
        meter_id: str,
        alert_id: Optional[int] = None,
        sequence_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Gathers actual persisted evidence from MySQL for the specified meter, optional alert, and sequence.
        Deterministic querying uses auto-increment ID ordering to prevent timezone/clock skew errors.
        """
        # A. Meter Information
        meter = db.query(Meter).filter(Meter.meter_id == meter_id).first()
        if not meter:
            return None, f"Meter '{meter_id}' not found in database."

        meter_info = {
            "meter_id": meter.meter_id,
            "location_name": meter.location_name or f"Sector-{meter.meter_id}",
            "latitude": meter.latitude,
            "longitude": meter.longitude,
            "status": meter.status,
            "priority": meter.priority,
            "is_online": meter.is_online,
            "last_seen": meter.last_seen.isoformat() if meter.last_seen else None,
        }

        # B. Consumption Sequence Information (Targeted or Latest by ID)
        if sequence_id is not None:
            latest_seq = (
                db.query(ConsumptionSequence)
                .filter(
                    ConsumptionSequence.id == sequence_id,
                    ConsumptionSequence.meter_id == meter_id,
                )
                .first()
            )
        else:
            latest_seq = (
                db.query(ConsumptionSequence)
                .filter(ConsumptionSequence.meter_id == meter_id)
                .order_by(ConsumptionSequence.id.desc())
                .first()
            )

        consumption_info = None
        if latest_seq:
            try:
                raw_seq = json.loads(latest_seq.consumption_json)
                arr = np.array(raw_seq, dtype=float)
                stats = {
                    "min_kwh": round(float(np.min(arr)), 3),
                    "max_kwh": round(float(np.max(arr)), 3),
                    "mean_kwh": round(float(np.mean(arr)), 3),
                    "std_kwh": round(float(np.std(arr)), 3),
                }
                if len(arr) >= 20 and stats["mean_kwh"] > 0:
                    first_half = float(np.mean(arr[: len(arr) // 2]))
                    second_half = float(np.mean(arr[len(arr) // 2 :]))
                    if first_half > 0:
                        stats["drop_percentage"] = round(((first_half - second_half) / first_half) * 100, 1)
                    else:
                        stats["drop_percentage"] = 0.0
                else:
                    stats["drop_percentage"] = None
            except Exception as e:
                logger.warning("Could not parse consumption_json: %s", e)
                raw_seq = []
                stats = {"min_kwh": None, "max_kwh": None, "mean_kwh": None, "std_kwh": None, "drop_percentage": None}

            consumption_info = {
                "sequence_id": latest_seq.id,
                "sequence_type": latest_seq.sequence_type,
                "sequence_length": latest_seq.sequence_length,
                "reconstruction_error": latest_seq.reconstruction_error,
                "threshold_used": latest_seq.threshold_used,
                "threshold_99": latest_seq.threshold_99,
                "is_anomaly": latest_seq.is_anomaly,
                "status": latest_seq.status,
                "is_simulated": latest_seq.is_simulated,
                "scenario": getattr(latest_seq, "scenario", None),
                "analyzed_at": latest_seq.analyzed_at.isoformat() if latest_seq.analyzed_at else None,
                "stats": stats,
                "sample_values": raw_seq[:10] if raw_seq else [],
            }

        # C. Hardware Information (Latest by ID)
        latest_hw = (
            db.query(HardwareReading)
            .filter(HardwareReading.meter_id == meter_id)
            .order_by(HardwareReading.id.desc())
            .first()
        )

        hardware_info = None
        if latest_hw:
            hardware_info = {
                "reading_id": latest_hw.id,
                "timestamp": latest_hw.timestamp.isoformat() if latest_hw.timestamp else None,
                "sensors": {
                    "T1_CS": latest_hw.t1_cs,
                    "T1_VS": latest_hw.t1_vs,
                    "T2_CS": latest_hw.t2_cs,
                    "T2_VS": latest_hw.t2_vs,
                    "H1_CS": latest_hw.h1_cs,
                    "H1_VS": latest_hw.h1_vs,
                },
                "electrical": {
                    "voltage_V": latest_hw.voltage_v,
                    "current_A": latest_hw.current_a,
                    "power_W": latest_hw.power_w,
                },
                "model1_status": latest_hw.model1_status,
                "model2_status": latest_hw.model2_status,
                "final_status": latest_hw.final_status,
                "priority": latest_hw.priority,
            }

        # D. Alert Information
        alert_obj = None
        if alert_id:
            alert_obj = db.query(AnomalyAlert).filter(AnomalyAlert.id == alert_id).first()
        else:
            # Query unresolved alerts ordered by ID descending
            active_alerts = (
                db.query(AnomalyAlert)
                .filter(AnomalyAlert.meter_id == meter_id, AnomalyAlert.is_resolved == False)  # noqa: E712
                .order_by(AnomalyAlert.id.desc())
                .all()
            )
            for a_cand in active_alerts:
                # If sequence is normal, do not pair with a stale active LSTM alert
                if a_cand.source_model == "LSTM_Autoencoder" and latest_seq and not latest_seq.is_anomaly:
                    continue
                alert_obj = a_cand
                break

            if not alert_obj:
                # If no active alert matched, check latest alert overall
                latest_any_alert = (
                    db.query(AnomalyAlert)
                    .filter(AnomalyAlert.meter_id == meter_id)
                    .order_by(AnomalyAlert.id.desc())
                    .first()
                )
                if latest_any_alert:
                    # Only link if consistent with sequence or non-LSTM
                    if not (latest_any_alert.source_model == "LSTM_Autoencoder" and latest_seq and not latest_seq.is_anomaly):
                        alert_obj = latest_any_alert

        alert_info = None
        if alert_obj:
            alert_info = {
                "alert_id": alert_obj.id,
                "source_model": alert_obj.source_model,
                "fault_type": alert_obj.fault_type,
                "severity": alert_obj.severity,
                "message": alert_obj.message,
                "is_resolved": alert_obj.is_resolved,
                "created_at": alert_obj.created_at.isoformat() if alert_obj.created_at else None,
            }

        evidence = {
            "meter": meter_info,
            "consumption": consumption_info,
            "hardware": hardware_info,
            "alert": alert_info,
            "collected_at": datetime.utcnow().isoformat(),
        }

        return evidence, None

    def generate_deterministic_markdown(self, evidence: Dict[str, Any]) -> str:
        """
        Deterministic Markdown report generator based strictly on stored database evidence.
        Never fabricates measurements, timestamps, or customer identities.
        """
        m = evidence["meter"]
        c = evidence.get("consumption")
        h = evidence.get("hardware")
        a = evidence.get("alert")

        meter_id = m["meter_id"]
        status = m["status"]
        priority = m["priority"]
        loc = m.get("location_name") or "Distribution Grid Zone"

        # Severity & Model determination
        severity = a["severity"] if a else ("HIGH" if priority in ["HIGH", "CRITICAL"] else "MEDIUM" if priority == "MEDIUM" else "LOW")
        source_model = a["source_model"] if a else ("LSTM_Autoencoder" if c and c.get("is_anomaly") else "RandomForest" if h and h.get("model2_status") not in ["NORMAL", None] else "IsolationForest")
        is_sim = (c.get("is_simulated", False) if c else False)
        if is_sim:
            sim_badge = "SIMULATED DATASET"
        elif h and h.get("t1_cs") is not None:
            sim_badge = "HARDWARE REPLAY STREAM"
        else:
            sim_badge = "STORED SIMULATION"
        scenario_note = f" (Scenario: `{c.get('scenario')}`)" if c and c.get("scenario") else ""

        # Main finding - strictly ground on actual sequence and hardware evidence
        if a and not a["is_resolved"]:
            if a.get("source_model") == "LSTM_Autoencoder" and c:
                main_finding = (
                    f"Active time-series consumption anomaly confirmed by LSTM Autoencoder: **{a['fault_type']}** "
                    f"({a['severity']} severity). Reconstruction MSE: `{c['reconstruction_error']}` "
                    f"(Threshold: `{c['threshold_used']}`, Status: **{c['status']}**)."
                )
            else:
                main_finding = f"Active anomaly detected by {source_model}: **{a['fault_type']}** ({a['severity']} severity). {a.get('message', '')}"
        elif c and c.get("is_anomaly"):
            main_finding = (
                f"Time-series consumption anomaly confirmed by LSTM Autoencoder: "
                f"Reconstruction MSE `{c['reconstruction_error']}` exceeded active threshold `{c['threshold_used']}` "
                f"(Status: **{c['status']}**)."
            )
        elif h and h.get("model2_status") not in ["NORMAL", None]:
            main_finding = f"Hardware differential sensor anomaly flagged by Model 2 ({h['model2_status']})."
        else:
            mse_val = f" (Reconstruction MSE: `{c['reconstruction_error']}` vs Threshold: `{c['threshold_used']}`)" if c and c.get('reconstruction_error') is not None else ""
            main_finding = f"Meter {meter_id} operating under routine parameters. No active tampering or unverified deviations detected.{mse_val}"

        # Section 2 formatting
        if c:
            stats = c.get("stats", {})
            drop_str = f"- **Observed Drop:** {stats.get('drop_percentage')}%" if stats.get("drop_percentage") is not None else "- **Profile Variation:** Standard statistical dispersion"
            c_section = f"""- **Sequence Type:** {c['sequence_type'].capitalize()} ({c['sequence_length']} observations)
- **Reconstruction MSE:** `{c['reconstruction_error']}` vs. **Active Threshold (95th%):** `{c['threshold_used']}`
- **99th Percentile Threshold:** `{c.get('threshold_99', 'N/A')}`
- **LSTM Anomaly Classification:** **{c['status']}**
- **Consumption Range:** Min `{stats.get('min_kwh')} kWh`, Max `{stats.get('max_kwh')} kWh`, Mean `{stats.get('mean_kwh')} kWh`
{drop_str}
- **Dataset Provenance:** {sim_badge}{scenario_note}"""
        else:
            c_section = "*No consumption sequence evaluated for this meter yet (awaiting 30-day daily or 24-hour sequence ingestion).*"

        if h:
            sensors = h.get("sensors", {})
            elec = h.get("electrical", {})
            h_section = f"""- **Current / Voltage:** `{elec.get('current_A')} A` @ `{elec.get('voltage_V')} V` (Power: `{elec.get('power_W')} W`)
- **Raw Sensor ADCs:** T1 CS: `{sensors.get('T1_CS')}`, T2 CS: `{sensors.get('T2_CS')}`, H1 CS: `{sensors.get('H1_CS')}`
- **Model 1 (Isolation Forest):** `{h.get('model1_status')}`
- **Model 2 (Random Forest):** `{h.get('model2_status')}`
- **Arbitration Status:** `{h.get('final_status')}` (Priority: `{h.get('priority')}`)"""
        else:
            h_section = "*High-frequency hardware differential telemetry currently unavailable for this record.*"

        # Hypotheses based on evidence
        hypotheses = []
        if a and "FAULT_S1" in a.get("fault_type", ""):
            hypotheses.append("1. **Physical Meter Bypass (Shunt):** Sensor telemetry indicates transformer-to-house current differential consistent with an intentional phase bypass.")
        elif a and "FAULT_S2" in a.get("fault_type", ""):
            hypotheses.append("1. **Direct Line Tapping / Neutral Divert:** Differential measurements indicate secondary line tapping between pole transformer and customer service entrance.")
        elif c and c.get("is_anomaly"):
            if c.get("scenario") == "sudden_drop" or (c.get("stats", {}).get("drop_percentage") or 0) > 40:
                hypotheses.append("1. **Unregistered Load Reduction / Partial Bypass:** An abrupt drop in daily energy consumption without corresponding seasonal shifts suggests partial load diversion.")
            elif c.get("scenario") == "flatline":
                hypotheses.append("1. **Meter Mechanical Jamming / Shunted ADC:** Constant negligible consumption is indicative of a stuck register, defective current sensor, or static shunt resistor.")
            elif c.get("scenario") == "consumption_spike":
                hypotheses.append("1. **Faulty Grounding or Unauthorized Industrial Load:** Extreme consumption surges exceed nominal residential ratings, indicating intermittent short-circuit or illicit heavy equipment.")
            else:
                hypotheses.append("1. **Non-Technical Anomaly:** Sequential reconstruction failure identifies unusual usage patterns inconsistent with normal household demand profiles.")
        else:
            hypotheses.append("1. **Operational Baseline:** Verified telemetry reflects normal consumer usage within established statistical confidence bounds.")
            hypotheses.append("2. **Sensor Calibration:** Current calibration factors match expected nominal voltage/current standards.")

        if len(hypotheses) < 2:
            hypotheses.append("2. **Secondary Hypothesis (Hardware Drift):** Potential degradation or drift in local current transformer (CT) or voltage sensor wiring.")
        if len(hypotheses) < 3:
            hypotheses.append("3. **External Factor Hypothesis:** Legitimate premise vacancy, scheduled outage, or localized load modification.")

        hypotheses_str = "\n".join(hypotheses)

        # Markdown Assembly
        report = f"""# Forensic Investigation Report: Meter `{meter_id}`

### 1. Executive Summary
- **Target Meter:** `{meter_id}` ({loc})
- **Alert Severity:** `{severity}`
- **Detection System:** `{source_model}`
- **Operational Data Source:** **{sim_badge}**{scenario_note}
- **Primary Finding:** {main_finding}

---

### 2. Observed Consumption & Sensor Evidence

#### A. Time-Series Consumption Profile (LSTM Autoencoder)
{c_section}

#### B. Hardware Telemetry & Electrical Differentials
{h_section}

---

### 3. Technical Root-Cause Hypotheses
> *Notice: The following hypotheses are computer-generated diagnostic possibilities derived from empirical sensor telemetry. All hypotheses require on-site physical verification by authorized utility personnel.*

{hypotheses_str}

---

### 4. Prioritized Field Inspection Checklist
- [ ] **Physical Integrity:** Inspect meter enclosure, terminal block, security seals, and anti-tamper latch for signs of mechanical breach or cutting.
- [ ] **CT & Sensor Line Verification:** Measure physical current entering service drop with a calibrated clamp multimeter and compare against ADC telemetry (`H1_CS`).
- [ ] **Bypass & Shunt Inspection:** Examine neutral line and phase terminals for illicit bridging shunts, neutral disconnects, or secondary tapping cables.
- [ ] **Magnetic Field Testing:** Check for residual magnetization near the meter casing using a magnetic field indicator to test for external neodymium magnet tampering.
- [ ] **Voltage & Terminal Calibration:** Measure incoming terminal line voltage to confirm nominal reference (`230V ± 10%`).

---

### 5. Recommended Next Steps
1. **Field Technician Dispatch:** Schedule a **Priority {priority}** on-site audit for Meter `{meter_id}` at `{loc}`.
2. **Telemetry Polling:** Increase sampling frequency on upstream pole sensors (`T1`, `T2`) to monitor for persistent load imbalance.
3. **Forensic Archival:** Log this investigation record into utility dispatch database and cross-reference previous billing cycles.
4. **Resolution Protocol:** Following technician inspection, submit physical findings to clear or escalate active alert in the MeterGuard AI console.
"""
        return report.strip()

    def generate_report(
        self,
        db: Session,
        meter_id: str,
        alert_id: Optional[int] = None,
        sequence_id: Optional[int] = None,
    ) -> Tuple[Optional[InvestigationReport], Optional[str]]:
        """
        Generates an investigation report via Gemini GenAI if available,
        or deterministic fallback, and persists the record into MySQL.
        """
        evidence, err = self.collect_evidence(
            db, meter_id, alert_id=alert_id, sequence_id=sequence_id
        )
        if err or not evidence:
            return None, err or "Failed to gather evidence."

        api_key = settings.GEMINI_API_KEY
        use_gemini = bool(
            api_key
            and api_key.strip()
            and api_key.strip() != "your_gemini_api_key_here"
        )

        report_markdown = None
        model_used = "deterministic-fallback"

        if use_gemini:
            try:
                from google import genai
                from google.genai import types

                active_model = settings.GEMINI_MODEL
                c_data = evidence.get("consumption") or {}
                c_mse = c_data.get("reconstruction_error")
                c_thresh = c_data.get("threshold_used")
                c_stat = c_data.get("status", "NORMAL")
                c_scen = c_data.get("scenario", "none")

                client = genai.Client(
                    api_key=api_key.strip(),
                    http_options=types.HttpOptions(
                        timeout=15000,
                        retry_options=types.HttpRetryOptions(attempts=2),
                    ),
                )
                prompt = (
                    f"Analyze the following verified utility meter evidence and generate a formal investigation report.\n\n"
                    f"STRICT EVIDENCE DATA (JSON):\n"
                    f"```json\n{json.dumps(evidence, indent=2)}\n```\n\n"
                    f"CRITICAL EVIDENCE & CONSISTENCY RULES:\n"
                    f"1. In '### 1. Executive Summary' and '### 2. Observed Consumption & Sensor Evidence', you MUST cite the EXACT same Reconstruction MSE value (`{c_mse}`), active threshold (`{c_thresh}`), and anomaly status (`{c_stat}`). Never state conflicting or mismatched values across sections.\n"
                    f"2. State clearly whether operational data is SIMULATED (scenario: `{c_scen}`) or LIVE.\n"
                    f"3. Never invent sensor readings, errors, or override the ML system's anomaly classification.\n\n"
                    f"Generate a professional Markdown document with EXACTLY these five numbered section titles:\n"
                    f"### 1. Executive Summary\n"
                    f"### 2. Observed Consumption & Sensor Evidence\n"
                    f"### 3. Technical Root-Cause Hypotheses\n"
                    f"### 4. Prioritized Field Inspection Checklist\n"
                    f"### 5. Recommended Next Steps\n"
                )

                response = client.models.generate_content(
                    model=active_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.2,
                    ),
                )
                if response and response.text and len(response.text.strip()) > 100:
                    report_markdown = response.text.strip()
                    model_used = active_model
                    logger.info("Successfully generated report using %s", model_used)
            except Exception as exc:
                logger.warning(
                    "Gemini API generation failed (%s). Falling back to deterministic generator.",
                    exc,
                )
                report_markdown = None

        if not report_markdown:
            report_markdown = self.generate_deterministic_markdown(evidence)
            model_used = "deterministic-fallback"

        # Persist report to MySQL
        try:
            matched_alert_id = evidence["alert"]["alert_id"] if evidence.get("alert") else None
            db_report = InvestigationReport(
                alert_id=matched_alert_id,
                meter_id=meter_id,
                report_markdown=report_markdown,
                model_used=model_used,
                evidence_json=json.dumps(evidence),
                created_at=datetime.utcnow(),
            )
            db.add(db_report)
            db.commit()
            db.refresh(db_report)
            return db_report, None
        except Exception as exc:
            db.rollback()
            logger.error("Failed to persist InvestigationReport to MySQL: %s", exc)
            return None, f"Database error saving report: {exc}"


# Global singleton instance
investigation_generator = InvestigationGenerator()
