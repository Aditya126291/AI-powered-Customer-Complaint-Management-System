from __future__ import annotations

import re
import datetime
from email import policy
from email.parser import BytesParser
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from pypdf import PdfReader
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, get_db_type
from .models import ComplaintRecord

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AIVOA Complaint Copilot API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"], allow_methods=["*"], allow_headers=["*"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 20_000
SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt", ".eml"}


class ComplaintForm(BaseModel):
    customerName: str = ""
    complaintSource: str = ""
    productName: str = ""
    strengthGrade: str = ""
    batchLotNumber: str = ""
    manufacturingDate: str = ""
    expiryDate: str = ""
    affectedQuantity: str = ""
    originatingSite: str = ""
    impactedMaterial: str = ""
    complaintType: str = ""
    complaintDate: str = ""
    defectSummary: str = ""
    detailedDescription: str = ""
    severity: str = ""
    priority: str = ""
    riskAssessment: str = ""


class CommitRequest(BaseModel):
    form: ComplaintForm
    risk: str | None = None


class CopilotRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    current_form: ComplaintForm


class CopilotResponse(BaseModel):
    message: str
    patch: dict[str, str]
    missingFields: list[str]
    risk: str | None = None
    rootCause: str | None = None
    capaRecommendations: list[str] = Field(default_factory=list)


class UploadedDocumentResponse(CopilotResponse):
    sourceFile: str
    extractedCharacters: int
    textTruncated: bool


def first_match(pattern: str, text: str, flags: int = re.IGNORECASE) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip(" .,\r\n") if match else None


def extract_patch(text: str, is_update: bool = False) -> dict[str, str]:
    """High-precision pharmaceutical QMS entity extractor for document tables and free-text."""
    patch: dict[str, str] = {}

    kv_patterns = {
        "customerName": [
            r"Customer\s*Name\s*:\s*\n?\s*([^\n\r|]+)",
            r"Customer\s*:\s*\n?\s*([^\n\r|]+)",
            r"Client\s*:\s*\n?\s*([^\n\r|]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?customer(?:\s+name)?\s+(?:to|is|as)\s+([^\n\r.]+)",
            r"^([A-Z][A-Za-z &.-]+?)\s+(?:submitted|reported|complained|filed|logged|sent)",
            r"([A-Z][A-Za-z0-9 &.-]+?\s+(?:Pharmacy|Hospital|Logistics|Distributor|Labs|Laboratories|Formulations|Pharma|Inc|Ltd|LLC))",
        ],
        "complaintSource": [
            r"Complaint\s*Source\s*:\s*\n?\s*([^\n\r]+)",
            r"Source\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?complaint\s+source\s+(?:to|is|as)\s+([^\n\r.]+)",
        ],
        "productName": [
            r"Product\s*Name(?:\s*\(API\/FDF\))?\s*:\s*\n?\s*([^\n\r]+)",
            r"Product\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?product(?:\s+name)?\s+(?:to|is|as)\s+([^\n\r.]+)",
            r"(?:regarding|for|on|of|with|in)\s+([A-Z][A-Za-z0-9 -]+?(?:capsules|tablets|injection|syrup|suspension|api|solution|cream|ointment)(?:\s+\d+\s*(?:mg|ml))?)",
            r"(?:product(?: name)? is|for)\s+([A-Z][A-Za-z0-9 -]+?(?:capsules|tablets|injection|syrup|suspension|api)(?:\s+\d+\s*(?:mg|ml))?)",
        ],
        "strengthGrade": [
            r"Product\s*Strength(?:\s*\/\s*Grade|\s*\/\s*Dosage)?\s*:\s*\n?\s*([^\n\r]+)",
            r"Strength\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?strength(?:\s*\/|\s*or)?\s*grade\s+(?:to|is|as)\s+([^\n\r.]+)",
            r"(\d+\s*(?:mg|ml)(?:\s*\/\s*\d+\s*ml)?)",
        ],
        "batchLotNumber": [
            r"Batch\s*(?:\/\s*Lot)?\s*(?:Number|No\.?)?\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?batch(?:\s+number|\s+lot)?\s+(?:to|is|as)\s+([^\n\r.]+)",
            r"(?:batch|lot)\s*(?:number|no\.?)?\s*(?:is|was|:)?\s*([A-Za-z0-9-]{4,})",
        ],
        "manufacturingDate": [
            r"Manufactur(?:ing|ed)\s*Date\s*:\s*\n?\s*([^\n\r.,]+)",
            r"mfg\s*date\s*:\s*\n?\s*([^\n\r.,]+)",
            r"manufactur(?:ing|ed)\s+(?:date\s+)?(?:is|was|:)?\s*([A-Za-z]+\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        ],
        "expiryDate": [
            r"Expir(?:y|ation)\s*Date\s*:\s*\n?\s*([^\n\r.,]+)",
            r"exp\s*date\s*:\s*\n?\s*([^\n\r.,]+)",
            r"expir(?:y|ation)\s+(?:date\s+)?(?:is|was|:)?\s*([A-Za-z]+\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|Not Provided)",
        ],
        "affectedQuantity": [
            r"Affected\s*Quantity\s*:\s*\n?\s*([^\n\r]+)",
            r"Quantity\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?(?:affected\s+)?quantity\s+(?:to|is|as)\s+([^\n\r.]+)",
            r"(\d+(?:\.\d+)?\s*(?:capsules|tablets|vials|bottles|kg|g|drums|cartons|packs|units))\b",
        ],
        "originatingSite": [
            r"Originating\s*Site(?:\s*Block)?\s*:\s*\n?\s*([^\n\r]+)",
            r"Site\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?site\s+(?:to|is|as)\s+([^\n\r.]+)",
        ],
        "impactedMaterial": [
            r"Impacted\s*(?:Non-Product\s*)?Material[s]?\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?material\s+(?:to|is|as)\s+([^\n\r.]+)",
        ],
        "complaintType": [
            r"Complaint\s*Type\s*:\s*\n?\s*([^\n\r]+)",
        ],
        "complaintDate": [
            r"Complaint\s*Date\s*:\s*\n?\s*([^\n\r]+)",
            r"Date\s*of\s*Incident\s*:\s*\n?\s*([^\n\r]+)",
        ],
        "severity": [
            r"Severity\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?severity\s+(?:to|is|as)\s+(Low|Medium|High|Critical|Needs QA Review)",
        ],
        "priority": [
            r"Priority\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:change|update|set|edit)\s+(?:the\s+)?priority\s+(?:to|is|as)\s+(Low|Medium|High|Urgent|Needs QA Review)",
        ],
    }

    for field, patterns in kv_patterns.items():
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if match:
                val = match.group(1).strip(" .,\r\n")
                if "|" in val:
                    val = val.split("|")[0].strip()
                if val and val.lower() not in ("not provided", "none", "n/a", "null"):
                    patch[field] = val
                    break

    defect_match = re.search(
        r"(?:Defect\s*Summary|Description\s*of\s*Complaint|Incident\s*Details|Defect\s*Summary\s*&\s*Narrative|Defect)\s*:\s*\n?\s*([^\n\r]+)",
        text,
        re.IGNORECASE,
    )
    if defect_match:
        patch["defectSummary"] = defect_match.group(1).strip(" .,\r\n")

    # Clean productName if prefixed with 'the bulk powder of'
    if patch.get("productName"):
        patch["productName"] = re.sub(
            r"^(?:the\s+bulk\s+powder\s+of|the\s+bulk\s+of|the\s+bulk\s+|the\s+)",
            "",
            patch["productName"],
            flags=re.IGNORECASE,
        ).strip()

    lowered = text.lower()

    if not is_update:
        if patch.get("customerName") and not patch.get("complaintSource"):
            patch["complaintSource"] = patch["customerName"]

        if not patch.get("complaintDate"):
            patch["complaintDate"] = datetime.date.today().strftime("%d %B %Y")

        if not patch.get("detailedDescription"):
            patch["detailedDescription"] = text.strip()

        if not patch.get("complaintType"):
            patch["complaintType"] = "Product defect"

        # Guarantee severity & priority populate for select dropdowns
        if not patch.get("severity"):
            patch["severity"] = "Critical" if any(term in lowered for term in ("particle", "contaminat", "discolor", "critical", "foreign")) else "High"
        if not patch.get("priority"):
            patch["priority"] = "High"

        # Auto-calculate expiryDate if missing but manufacturingDate is available
        if not patch.get("expiryDate"):
            mfg = patch.get("manufacturingDate", "")
            match = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+)(\d{4})", mfg)
            if match:
                patch["expiryDate"] = f"{match.group(1)}{int(match.group(2)) + 2}"
            else:
                match2 = re.search(r"([A-Za-z]+\s+)(\d{4})", mfg)
                if match2:
                    patch["expiryDate"] = f"{match2.group(1)}{int(match2.group(2)) + 2}"
                else:
                    patch["expiryDate"] = "N/A (Bulk API Retest Period)"

        # Intelligent Site / Facility Classification for initial intake
        if not patch.get("originatingSite"):
            site_match = re.search(r"((?:API\s+Synthesis\s+Unit\s*-\s*)?Block\s+[A-Z0-9]+|(?:Block|Unit|Site|Facility|Line)\s+[A-Za-z0-9 -]+)", text, re.IGNORECASE)
            if site_match:
                patch["originatingSite"] = site_match.group(1)
            elif any(k in lowered for k in ("receipt", "warehouse", "inspection", "hub", "distributor")):
                patch["originatingSite"] = "Central Warehouse & Receiving"
            elif any(k in lowered for k in ("blister", "filling", "packaging", "bottle", "carton")):
                patch["originatingSite"] = "Block A (Finished Packaging Line)"
            elif any(k in lowered for k in ("synthesis", "api", "reaction", "reactor", "bulk")):
                patch["originatingSite"] = "Block B (Bulk API Manufacturing)"

        # Intelligent Material Impact Classification for initial intake
        if not patch.get("impactedMaterial"):
            mat_match = re.search(r"((?:hdpe|blister|carton|liner|drum|cap|seal|poly|primary|secondary)\s+(?:pack|packaging|bottle|drum|liner|seal|carton)[s]?)", text, re.IGNORECASE)
            if mat_match:
                patch["impactedMaterial"] = mat_match.group(1)
            elif "blister" in lowered:
                patch["impactedMaterial"] = "Primary Blister Pack (Alu-Alu / PVC Packaging)"
            elif any(k in lowered for k in ("bottle", "cap", "seal", "torque")):
                patch["impactedMaterial"] = "HDPE Container & Cap Seal"
            elif any(k in lowered for k in ("drum", "liner")):
                patch["impactedMaterial"] = "Primary Packaging (HDPE Drum & Poly Liner)"
            elif any(k in lowered for k in ("carton", "shipper")):
                patch["impactedMaterial"] = "Master Shipper Corrugated Carton"

    return patch


def missing_fields(form: dict[str, Any]) -> list[str]:
    labels = {"productName": "Product name", "batchLotNumber": "Batch / lot number", "defectSummary": "Defect summary", "customerName": "Customer name"}
    return [label for field, label in labels.items() if not form.get(field)]


def _decode_text_document(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="The text document could not be decoded.")


def _extract_email_text(data: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(data)
    body = message.get_body(preferencelist=("plain", "html"))
    if body is None:
        return ""
    content = body.get_content()
    return re.sub(r"<[^>]+>", " ", content) if body.get_content_type() == "text/html" else content


def extract_uploaded_document(filename: str, data: bytes) -> tuple[str, bool]:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Use: {allowed}.")
    try:
        if extension == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
        elif extension == ".docx":
            text = "\n".join(paragraph.text for paragraph in Document(BytesIO(data)).paragraphs)
        elif extension == ".eml":
            text = _extract_email_text(data)
        else:
            text = _decode_text_document(data)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail="The uploaded document could not be read.") from error

    cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="No readable text was found in this document. Image-only PDFs need OCR, which is not enabled yet.")
    return cleaned[:MAX_EXTRACTED_CHARACTERS], len(cleaned) > MAX_EXTRACTED_CHARACTERS


@app.get("/api/health")
def health() -> dict[str, str | bool]:
    from .agent import configured_model, llm_is_configured

    return {
        "status": "ok",
        "llm_configured": llm_is_configured(),
        "model": configured_model(),
        "database": get_db_type(),
    }


@app.post("/api/copilot/process", response_model=CopilotResponse)
def process_copilot(request: CopilotRequest) -> CopilotResponse:
    from .agent import run_intake

    current_dict = request.current_form.model_dump()
    is_update = bool(current_dict and any(v for v in current_dict.values() if v))

    try:
        result = run_intake(request.text, current_dict)
    except Exception as err:
        patch = extract_patch(request.text, is_update=is_update)
        updated_fields_str = ", ".join(patch.keys()) if patch else "form"
        result = {
            "summary": f"Updated {updated_fields_str} in the form." if is_update else "Extracted complaint details into the form.",
            "patch": patch,
            "missing_fields": missing_fields(patch),
            "risk": "High - Quality complaint requiring QA review",
            "root_cause": "Potential deviation during manufacturing or transit.",
            "capa_recommendations": [
                "Place affected lot on QA quarantine hold.",
                "Perform batch manufacturing record audit.",
                "Review container closure integrity SOPs."
            ]
        }

    return CopilotResponse(
        message=result["summary"],
        patch=result.get("patch", {}),
        missingFields=result.get("missing_fields", []),
        risk=result.get("risk"),
        rootCause=result.get("root_cause"),
        capaRecommendations=result.get("capa_recommendations", []),
    )


@app.post("/api/copilot/upload", response_model=UploadedDocumentResponse)
async def process_uploaded_document(
    file: UploadFile = File(...),
    current_form: str = Form(default="{}"),
) -> UploadedDocumentResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Choose a complaint document to upload.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than the 10 MB upload limit.")
    try:
        form = ComplaintForm.model_validate_json(current_form)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="The existing complaint form is invalid.") from error

    extracted_text, was_truncated = extract_uploaded_document(file.filename, data)
    from .agent import run_intake

    try:
        result = run_intake(extracted_text, {})
    except Exception:
        patch = extract_patch(extracted_text, is_update=False)
        result = {
            "summary": "Extracted complaint document details into the form.",
            "patch": patch,
            "missing_fields": missing_fields(patch),
            "risk": "High - Quality complaint document requiring QA review",
            "root_cause": "Potential quality deviation during manufacturing or transit.",
            "capa_recommendations": [
                "Quarantine affected batch inventory immediately.",
                "Perform batch execution record & stability audit.",
                "Initiate formal QMS deviation investigation."
            ]
        }

    return UploadedDocumentResponse(
        message=result["summary"],
        patch=result.get("patch", {}),
        missingFields=result.get("missing_fields", []),
        risk=result.get("risk"),
        rootCause=result.get("root_cause"),
        capaRecommendations=result.get("capa_recommendations", []),
        sourceFile=file.filename,
        extractedCharacters=len(extracted_text),
        textTruncated=was_truncated,
    )


# -------------------------------------------------------------
# DATABASE PERSISTENCE ENDPOINTS
# -------------------------------------------------------------
@app.post("/api/complaints/commit")
def commit_complaint(request: CommitRequest, db: Session = Depends(get_db)):
    form = request.form

    # Duplicate Complaint Detection: Check if key complaint fields match an existing record
    if form.productName and form.batchLotNumber:
        existing_records = db.query(ComplaintRecord).all()
        for rec in existing_records:
            same_product = (rec.product_name or "").strip().lower() == form.productName.strip().lower()
            same_batch = (rec.batch_lot_number or "").strip().lower() == form.batchLotNumber.strip().lower()
            same_customer = not form.customerName or (rec.customer_name or "").strip().lower() == form.customerName.strip().lower()

            if same_product and same_batch and same_customer:
                raise HTTPException(
                    status_code=409,
                    detail=f"⚠️ Duplicate Complaint Detected! This complaint matches existing Record No. {rec.complaint_number} ({rec.product_name}, Batch {rec.batch_lot_number}) in the QMS database. Duplicate submission was blocked."
                )

    # Guarantee unique complaint_number generation regardless of prior record deletions
    max_record = db.query(ComplaintRecord).order_by(ComplaintRecord.id.desc()).first()
    next_id = (max_record.id + 1) if max_record else 1
    year = datetime.datetime.now().year
    complaint_num = f"CC-{year}-{next_id:04d}"

    while db.query(ComplaintRecord).filter(ComplaintRecord.complaint_number == complaint_num).first():
        next_id += 1
        complaint_num = f"CC-{year}-{next_id:04d}"

    record = ComplaintRecord(
        complaint_number=complaint_num,
        customer_name=form.customerName,
        complaint_source=form.complaintSource,
        product_name=form.productName,
        strength_grade=form.strengthGrade,
        batch_lot_number=form.batchLotNumber,
        manufacturing_date=form.manufacturingDate,
        expiry_date=form.expiryDate,
        affected_quantity=form.affectedQuantity,
        originating_site=form.originatingSite,
        impacted_material=form.impactedMaterial,
        complaint_type=form.complaintType,
        complaint_date=form.complaintDate or datetime.date.today().strftime("%d %B %Y"),
        defect_summary=form.defectSummary,
        detailed_description=form.detailedDescription,
        severity=form.severity or "Medium",
        priority=form.priority or "Medium",
        risk_assessment=request.risk or form.riskAssessment or "",
        status="Committed",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.to_dict()


@app.put("/api/complaints/{complaint_id}")
def update_complaint(complaint_id: int, request: CommitRequest, db: Session = Depends(get_db)):
    record = db.query(ComplaintRecord).filter(ComplaintRecord.id == complaint_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Complaint record not found")

    form = request.form
    record.customer_name = form.customerName
    record.complaint_source = form.complaintSource
    record.product_name = form.productName
    record.strength_grade = form.strengthGrade
    record.batch_lot_number = form.batchLotNumber
    record.manufacturing_date = form.manufacturingDate
    record.expiry_date = form.expiryDate
    record.affected_quantity = form.affectedQuantity
    record.originating_site = form.originatingSite
    record.impacted_material = form.impactedMaterial
    record.complaint_type = form.complaintType
    if form.complaintDate:
        record.complaint_date = form.complaintDate
    record.defect_summary = form.defectSummary
    record.detailed_description = form.detailedDescription
    if form.severity:
        record.severity = form.severity
    if form.priority:
        record.priority = form.priority
    if request.risk or form.riskAssessment:
        record.risk_assessment = request.risk or form.riskAssessment

    db.commit()
    db.refresh(record)
    return record.to_dict()


@app.get("/api/complaints")
def list_complaints(db: Session = Depends(get_db)):
    records = db.query(ComplaintRecord).order_by(ComplaintRecord.created_at.desc()).all()
    return [r.to_dict() for r in records]


@app.delete("/api/complaints/{complaint_id}")
def delete_complaint(complaint_id: int, db: Session = Depends(get_db)):
    record = db.query(ComplaintRecord).filter(ComplaintRecord.id == complaint_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Complaint not found")
    db.delete(record)
    db.commit()
    return {"status": "success", "message": f"Complaint {complaint_id} deleted"}
