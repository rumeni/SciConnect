from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Institution(TimestampMixin, Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    instruments: Mapped[list[InstitutionInstrument]] = relationship(
        back_populates="institution", cascade="all, delete-orphan"
    )
    analyses: Mapped[list[InstitutionAnalysis]] = relationship(
        back_populates="institution", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'archived')", name="valid_status"),
        Index("ix_institutions_country_city", "country", "city"),
    )


class InstrumentType(TimestampMixin, Base):
    __tablename__ = "instrument_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    institution_instruments: Mapped[list[InstitutionInstrument]] = relationship(
        back_populates="instrument_type"
    )


class InstitutionInstrument(TimestampMixin, Base):
    __tablename__ = "institution_instruments"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    instrument_type_id: Mapped[int] = mapped_column(
        ForeignKey("instrument_types.id", ondelete="RESTRICT"), nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(200))
    manufacturer: Mapped[str | None] = mapped_column(String(160))
    model: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="operational")
    access_notes: Mapped[str | None] = mapped_column(Text)

    institution: Mapped[Institution] = relationship(back_populates="instruments")
    instrument_type: Mapped[InstrumentType] = relationship(
        back_populates="institution_instruments"
    )
    analysis_links: Mapped[list[InstitutionAnalysisInstrument]] = relationship(
        back_populates="institution_instrument",
        cascade="all, delete-orphan",
        overlaps="institution_analysis,instrument_links",
    )

    __table_args__ = (
        UniqueConstraint("id", "institution_id", name="uq_instrument_same_institution"),
        CheckConstraint(
            "status IN ('operational', 'maintenance', 'unavailable', 'archived')",
            name="valid_status",
        ),
        Index("ix_institution_instruments_type", "instrument_type_id", "institution_id"),
    )


class AnalysisType(TimestampMixin, Base):
    __tablename__ = "analysis_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    institution_analyses: Mapped[list[InstitutionAnalysis]] = relationship(
        back_populates="analysis_type"
    )


class InstitutionAnalysis(TimestampMixin, Base):
    __tablename__ = "institution_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    analysis_type_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_types.id", ondelete="RESTRICT"), nullable=False
    )
    public_name: Mapped[str | None] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    turnaround_days: Mapped[int | None]
    availability: Mapped[str] = mapped_column(String(20), nullable=False, default="available")

    institution: Mapped[Institution] = relationship(back_populates="analyses")
    analysis_type: Mapped[AnalysisType] = relationship(back_populates="institution_analyses")
    instrument_links: Mapped[list[InstitutionAnalysisInstrument]] = relationship(
        back_populates="institution_analysis",
        cascade="all, delete-orphan",
        overlaps="analysis_links,institution_instrument",
    )
    target_links: Mapped[list[InstitutionAnalysisTarget]] = relationship(
        back_populates="institution_analysis", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("id", "institution_id", name="uq_analysis_same_institution"),
        UniqueConstraint(
            "institution_id", "analysis_type_id", name="uq_institution_analysis_type"
        ),
        CheckConstraint("turnaround_days IS NULL OR turnaround_days > 0", name="positive_days"),
        CheckConstraint(
            "availability IN ('available', 'limited', 'unavailable', 'archived')",
            name="valid_availability",
        ),
        Index("ix_institution_analyses_type", "analysis_type_id", "institution_id"),
    )


class InstitutionAnalysisInstrument(Base):
    __tablename__ = "institution_analysis_instruments"

    institution_analysis_id: Mapped[int] = mapped_column(primary_key=True)
    institution_instrument_id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(nullable=False)
    usage: Mapped[str] = mapped_column(String(20), nullable=False, default="required")

    institution_analysis: Mapped[InstitutionAnalysis] = relationship(
        back_populates="instrument_links",
        foreign_keys=[institution_analysis_id, institution_id],
        overlaps="analysis_links,institution_instrument",
    )
    institution_instrument: Mapped[InstitutionInstrument] = relationship(
        back_populates="analysis_links",
        foreign_keys=[institution_instrument_id, institution_id],
        overlaps="institution_analysis,instrument_links",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_analysis_id", "institution_id"],
            ["institution_analyses.id", "institution_analyses.institution_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["institution_instrument_id", "institution_id"],
            ["institution_instruments.id", "institution_instruments.institution_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("usage IN ('required', 'optional', 'alternative')", name="valid_usage"),
    )


class Microorganism(TimestampMixin, Base):
    __tablename__ = "microorganisms"

    id: Mapped[int] = mapped_column(primary_key=True)
    scientific_name: Mapped[str] = mapped_column(String(240), nullable=False, unique=True)
    common_name: Mapped[str | None] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)

    analysis_links: Mapped[list[InstitutionAnalysisTarget]] = relationship(
        back_populates="microorganism"
    )


class InstitutionAnalysisTarget(Base):
    __tablename__ = "institution_analysis_targets"

    institution_analysis_id: Mapped[int] = mapped_column(
        ForeignKey("institution_analyses.id", ondelete="CASCADE"), primary_key=True
    )
    microorganism_id: Mapped[int] = mapped_column(
        ForeignKey("microorganisms.id", ondelete="RESTRICT"), primary_key=True
    )

    institution_analysis: Mapped[InstitutionAnalysis] = relationship(
        back_populates="target_links"
    )
    microorganism: Mapped[Microorganism] = relationship(back_populates="analysis_links")
