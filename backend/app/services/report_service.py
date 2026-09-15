import io
import re
import uuid
import html
from datetime import datetime, timezone
from typing import Tuple, Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from app.core.logging import logger
from app.core.config import settings
from app.schemas.extraction import categorize_confidence
from app.core.exceptions import RecordNotFoundError, ForbiddenError
from app.models.land_record import LandRecordModel
from app.models.document import DocumentModel
from app.models.extraction import ExtractionResultModel
from app.models.audit_log import AuditLogModel
from app.models.user import UserModel
from app.services.land_record_service import land_record_service
from app.services.audit_service import audit_service


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that computes total page count and draws consistent
    header rules, running titles, and 'Page X of Y' footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)

        # Header rule and running title
        self.line(36, A4[1] - 30, A4[0] - 36, A4[1] - 30)
        self.drawString(36, A4[1] - 25, "SIH26018 — Intelligent Land Record Digitization & Validation System")
        self.drawRightString(A4[0] - 36, A4[1] - 25, "RECORD VERIFICATION REPORT")

        # Footer rule and page numbers
        self.line(36, 35, A4[0] - 36, 35)
        self.drawString(36, 22, "Confidential & System-Generated • Not a Legal Title Certificate")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 22, page_str)
        self.restoreState()


def safe_text(val: Any) -> str:
    """Safely converts arbitrary values into XML-escaped strings for ReportLab Paragraphs."""
    if val is None or val == "":
        return "N/A"
    return html.escape(str(val))


class VerificationReportService:
    """
    Service generating on-demand, point-in-time PDF Verification Reports
    for land records using ReportLab.
    """

    def __init__(self):
        self._init_styles()

    def _init_styles(self):
        base_styles = getSampleStyleSheet()
        self.styles = base_styles

        self.title_style = ParagraphStyle(
            "ReportTitle",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a")
        )
        self.subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#475569")
        )
        self.section_heading = ParagraphStyle(
            "SectionHeading",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=8,
            spaceAfter=4
        )
        self.body_style = ParagraphStyle(
            "ReportBody",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b")
        )
        self.body_bold = ParagraphStyle(
            "ReportBodyBold",
            parent=self.body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f172a")
        )
        self.cell_header = ParagraphStyle(
            "CellHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#ffffff")
        )
        self.disclaimer_banner = ParagraphStyle(
            "DisclaimerBanner",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#92400e")
        )
        self.statutory_text = ParagraphStyle(
            "StatutoryText",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#334155")
        )

    async def generate_verification_pdf(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        current_user: UserModel
    ) -> Tuple[bytes, str]:
        """
        Builds a comprehensive Verification Report PDF for the requested land record.
        Returns (pdf_bytes, filename).
        """
        # 1. Fetch land record with all relationships
        query = (
            select(LandRecordModel)
            .where(LandRecordModel.id == record_id)
            .options(
                selectinload(LandRecordModel.document),
                selectinload(LandRecordModel.validation_results),
                selectinload(LandRecordModel.discrepancies),
                selectinload(LandRecordModel.comparisons),
                selectinload(LandRecordModel.parcel_location)
            )
        )
        result = await session.execute(query)
        record = result.scalars().first()
        if not record:
            raise RecordNotFoundError(record_id)

        # 2. Enforce ownership and access authorization
        land_record_service.check_record_access(record, current_user)

        # 3. Retrieve latest extraction result if document is present
        extraction: Optional[ExtractionResultModel] = None
        if record.document_id:
            ext_query = (
                select(ExtractionResultModel)
                .where(ExtractionResultModel.document_id == record.document_id)
                .order_by(desc(ExtractionResultModel.extracted_at))
            )
            ext_res = await session.execute(ext_query)
            extraction = ext_res.scalars().first()

        # 4. Fetch audit events related to this land record
        audit_query = (
            select(AuditLogModel)
            .where(
                AuditLogModel.entity_type == "LAND_RECORD",
                AuditLogModel.entity_id == record.id
            )
            .order_by(desc(AuditLogModel.created_at))
            .limit(8)
        )
        audit_res = await session.execute(audit_query)
        audit_logs = list(audit_res.scalars().all())

        # 5. Generate report metadata
        now_utc = datetime.utcnow()
        report_ref = f"VR-{now_utc.strftime('%Y%m%d')}-{record.id.hex[:8].upper()}"
        report_version = "v1.0"

        # 6. Build PDF document flowables
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=44,
            bottomMargin=48
        )

        story = []
        usable_width = A4[0] - 72 # 523.27 pt

        # --- Title & Header ---
        story.append(Paragraph("LAND RECORD VERIFICATION REPORT", self.title_style))
        story.append(Paragraph("Automated Extraction, Rule Validation & Discrepancy Cross-Examination", self.subtitle_style))
        story.append(Spacer(1, 8))

        # --- Prominent Disclaimer Notice Box ---
        disclaimer_p = Paragraph(
            "<b>SYSTEM-GENERATED VERIFICATION SUMMARY:</b> This document summarizes automated ingestion, OCR extraction, "
            "algorithmic rule validation, cross-record discrepancy analysis, and human review actions recorded in the system. "
            "<b>It is not, by itself, a government-issued title deed, legal ownership certificate, or final legal determination.</b>",
            self.disclaimer_banner
        )
        disclaimer_table = Table([[disclaimer_p]], colWidths=[usable_width])
        disclaimer_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(disclaimer_table)
        story.append(Spacer(1, 8))

        # --- Metadata Summary Bar ---
        meta_data = [
            [
                Paragraph("<b>Report Reference:</b>", self.body_style),
                Paragraph(safe_text(report_ref), self.body_bold),
                Paragraph("<b>Generated Timestamp:</b>", self.body_style),
                Paragraph(safe_text(now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")), self.body_style)
            ],
            [
                Paragraph("<b>Report Version:</b>", self.body_style),
                Paragraph(safe_text(report_version), self.body_style),
                Paragraph("<b>Requesting Actor:</b>", self.body_style),
                Paragraph(f"{safe_text(current_user.role)} ({safe_text(current_user.id.hex[:8])})", self.body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[110, 150, 120, 143])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # --- Section 1: Land Record Identification ---
        story.append(Paragraph("1. Land Record Identification & Registry Attributes", self.section_heading))
        co_owners_str = ", ".join(record.co_owners) if record.co_owners else "None recorded"
        rec_data = [
            [
                Paragraph("<b>Record ID:</b>", self.body_style),
                Paragraph(safe_text(record.id), self.body_style),
                Paragraph("<b>Document ID:</b>", self.body_style),
                Paragraph(safe_text(record.document_id), self.body_style),
            ],
            [
                Paragraph("<b>Khasra / Survey No:</b>", self.body_style),
                Paragraph(safe_text(record.khasra_number), self.body_bold),
                Paragraph("<b>Khata / Account No:</b>", self.body_style),
                Paragraph(safe_text(record.khata_number), self.body_bold),
            ],
            [
                Paragraph("<b>Village:</b>", self.body_style),
                Paragraph(safe_text(record.village), self.body_style),
                Paragraph("<b>Tehsil:</b>", self.body_style),
                Paragraph(safe_text(record.tehsil), self.body_style),
            ],
            [
                Paragraph("<b>District:</b>", self.body_style),
                Paragraph(safe_text(record.district), self.body_style),
                Paragraph("<b>State:</b>", self.body_style),
                Paragraph(safe_text(record.state), self.body_style),
            ],
            [
                Paragraph("<b>Registered Owner:</b>", self.body_style),
                Paragraph(safe_text(record.owner_name or "N/A"), self.body_style),
                Paragraph("<b>Co-Owners:</b>", self.body_style),
                Paragraph(safe_text(co_owners_str), self.body_style),
            ],
            [
                Paragraph("<b>Total Area:</b>", self.body_style),
                Paragraph(f"{safe_text(record.area_in_hectares)} Hectares", self.body_style),
                Paragraph("<b>Land Classification:</b>", self.body_style),
                Paragraph(safe_text(record.land_classification), self.body_style),
            ],
            [
                Paragraph("<b>Patta / Title No:</b>", self.body_style),
                Paragraph(safe_text(record.patta_number or "N/A"), self.body_style),
                Paragraph("<b>Reg / Mutation No:</b>", self.body_style),
                Paragraph(f"{safe_text(record.registration_number or 'N/A')} / {safe_text(record.mutation_number or 'N/A')}", self.body_style),
            ],
            [
                Paragraph("<b>Record Status:</b>", self.body_style),
                Paragraph(f"<b>{safe_text(record.status)}</b>", self.body_style),
                Paragraph("<b>Review Status:</b>", self.body_style),
                Paragraph(f"<b>{safe_text(record.review_status)}</b>", self.body_style),
            ]
        ]
        rec_table = Table(rec_data, colWidths=[110, 150, 110, 153])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 10))

        # --- Section 2: Extracted Data & Field-Level Confidence ---
        story.append(Paragraph("2. Automated OCR Field Extraction & Confidence Assessment", self.section_heading))
        doc_filename = record.document.file_name if record.document else "Direct Data Ingestion"
        provider_name = extraction.provider if extraction else "N/A"
        story.append(Paragraph(
            f"<i>Source Document: {safe_text(doc_filename)} • Provider Engine: {safe_text(provider_name)}</i>",
            self.subtitle_style
        ))
        story.append(Spacer(1, 4))

        ext_rows = [
            [
                Paragraph("Field Name", self.cell_header),
                Paragraph("Extracted Value", self.cell_header),
                Paragraph("Confidence", self.cell_header),
                Paragraph("Quality Tier", self.cell_header),
                Paragraph("System Verification", self.cell_header),
            ]
        ]

        extracted_dict = extraction.extracted_fields if extraction and extraction.extracted_fields else {}
        confidences = extraction.field_confidences if extraction and extraction.field_confidences else {}

        sample_fields = [
            ("state", "State", record.state),
            ("district", "District", record.district),
            ("tehsil", "Tehsil", record.tehsil),
            ("village", "Village", record.village),
            ("khasra_number", "Khasra Number", record.khasra_number),
            ("khata_number", "Khata Number", record.khata_number),
            ("area_in_hectares", "Area (Hectares)", str(record.area_in_hectares)),
            ("owner_name", "Primary Owner", record.owner_name or "N/A"),
        ]

        for field_key, field_label, fallback_val in sample_fields:
            val = extracted_dict.get(field_key, fallback_val)
            score = confidences.get(field_key, record.confidence_score)
            tier = categorize_confidence(score, settings.CONFIDENCE_THRESHOLD_HIGH, settings.CONFIDENCE_THRESHOLD_MEDIUM).value
            tier_color = "#059669" if tier == "HIGH" else ("#d97706" if tier == "MEDIUM" else "#dc2626")
            status_text = "PASSED" if tier != "LOW" else "FLAGGED_FOR_REVIEW"

            ext_rows.append([
                Paragraph(safe_text(field_label), self.body_style),
                Paragraph(safe_text(val), self.body_style),
                Paragraph(f"{score:.2f}", self.body_style),
                Paragraph(f"<font color='{tier_color}'><b>{tier}</b></font>", self.body_style),
                Paragraph(safe_text(status_text), self.body_style)
            ])

        ext_table = Table(ext_rows, colWidths=[110, 163, 70, 80, 100])
        ext_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(ext_table)
        story.append(Spacer(1, 10))

        # --- Section 3: Automated Validation Results ---
        story.append(Paragraph("3. Deterministic Validation Engine Results", self.section_heading))
        latest_val = record.validation_results[0] if record.validation_results else None
        if latest_val:
            rule_results = latest_val.rule_results or []
            passed_rules = sum(1 for r in rule_results if r.get("is_valid") or r.get("passed"))
            failed_rules = len(rule_results) - passed_rules
            val_status = "VALIDATED" if latest_val.is_valid else "FLAGGED"
            val_color = "#059669" if latest_val.is_valid else "#dc2626"

            story.append(Paragraph(
                f"Overall Result: <font color='{val_color}'><b>{val_status}</b></font> • "
                f"Rules Executed: {len(rule_results)} • Passed: {passed_rules} • Failed: {failed_rules} • "
                f"Timestamp: {safe_text(latest_val.validated_at.strftime('%Y-%m-%d %H:%M:%S UTC'))}",
                self.subtitle_style
            ))
            story.append(Spacer(1, 4))

            val_rows = [
                [
                    Paragraph("Validation Rule", self.cell_header),
                    Paragraph("Status", self.cell_header),
                    Paragraph("Rule Evaluation Finding", self.cell_header),
                    Paragraph("Severity", self.cell_header)
                ]
            ]
            for rule in rule_results:
                r_valid = rule.get("is_valid", rule.get("passed", False))
                r_status = "PASSED" if r_valid else "FAILED"
                r_color = "#059669" if r_valid else "#dc2626"
                r_name = rule.get("rule_name", rule.get("rule_id", "Validation Check"))
                r_msg = rule.get("message", rule.get("description", "Rule evaluation complete."))
                r_severity = rule.get("severity", "MEDIUM") if not r_valid else "INFO"

                val_rows.append([
                    Paragraph(safe_text(r_name), self.body_style),
                    Paragraph(f"<font color='{r_color}'><b>{r_status}</b></font>", self.body_style),
                    Paragraph(safe_text(r_msg), self.body_style),
                    Paragraph(safe_text(r_severity), self.body_style)
                ])

            val_table = Table(val_rows, colWidths=[140, 65, 248, 70])
            val_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(val_table)
        else:
            no_val_p = Paragraph("<i>No automated validation audits have been executed on this record yet.</i>", self.body_style)
            story.append(no_val_p)
        story.append(Spacer(1, 10))

        # --- Section 4: Cross-Record Discrepancy Cross-Examination ---
        story.append(Paragraph("4. Cross-Record Discrepancy & Cross-Examination Analysis", self.section_heading))
        discrepancies = record.discrepancies or []
        if discrepancies:
            disc_rows = [
                [
                    Paragraph("Type", self.cell_header),
                    Paragraph("Affected Field", self.cell_header),
                    Paragraph("Severity", self.cell_header),
                    Paragraph("Status", self.cell_header),
                    Paragraph("Discrepancy Details", self.cell_header)
                ]
            ]
            for disc in discrepancies:
                sev_color = "#dc2626" if disc.severity == "CRITICAL" else ("#ea580c" if disc.severity == "HIGH" else "#d97706")
                disc_rows.append([
                    Paragraph(safe_text(disc.discrepancy_type), self.body_style),
                    Paragraph(safe_text(disc.field_name or "General"), self.body_style),
                    Paragraph(f"<font color='{sev_color}'><b>{safe_text(disc.severity)}</b></font>", self.body_style),
                    Paragraph(safe_text(disc.status), self.body_style),
                    Paragraph(safe_text(disc.description), self.body_style)
                ])
            disc_table = Table(disc_rows, colWidths=[100, 85, 65, 65, 208])
            disc_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(disc_table)
        else:
            no_disc_p = Paragraph(
                "<b>No cross-record discrepancies recorded.</b> "
                "This summary includes only recorded checks; it does not certify ownership or spatial overlap.",
                self.body_style
            )
            no_disc_table = Table([[no_disc_p]], colWidths=[usable_width])
            no_disc_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(no_disc_table)
        story.append(Spacer(1, 10))

        # --- Section 5: Human Review & Oversight ---
        story.append(Paragraph("5. Statutory Human Review & Oversight Decision", self.section_heading))
        rev_status = record.review_status or "PENDING_REVIEW"
        rev_color = "#059669" if rev_status == "APPROVED" else ("#dc2626" if rev_status == "REJECTED" else "#d97706")
        reviewer_ref = f"Reviewer User {record.reviewed_by.hex[:8]}" if record.reviewed_by else "Unassigned / Pending"
        reviewed_time_str = record.reviewed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if record.reviewed_at else "Pending"

        rev_data = [
            [
                Paragraph("<b>Review Status:</b>", self.body_style),
                Paragraph(f"<font color='{rev_color}'><b>{safe_text(rev_status)}</b></font>", self.body_style),
                Paragraph("<b>Reviewer Reference:</b>", self.body_style),
                Paragraph(safe_text(reviewer_ref), self.body_style)
            ],
            [
                Paragraph("<b>Decision Timestamp:</b>", self.body_style),
                Paragraph(safe_text(reviewed_time_str), self.body_style),
                Paragraph("<b>Review Justification:</b>", self.body_style),
                Paragraph(safe_text(record.review_notes or "None recorded"), self.body_style)
            ]
        ]
        if record.rejection_reason:
            rev_data.append([
                Paragraph("<b>Rejection Reason:</b>", self.body_style),
                Paragraph(safe_text(record.rejection_reason), self.body_style),
                Paragraph("", self.body_style),
                Paragraph("", self.body_style)
            ])

        rev_table = Table(rev_data, colWidths=[110, 150, 120, 143])
        rev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(rev_table)
        story.append(Spacer(1, 10))

        # --- Section 6: GIS Cadastral Survey & Spatial Geometry ---
        story.append(Paragraph("6. GIS Cadastral Survey & Spatial Representation", self.section_heading))
        if record.parcel_location:
            loc = record.parcel_location
            gis_data = [
                [
                    Paragraph("<b>Centroid Latitude:</b>", self.body_style),
                    Paragraph(f"{loc.latitude:.6f}" if loc.latitude is not None else "N/A", self.body_style),
                    Paragraph("<b>Centroid Longitude:</b>", self.body_style),
                    Paragraph(f"{loc.longitude:.6f}" if loc.longitude is not None else "N/A", self.body_style),
                ],
                [
                    Paragraph("<b>CRS Reference:</b>", self.body_style),
                    Paragraph(safe_text(loc.coordinate_reference_system), self.body_style),
                    Paragraph("<b>Geometry Validation:</b>", self.body_style),
                    Paragraph(safe_text(loc.geometry_validation_status), self.body_style),
                ],
                [
                    Paragraph("<b>Survey Map Source:</b>", self.body_style),
                    Paragraph(safe_text(loc.map_source), self.body_style),
                    Paragraph("<b>Spatial Confidence:</b>", self.body_style),
                    Paragraph(f"{loc.location_confidence:.2f}", self.body_style),
                ]
            ]
            gis_table = Table(gis_data, colWidths=[110, 150, 120, 143])
            gis_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(gis_table)
        else:
            gis_p = Paragraph(
                "<i>No spatial cadastral survey coordinates or GeoJSON boundaries attached to this record (Cadastral survey pending).</i>",
                self.body_style
            )
            story.append(gis_p)
        story.append(Spacer(1, 10))

        # --- Section 7: Lifecycle Audit Trail Reference ---
        story.append(Paragraph("7. Lifecycle Audit Trail Summary", self.section_heading))
        if audit_logs:
            audit_rows = [
                [
                    Paragraph("Event Timestamp", self.cell_header),
                    Paragraph("Action Type", self.cell_header),
                    Paragraph("Actor Reference", self.cell_header),
                    Paragraph("State Summary", self.cell_header)
                ]
            ]
            for alog in audit_logs:
                actor_txt = f"User {alog.actor_user_id.hex[:8]}" if alog.actor_user_id else "System Service"
                state_summary = ""
                if alog.new_state:
                    state_summary = ", ".join(f"{k}: {v}" for k, v in list(alog.new_state.items())[:2])
                audit_rows.append([
                    Paragraph(safe_text(alog.created_at.strftime("%Y-%m-%d %H:%M:%S")), self.body_style),
                    Paragraph(safe_text(alog.action), self.body_style),
                    Paragraph(safe_text(actor_txt), self.body_style),
                    Paragraph(safe_text(state_summary or "Audit event recorded"), self.body_style)
                ])
            audit_table = Table(audit_rows, colWidths=[110, 130, 110, 173])
            audit_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(audit_table)
        else:
            story.append(Paragraph("<i>No historical audit trail events found for this record.</i>", self.body_style))
        story.append(Spacer(1, 10))

        # --- Section 8: Statutory Disclaimer Box ---
        statutory_box = [
            [
                Paragraph(
                    "<b>STATUTORY DISCLAIMER & NON-CERTIFICATION NOTICE:</b><br/>"
                    "This system-generated report summarizes digitization, extraction, validation, discrepancy, and review "
                    "information available at the time of generation. It is not, by itself, a government-issued title deed, "
                    "legal ownership certificate, or final legal determination. Any statutory land transaction, transfer, mutation, "
                    "or judicial proceedings require verified records issued directly by the Competent State Revenue Authority.",
                    self.statutory_text
                )
            ]
        ]
        stat_table = Table(statutory_box, colWidths=[usable_width])
        stat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(KeepTogether([stat_table]))

        # 7. Compile PDF document
        doc.build(story, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # 8. Sanitize filename
        clean_khasra = re.sub(r"[^a-zA-Z0-9_-]", "_", str(record.khasra_number))
        filename = f"verification_report_{clean_khasra}_{now_utc.strftime('%Y%m%d_%H%M%S')}.pdf"

        # 9. Log audit event for report generation
        await audit_service.log_event(
            session=session,
            action="REPORT_GENERATED",
            entity_type="LAND_RECORD",
            actor_user_id=current_user.id,
            entity_id=record.id,
            new_state={
                "report_reference": report_ref,
                "report_version": report_version,
                "khasra_number": record.khasra_number,
                "filename": filename,
                "file_size_bytes": len(pdf_bytes)
            }
        )
        await session.commit()
        logger.info(f"Generated verification report {report_ref} for record {record.id} by user {current_user.id}")

        return pdf_bytes, filename


verification_report_service = VerificationReportService()
