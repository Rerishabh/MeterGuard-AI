"""
MeterGuard AI: SQLAlchemy ORM Models
Defines schema for Meters, Telemetry Readings, Consumption Sequences, Anomaly Alerts, and Investigation Reports.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from backend.database.base import Base


class Meter(Base):
    """
    Physical or synthetic smart meter entity.
    Serves as the root parent entity for readings, sequences, alerts, and reports.
    """
    __tablename__ = "meters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meter_id = Column(String(64), unique=True, index=True, nullable=False)
    location_name = Column(String(128), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(String(32), default="MONITORING", nullable=False)
    priority = Column(String(16), default="LOW", nullable=False)
    is_online = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    hardware_readings = relationship(
        "HardwareReading",
        back_populates="meter",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    consumption_sequences = relationship(
        "ConsumptionSequence",
        back_populates="meter",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    anomaly_alerts = relationship(
        "AnomalyAlert",
        back_populates="meter",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    investigation_reports = relationship(
        "InvestigationReport",
        back_populates="meter",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Meter(id={self.id}, meter_id='{self.meter_id}', status='{self.status}')>"


class HardwareReading(Base):
    """
    High-frequency hardware sensor telemetry (approx. 100ms ESP32 recordings).
    Stores electrical channels, computed V/I/W, and Model 1 & 2 predictions.
    """
    __tablename__ = "hardware_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meter_id = Column(
        String(64),
        ForeignKey("meters.meter_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Sensor measurements
    t1_cs = Column(Float, nullable=True)
    t1_vs = Column(Float, nullable=True)
    t2_cs = Column(Float, nullable=True)
    t2_vs = Column(Float, nullable=True)
    h1_cs = Column(Float, nullable=True)
    h1_vs = Column(Float, nullable=True)

    # Calibrated electrical values
    voltage_v = Column(Float, nullable=True)
    current_a = Column(Float, nullable=True)
    power_w = Column(Float, nullable=True)

    # Classification outcomes
    model1_status = Column(String(32), nullable=True)
    model2_status = Column(String(32), nullable=True)
    final_status = Column(String(32), nullable=True)
    priority = Column(String(16), nullable=True)

    # Relationship to parent Meter
    meter = relationship("Meter", back_populates="hardware_readings")

    __table_args__ = (
        Index("idx_hw_meter_timestamp", "meter_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<HardwareReading(id={self.id}, meter_id='{self.meter_id}', status='{self.final_status}')>"


class ConsumptionSequence(Base):
    """
    Aggregated consumption sequences (Daily 30-day or Hourly 24-hour).
    Evaluated by LSTM Autoencoder Model 3.
    """
    __tablename__ = "consumption_sequences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meter_id = Column(
        String(64),
        ForeignKey("meters.meter_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_type = Column(String(16), nullable=False)  # 'daily' or 'hourly'
    sequence_length = Column(Integer, nullable=False)    # 30 or 24
    consumption_json = Column(Text, nullable=False)     # JSON serialized list of floats
    reconstruction_error = Column(Float, nullable=True)
    threshold_used = Column(Float, nullable=True)
    threshold_99 = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="NORMAL", nullable=False)
    is_simulated = Column(Boolean, default=False, nullable=False)
    scenario = Column(String(64), nullable=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    meter = relationship("Meter", back_populates="consumption_sequences")

    __table_args__ = (
        Index("idx_seq_meter_type", "meter_id", "sequence_type"),
    )

    def __repr__(self) -> str:
        return f"<ConsumptionSequence(id={self.id}, meter_id='{self.meter_id}', type='{self.sequence_type}', error={self.reconstruction_error})>"


class AnomalyAlert(Base):
    """
    Operational alerts triggered by any detection model or arbitration engine.
    """
    __tablename__ = "anomaly_alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meter_id = Column(
        String(64),
        ForeignKey("meters.meter_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_model = Column(String(64), nullable=False)
    fault_type = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    message = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    meter = relationship("Meter", back_populates="anomaly_alerts")
    investigation_reports = relationship(
        "InvestigationReport",
        back_populates="alert",
    )

    __table_args__ = (
        Index("idx_alert_meter_severity", "meter_id", "severity", "is_resolved"),
    )

    def __repr__(self) -> str:
        return f"<AnomalyAlert(id={self.id}, meter_id='{self.meter_id}', fault='{self.fault_type}', severity='{self.severity}')>"


class InvestigationReport(Base):
    """
    Forensic investigation report prepared for Phase 3B automated diagnostics.
    """
    __tablename__ = "investigation_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(
        Integer,
        ForeignKey("anomaly_alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    meter_id = Column(
        String(64),
        ForeignKey("meters.meter_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_markdown = Column(Text, nullable=False)
    model_used = Column(String(64), nullable=False)
    evidence_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    meter = relationship("Meter", back_populates="investigation_reports")
    alert = relationship("AnomalyAlert", back_populates="investigation_reports")

    def __repr__(self) -> str:
        return f"<InvestigationReport(id={self.id}, meter_id='{self.meter_id}', model='{self.model_used}')>"
