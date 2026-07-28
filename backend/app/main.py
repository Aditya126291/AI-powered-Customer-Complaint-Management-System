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


def extract_patch(text: str) -> dict[str, str]:
    """High-precision pharmaceutical QMS entity extractor for document tables and free-text."""
    patch: dict[str, str] = {}

    kv_patterns = {
        "customerName": [
            r"Customer\s*Name\s*:\s*\n?\s*([^\n\r|]+)",
            r"Customer\s*:\s*\n?\s*([^\n\r|]+)",
            r"Client\s*:\s*\n?\s*([^\n\r|]+)",
            r"^([A-Z][A-Za-z &.-]+?)\s+(?:reported|complained)",
        ],
        "complaintSource": [
            r"Complaint\s*Source\s*:\s*\n?\s*([^\n\r]+)",
            r"Source\s*:\s*\n?\s*([^\n\r]+)",
        ],
        "productName": [
            r"Product\s*Name(?:\s*\(API\/FDF\))?\s*:\s*\n?\s*([^\n\r]+)",
            r"Product\s*:\s*\n?\s*([^\n\r]+)",
            r"\bin\s+([A-Z][A-Za-z0-9 -]+?(?:capsules|tablets|injection|syrup|suspension|api)(?:\s+\d+\s*(?:mg|ml))?)\b",
            r"(?:product(?: name)? is|for)\s+([A-Z][A-Za-z0-9 -]+?(?:capsules|tablets|injection|syrup|suspension|api)(?:\s+\d+\s*(?:mg|ml))?)\b",
        ],
        "strengthGrade": [
            r"Product\s*Strength(?:\s*\/\s*Grade|\s*\/\s*Dosage)?\s*:\s*\n?\s*([^\n\r]+)",
            r"Strength\s*:\s*\n?\s*([^\n\r]+)",
            r"(\d+\s*(?:mg|ml)(?:\s*\/\s*\d+\s*ml)?)",
        ],
        "batchLotNumber": [
            r"Batch\s*(?:\/\s*Lot)?\s*(?:Number|No\.?)?\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:batch|lot)\s*(?:number|no\.?)?\s*(?:is|:)?\s*([A-Za-z0-9-]{4,})",
        ],
        "manufacturingDate": [
            r"Manufactur(?:ing|ed)\s*Date\s*:\s*\n?\s*([^\n\r]+)",
            r"mfg\s*date\s*:\s*\n?\s*([^\n\r]+)",
            r"manufactur(?:ing|ed)\s+date\s*(?:is|:)?\s*([A-Za-z0-9, -]+\d{4})",
        ],
        "expiryDate": [
            r"Expir(?:y|ation)\s*Date\s*:\s*\n?\s*([^\n\r]+)",
            r"exp\s*date\s*:\s*\n?\s*([^\n\r]+)",
            r"expir(?:y|ation)\s+date\s*(?:is|:)?\s*([A-Za-z0-9, -]+\d{4}|Not Provided)",
        ],
        "affectedQuantity": [
            r"Affected\s*Quantity\s*:\s*\n?\s*([^\n\r]+)",
            r"Quantity\s*:\s*\n?\s*([^\n\r]+)",
            r"(?:affected\s+quantity|quantity)\s*(?:is|:)?\s*(\d+(?:\.\d+)?\s*(?:capsules|tablets|vials|kg|g|units?|bottles[^\n\r]*))",
        ],
        "originatingSite": [
            r"Originating\s*Site(?:\s*Block)?\s*:\s*\n?\s*([^\n\r]+)",
            r"Site\s*:\s*\n?\s*([^\n\r]+)",
        ],
        "impactedMaterial": [
            r"Impacted\s*(?:Non-Product\s*)?Material[s]?\s*:\s*\n?\s*([^\n\r]+)",
        ],
        "complaintType": [
            r"Complaint\s*Type\s*:\s*\n?\s*([^\n\r]+)",
        ],
        "complaintDate": [
            r"Complaint\s*Date\s*:\s*\n?\s*([^\n\r]+)",
            r"Date\s*of\s*Incident\s*:\s*\n?\s*([^\n\r]+)",
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

    if not patch.get("detailedDescription"):
        patch["detailedDescription"] = text.strip()

    lowered = text.lower()
    if any(term in lowered for term in ("discolor", "foreign particle", "broken", "leak", "contamination", "syrup", "capsule")):
        if not patch.get("complaintType"):
            patch["complaintType"] = "Product defect"
        if not patch.get("severity"):
            patch["severity"] = "Critical" if any(term in lowered for term in ("contamination", "critical", "foreign particle")) else "High"
        if not patch.get("priority"):
            patch["priority"] = "High"

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

    result = run_intake(request.text, request.current_form.model_dump())
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

    # Clear current form for fresh document intake so old document fields don't bleed into new document
    result = run_intake(extracted_text, {})

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
    count = db.query(ComplaintRecord).count() + 1
    year = datetime.datetime.now().year
    complaint_num = f"CC-{year}-{count:04d}"

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
