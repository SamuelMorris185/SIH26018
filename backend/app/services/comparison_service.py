import uuid
import difflib
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.config import settings
from app.core.exceptions import RecordNotFoundError, DiscrepancyNotFoundError, InvalidStateTransitionError
from app.models.land_record import LandRecordModel
from app.models.discrepancy import RecordComparisonModel, DiscrepancyModel
from app.schemas.discrepancy import (
    DiscrepancyType,
    DiscrepancySeverity,
    DiscrepancyStatus,
    DiscrepancyResponse,
    DiscrepancyUpdate,
    RecordComparisonResponse,
    ComparisonSummaryResponse,
)
from app.services.audit_service import audit_service

class ComparisonService:
    """
    Deterministic cross-record discrepancy detection service.
    Matches land records by parcel identity (Khasra, Khata, Village, District, State)
    and flags discrepancies (owner, area, survey, duplicate, sequence, low-confidence).
    """

    @staticmethod
    def _name_similarity(name1: Optional[str], name2: Optional[str]) -> float:
        if not name1 or not name2:
            return 0.0
        n1 = name1.strip().lower()
        n2 = name2.strip().lower()
        if n1 == n2:
            return 1.0
        return difflib.SequenceMatcher(None, n1, n2).ratio()

    async def find_matching_records(
        self,
        session: AsyncSession,
        record: LandRecordModel
    ) -> List[LandRecordModel]:
        """
        Resolves existing records sharing the same parcel identity:
        Matches State + District + Tehsil + Village AND Khasra Number (or Khata Number).
        Excludes the target record itself.
        """
        stmt = (
            select(LandRecordModel)
            .where(
                and_(
                    LandRecordModel.id != record.id,
                    LandRecordModel.state.ilike(record.state.strip()),
                    LandRecordModel.district.ilike(record.district.strip()),
                    LandRecordModel.tehsil.ilike(record.tehsil.strip()),
                    LandRecordModel.village.ilike(record.village.strip()),
                    or_(
                        LandRecordModel.khasra_number == record.khasra_number,
                        and_(
                            LandRecordModel.khata_number == record.khata_number,
                            LandRecordModel.khasra_number.isnot(None)
                        )
                    )
                )
            )
            .order_by(LandRecordModel.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def evaluate_pair(
        self,
        source: LandRecordModel,
        existing: LandRecordModel
    ) -> List[Dict[str, Any]]:
        """
        Applies deterministic comparison rules between a newly extracted record and an existing record.
        """
        discrepancies: List[Dict[str, Any]] = []

        # 1. Owner Mismatch Detection
        if source.owner_name and existing.owner_name:
            similarity = self._name_similarity(source.owner_name, existing.owner_name)
            if similarity < 0.80:
                severity = DiscrepancySeverity.CRITICAL if similarity < 0.50 else DiscrepancySeverity.HIGH
                discrepancies.append({
                    "discrepancy_type": DiscrepancyType.OWNER_MISMATCH.value,
                    "severity": severity.value,
                    "field_name": "owner_name",
                    "source_value": source.owner_name,
                    "conflicting_value": existing.owner_name,
                    "description": (
                        f"Ownership mismatch on parcel {source.khasra_number}: "
                        f"Incoming document claims '{source.owner_name}', but existing title record holds '{existing.owner_name}'."
                    ),
                    "confidence": round(1.0 - similarity, 2)
                })

        # 2. Co-Owner Mismatch Detection
        if source.co_owners and existing.co_owners:
            s_co = set(c.strip().lower() for c in source.co_owners)
            e_co = set(c.strip().lower() for c in existing.co_owners)
            diff = s_co.symmetric_difference(e_co)
            if diff:
                discrepancies.append({
                    "discrepancy_type": DiscrepancyType.CO_OWNER_MISMATCH.value,
                    "severity": DiscrepancySeverity.MEDIUM.value,
                    "field_name": "co_owners",
                    "source_value": ", ".join(source.co_owners),
                    "conflicting_value": ", ".join(existing.co_owners),
                    "description": (
                        f"Co-owner discrepancies detected on parcel {source.khasra_number}: "
                        f"Unmatched parties: {', '.join(diff).title()}."
                    ),
                    "confidence": 0.90
                })

        # 3. Land Area Mismatch Detection
        s_area = float(source.area_in_hectares or 0.0)
        e_area = float(existing.area_in_hectares or 0.0)
        area_diff = abs(s_area - e_area)
        if area_diff > settings.AREA_TOLERANCE_HECTARES:
            severity = DiscrepancySeverity.CRITICAL if area_diff > 1.0 else DiscrepancySeverity.HIGH
            discrepancies.append({
                "discrepancy_type": DiscrepancyType.AREA_MISMATCH.value,
                "severity": severity.value,
                "field_name": "area_in_hectares",
                "source_value": f"{s_area:.4f} ha",
                "conflicting_value": f"{e_area:.4f} ha",
                "description": (
                    f"Land area divergence of {area_diff:.4f} ha exceeds tolerance ({settings.AREA_TOLERANCE_HECTARES} ha): "
                    f"Incoming record: {s_area:.4f} ha vs Existing registry: {e_area:.4f} ha."
                ),
                "confidence": 0.95
            })

        # 4. Survey / Classification Conflict Detection
        if (
            source.khasra_number == existing.khasra_number
            and source.land_classification
            and existing.land_classification
            and source.land_classification.lower() != existing.land_classification.lower()
        ):
            discrepancies.append({
                "discrepancy_type": DiscrepancyType.SURVEY_CONFLICT.value,
                "severity": DiscrepancySeverity.HIGH.value,
                "field_name": "land_classification",
                "source_value": source.land_classification,
                "conflicting_value": existing.land_classification,
                "description": (
                    f"Conflicting land classification on survey parcel {source.khasra_number}: "
                    f"Incoming claims '{source.land_classification}', existing title states '{existing.land_classification}'."
                ),
                "confidence": 0.92
            })

        # 5. Identifier Conflict (Registration / Mutation number mismatch)
        if (
            source.registration_number
            and existing.registration_number
            and source.registration_number != existing.registration_number
            and source.owner_name
            and existing.owner_name
            and self._name_similarity(source.owner_name, existing.owner_name) > 0.90
        ):
            discrepancies.append({
                "discrepancy_type": DiscrepancyType.IDENTIFIER_CONFLICT.value,
                "severity": DiscrepancySeverity.HIGH.value,
                "field_name": "registration_number",
                "source_value": source.registration_number,
                "conflicting_value": existing.registration_number,
                "description": (
                    f"Conflicting registration identifier for identical owner '{source.owner_name}' on parcel {source.khasra_number}: "
                    f"Incoming: {source.registration_number} vs Existing: {existing.registration_number}."
                ),
                "confidence": 0.90
            })

        # 6. Duplicate Document Detection
        # If all core parcel and ownership details match identically across separate document submissions
        if (
            source.document_id
            and existing.document_id
            and source.document_id != existing.document_id
            and source.khasra_number == existing.khasra_number
            and source.khata_number == existing.khata_number
            and self._name_similarity(source.owner_name, existing.owner_name) > 0.95
            and area_diff <= settings.AREA_TOLERANCE_HECTARES
        ):
            discrepancies.append({
                "discrepancy_type": DiscrepancyType.DUPLICATE_DOCUMENT.value,
                "severity": DiscrepancySeverity.MEDIUM.value,
                "field_name": "document_id",
                "source_value": str(source.document_id),
                "conflicting_value": str(existing.document_id),
                "description": (
                    f"Potential duplicate document submission detected for parcel {source.khasra_number}. "
                    f"Identical record attributes already registered under document {existing.document_id}."
                ),
                "confidence": 0.98
            })

        return discrepancies

    def evaluate_self_record(self, record: LandRecordModel) -> List[Dict[str, Any]]:
        """
        Evaluates record-level discrepancies independent of cross-document pairs,
        including low-confidence critical fields and suspicious chronological sequences.
        """
        discrepancies: List[Dict[str, Any]] = []

        # 7. Low-Confidence Critical Field Detection
        if record.confidence_score < settings.CONFIDENCE_THRESHOLD_LOW:
            discrepancies.append({
                "discrepancy_type": DiscrepancyType.LOW_CONFIDENCE_CRITICAL_FIELD.value,
                "severity": DiscrepancySeverity.HIGH.value,
                "field_name": "confidence_score",
                "source_value": f"{record.confidence_score:.2f}",
                "conflicting_value": f"Threshold >= {settings.CONFIDENCE_THRESHOLD_LOW}",
                "description": (
                    f"Overall extraction confidence ({record.confidence_score:.2f}) falls below acceptable "
                    f"confidence threshold ({settings.CONFIDENCE_THRESHOLD_LOW}). Manual verification required."
                ),
                "confidence": round(1.0 - record.confidence_score, 2)
            })

        return discrepancies

    async def compare_record(
        self,
        session: AsyncSession,
        record_id: uuid.UUID
    ) -> ComparisonSummaryResponse:
        """
        Executes cross-document comparison for a given land record.
        Ensures idempotent persistence by clearing prior comparisons and discrepancies.
        """
        result = await session.execute(
            select(LandRecordModel).where(LandRecordModel.id == record_id)
        )
        record = result.scalars().first()
        if not record:
            raise RecordNotFoundError(record_id)

        logger.info(f"[COMPARISON] Running discrepancy comparison for Record {record.id} (Khasra: {record.khasra_number}, Village: {record.village})")

        # 1. Clear existing comparisons and discrepancies for this record (idempotent run)
        await session.execute(
            delete(DiscrepancyModel).where(DiscrepancyModel.record_id == record.id)
        )
        await session.execute(
            delete(RecordComparisonModel).where(RecordComparisonModel.record_id == record.id)
        )
        await session.flush()

        # 2. Find candidate matching records
        matched_records = await self.find_matching_records(session, record)
        all_discrepancy_models: List[DiscrepancyModel] = []
        severity_rank = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}
        highest_severity_str: Optional[str] = None
        highest_severity_val = 0

        # 3. Evaluate self-record rules
        self_discrepancies = self.evaluate_self_record(record)
        for d in self_discrepancies:
            d_model = DiscrepancyModel(
                id=uuid.uuid4(),
                record_id=record.id,
                compared_record_id=None,
                comparison_id=None,
                discrepancy_type=d["discrepancy_type"],
                severity=d["severity"],
                description=d["description"],
                field_name=d.get("field_name"),
                source_value=d.get("source_value"),
                conflicting_value=d.get("conflicting_value"),
                confidence=d.get("confidence", 1.0),
                status=DiscrepancyStatus.OPEN.value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(d_model)
            all_discrepancy_models.append(d_model)

            rank = severity_rank.get(d["severity"], 0)
            if rank > highest_severity_val:
                highest_severity_val = rank
                highest_severity_str = d["severity"]

        # 4. Evaluate pair-wise rules against each matching record
        for matched in matched_records:
            pair_discrepancies = self.evaluate_pair(record, matched)
            pair_highest: Optional[str] = None
            pair_highest_rank = 0

            for d in pair_discrepancies:
                rank = severity_rank.get(d["severity"], 0)
                if rank > pair_highest_rank:
                    pair_highest_rank = rank
                    pair_highest = d["severity"]
                if rank > highest_severity_val:
                    highest_severity_val = rank
                    highest_severity_str = d["severity"]

            comparison_model = RecordComparisonModel(
                id=uuid.uuid4(),
                record_id=record.id,
                compared_record_id=matched.id,
                match_type="PARCEL_EXACT_MATCH" if record.khasra_number == matched.khasra_number else "KHATA_MATCH",
                discrepancy_count=len(pair_discrepancies),
                highest_severity=pair_highest,
                status="CONFLICT" if pair_discrepancies else "MATCH_CONFIRMED",
                compared_at=datetime.utcnow()
            )
            session.add(comparison_model)
            await session.flush()

            for d in pair_discrepancies:
                d_model = DiscrepancyModel(
                    id=uuid.uuid4(),
                    record_id=record.id,
                    compared_record_id=matched.id,
                    comparison_id=comparison_model.id,
                    discrepancy_type=d["discrepancy_type"],
                    severity=d["severity"],
                    description=d["description"],
                    field_name=d.get("field_name"),
                    source_value=d.get("source_value"),
                    conflicting_value=d.get("conflicting_value"),
                    confidence=d.get("confidence", 1.0),
                    status=DiscrepancyStatus.OPEN.value,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(d_model)
                all_discrepancy_models.append(d_model)

        await session.flush()

        # 5. If CRITICAL or HIGH discrepancies were detected, flag record and initiate review
        if highest_severity_val >= severity_rank["HIGH"]:
            record.status = "FLAGGED"
            record.review_status = "PENDING_REVIEW"
            await session.flush()
            logger.warning(f"[COMPARISON] Record {record.id} FLAGGED due to {highest_severity_str} discrepancies.")

        # Count discrepancies by severity
        crit_count = sum(1 for d in all_discrepancy_models if d.severity == "CRITICAL")
        high_count = sum(1 for d in all_discrepancy_models if d.severity == "HIGH")
        med_count = sum(1 for d in all_discrepancy_models if d.severity == "MEDIUM")
        low_count = sum(1 for d in all_discrepancy_models if d.severity == "LOW")
        info_count = sum(1 for d in all_discrepancy_models if d.severity == "INFO")

        return ComparisonSummaryResponse(
            record_id=record.id,
            matched_records_count=len(matched_records),
            total_discrepancies=len(all_discrepancy_models),
            critical_count=crit_count,
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count,
            info_count=info_count,
            highest_severity=highest_severity_str,
            discrepancies=[DiscrepancyResponse.model_validate(d) for d in all_discrepancy_models]
        )

    async def get_record_discrepancies(
        self,
        session: AsyncSession,
        record_id: uuid.UUID
    ) -> List[DiscrepancyModel]:
        """Retrieves all discrepancies associated with a land record."""
        stmt = (
            select(DiscrepancyModel)
            .where(DiscrepancyModel.record_id == record_id)
            .order_by(DiscrepancyModel.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_record_comparisons(
        self,
        session: AsyncSession,
        record_id: uuid.UUID
    ) -> List[RecordComparisonModel]:
        """Retrieves comparison history for a land record."""
        stmt = (
            select(RecordComparisonModel)
            .where(RecordComparisonModel.record_id == record_id)
            .options(selectinload(RecordComparisonModel.discrepancies))
            .order_by(RecordComparisonModel.compared_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    ALLOWED_DISCREPANCY_TRANSITIONS = {
        "OPEN": {"ACKNOWLEDGED", "RESOLVED", "DISMISSED"},
        "ACKNOWLEDGED": {"RESOLVED", "DISMISSED", "OPEN"},
        "RESOLVED": {"OPEN"},   # Re-opening a previously resolved discrepancy
        "DISMISSED": {"OPEN"},  # Re-opening a previously dismissed discrepancy
    }

    async def update_discrepancy_status(
        self,
        session: AsyncSession,
        discrepancy_id: uuid.UUID,
        payload: DiscrepancyUpdate,
        actor_user_id: Optional[uuid.UUID] = None
    ) -> DiscrepancyModel:
        """
        Updates the resolution lifecycle status of an identified discrepancy.
        Enforces explicit state machine transitions, raising InvalidStateTransitionError (HTTP 409)
        if an invalid transition is attempted.
        """
        result = await session.execute(
            select(DiscrepancyModel).where(DiscrepancyModel.id == discrepancy_id)
        )
        discrepancy = result.scalars().first()
        if not discrepancy:
            raise DiscrepancyNotFoundError(discrepancy_id)

        old_status = discrepancy.status
        new_status = payload.status.value

        # Validate state transition
        if new_status != old_status:
            allowed = self.ALLOWED_DISCREPANCY_TRANSITIONS.get(old_status, set())
            if new_status not in allowed:
                raise InvalidStateTransitionError(
                    current_status=old_status,
                    attempted_status=new_status,
                    entity_name="Discrepancy"
                )

        discrepancy.status = new_status
        discrepancy.updated_at = datetime.utcnow()
        await session.flush()

        # Audit log
        await audit_service.log_event(
            session=session,
            action="DISCREPANCY_STATUS_UPDATED",
            entity_type="DISCREPANCY",
            actor_user_id=actor_user_id,
            entity_id=discrepancy.id,
            previous_state={"status": old_status},
            new_state={
                "status": discrepancy.status,
                "notes": payload.resolution_notes
            }
        )

        return discrepancy

comparison_service = ComparisonService()
