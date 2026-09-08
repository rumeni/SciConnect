"""Finding any named record by a fragment of its name.

This is a navigation aid rather than a capability search: it answers "what is
called something like this", across every kind of record the detail views can
open. Each kind is matched on its own name only, so an analysis type and the
offerings named after it stay separate entries instead of duplicating.

Like the detail views, it does not hide archived or unavailable records; the
note says so instead, because being unable to find a draft you just created
would be worse than seeing its status.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.orm import Session

from app.modules.catalog.models import (
    AnalysisType,
    Institution,
    InstitutionAnalysis,
    InstitutionInstrument,
    InstrumentType,
    Microorganism,
    Researcher,
)
from app.modules.catalog.schemas import EntityMatch, EntitySearchResponse

# The state each kind is in when there is nothing worth remarking on.
_UNREMARKABLE = {"active", "operational", "available"}


def _contains(column: ColumnElement[str | None], term: str) -> ColumnElement[bool]:
    """Case-insensitive substring match, with LIKE's own wildcards defused."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")


def _note(*parts: str | None) -> str | None:
    kept = [part for part in parts if part]
    return " · ".join(kept) or None


def _status_note(status: str) -> str | None:
    return None if status in _UNREMARKABLE else status


def find_entities(db: Session, term: str, *, limit: int = 20) -> EntitySearchResponse:
    term = term.strip()
    if not term:
        return EntitySearchResponse(query=term, items=[], truncated=False)

    matches: list[EntityMatch] = []
    # Each kind is capped on its own, so one crowded kind cannot fill the answer.
    per_kind = limit

    for institution in db.scalars(
        select(Institution)
        .where(_contains(Institution.name, term))
        .order_by(Institution.name)
        .limit(per_kind)
    ):
        matches.append(
            EntityMatch(
                kind="institution",
                id=institution.id,
                label=institution.name,
                note=_note(
                    f"{institution.city}, {institution.country}",
                    _status_note(institution.status),
                ),
            )
        )

    for instrument_type in db.scalars(
        select(InstrumentType)
        .where(_contains(InstrumentType.name, term))
        .order_by(InstrumentType.name)
        .limit(per_kind)
    ):
        matches.append(
            EntityMatch(
                kind="instrument-type",
                id=instrument_type.id,
                label=instrument_type.name,
                note=None,
            )
        )

    for analysis_type in db.scalars(
        select(AnalysisType)
        .where(_contains(AnalysisType.name, term))
        .order_by(AnalysisType.name)
        .limit(per_kind)
    ):
        matches.append(
            EntityMatch(
                kind="analysis-type",
                id=analysis_type.id,
                label=analysis_type.name,
                note=None,
            )
        )

    for organism in db.scalars(
        select(Microorganism)
        .where(
            or_(
                _contains(Microorganism.scientific_name, term),
                _contains(Microorganism.common_name, term),
            )
        )
        .order_by(Microorganism.scientific_name)
        .limit(per_kind)
    ):
        matches.append(
            EntityMatch(
                kind="microorganism",
                id=organism.id,
                label=organism.scientific_name,
                note=organism.common_name,
            )
        )

    people = db.execute(
        select(Researcher, Institution.name)
        .join(Institution, Researcher.institution_id == Institution.id)
        .where(_contains(Researcher.full_name, term))
        .order_by(Researcher.full_name)
        .limit(per_kind)
    )
    for researcher, institution_name in people:
        matches.append(
            EntityMatch(
                kind="researcher",
                id=researcher.id,
                label=researcher.full_name,
                note=_note(
                    researcher.title, institution_name, _status_note(researcher.status)
                ),
            )
        )

    instruments = db.execute(
        select(InstitutionInstrument, Institution.name, InstrumentType.name)
        .join(Institution, InstitutionInstrument.institution_id == Institution.id)
        .join(
            InstrumentType,
            InstitutionInstrument.instrument_type_id == InstrumentType.id,
        )
        .where(_contains(InstitutionInstrument.display_name, term))
        .order_by(InstitutionInstrument.display_name)
        .limit(per_kind)
    )
    for instrument, institution_name, type_name in instruments:
        matches.append(
            EntityMatch(
                kind="instrument",
                id=instrument.id,
                label=instrument.display_name or type_name,
                note=_note(
                    type_name, institution_name, _status_note(instrument.status)
                ),
            )
        )

    offerings = db.execute(
        select(InstitutionAnalysis, Institution.name, AnalysisType.name)
        .join(Institution, InstitutionAnalysis.institution_id == Institution.id)
        .join(AnalysisType, InstitutionAnalysis.analysis_type_id == AnalysisType.id)
        .where(_contains(InstitutionAnalysis.public_name, term))
        .order_by(InstitutionAnalysis.public_name)
        .limit(per_kind)
    )
    for offering, institution_name, type_name in offerings:
        matches.append(
            EntityMatch(
                kind="analysis",
                id=offering.id,
                label=offering.public_name or type_name,
                note=_note(
                    institution_name, _status_note(offering.availability)
                ),
            )
        )

    matches.sort(key=lambda match: _rank(match.label, term))
    return EntitySearchResponse(
        query=term,
        items=matches[:limit],
        truncated=len(matches) > limit,
    )


def _rank(label: str, term: str) -> tuple[int, str]:
    """A name that starts with what was typed is the more likely target."""
    lowered = label.lower()
    needle = term.lower()
    if lowered.startswith(needle):
        return (0, lowered)
    if any(word.startswith(needle) for word in lowered.split()):
        return (1, lowered)
    return (2, lowered)
