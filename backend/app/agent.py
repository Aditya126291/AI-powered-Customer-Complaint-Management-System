"""LangGraph workflow for safe, structured complaint intake with Automatic Defect Summary Synthesis, CAPA Recommendations & AI Risk Assessment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Walk up from this file to find .env in the project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")


class StructuredExtraction(BaseModel):
    """The only shape an LLM is allowed to return to the form."""

    intent: Literal["create", "update"] = "create"
    updates: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value updates where keys match form fields: customerName, complaintSource, productName, strengthGrade, batchLotNumber, manufacturingDate, expiryDate, affectedQuantity, originatingSite, impactedMaterial, complaintType, complaintDate, defectSummary, detailedDescription, severity, priority."
    )
    summary: str = Field(default="", description="A short summary of what was extracted or updated.")
    risk: str | None = Field(default=None, description="Recommended risk classification or assessment if applicable.")
    root_cause_hypothesis: str | None = Field(default=None, description="Suggested initial root cause hypothesis for Quality Assurance investigation.")
    capa_recommendations: list[str] = Field(
        default_factory=list,
        description="List of 2 to 4 recommended Corrective And Preventive Action (CAPA) steps for QA teams."
    )
    dropdown_actions: dict[str, Literal["lower", "increase", "unclear"]] = Field(
        default_factory=dict,
        description="Relative dropdown change intents."
    )


class IntakeState(TypedDict, total=False):
    text: str
    current_form: dict[str, str]
    patch: dict[str, str]
    intent: str
    summary: str
    missing_fields: list[str]
    risk: str | None
    root_cause: str | None
    capa_recommendations: list[str]
    dropdown_actions: dict[str, str]


ALLOWED_FIELDS = {
    "customerName", "complaintSource", "productName", "strengthGrade", "batchLotNumber",
    "manufacturingDate", "expiryDate", "affectedQuantity", "originatingSite", "impactedMaterial",
    "complaintType", "complaintDate", "defectSummary", "detailedDescription", "severity", "priority",
}

FIELD_ALIASES = {
    "customer": "customerName",
    "customer_name": "customerName",
    "product": "productName",
    "product_name": "productName",
    "batch": "batchLotNumber",
    "batch_number": "batchLotNumber",
    "batch_lot": "batchLotNumber",
    "lot_number": "batchLotNumber",
    "mfg_date": "manufacturingDate",
    "manufacturing_date": "manufacturingDate",
    "exp_date": "expiryDate",
    "expiry_date": "expiryDate",
    "quantity": "affectedQuantity",
    "affected_quantity": "affectedQuantity",
    "defect": "defectSummary",
    "defect_summary": "defectSummary",
    "description": "detailedDescription",
    "detailed_description": "detailedDescription",
    "strength": "strengthGrade",
    "strength_grade": "strengthGrade",
    "source": "complaintSource",
    "complaint_source": "complaintSource",
}


def _deterministic_extract(text: str) -> dict[str, str]:
    from .main import extract_patch
    return extract_patch(text)


def _generate_default_capa(defect_text: str) -> tuple[str, list[str]]:
    lowered = defect_text.lower()
    if any(k in lowered for k in ("discolor", "color", "degrad")):
        return (
            "Potential oxidation or moisture exposure causing active ingredient chemical degradation.",
            [
                "Immediate Containment: Place affected batch on QA hold and quarantine warehouse inventory.",
                "Root Cause: Test seal integrity of blister packs and evaluate relative humidity during packaging line run.",
                "Preventive Action: Review desiccant packaging specifications and ambient storage temperature controls."
            ]
        )
    elif any(k in lowered for k in ("foreign", "particle", "contaminat")):
        return (
            "Possible environmental or packaging material particulate contamination during filling.",
            [
                "Immediate Containment: Issue immediate quarantine alert for batch and pause filling line.",
                "Root Cause: Audit HVAC HEPA filter particulate counts and inspect poly liners.",
                "Preventive Action: Upgrade inline optical vision particle inspection on packaging block."
            ]
        )
    elif any(k in lowered for k in ("leak", "seal", "bottle", "cap", "torque")):
        return (
            "Container closure integrity failure or inadequate capping machine torque setting.",
            [
                "Immediate Containment: Inspect all master cartons in transit and quarantine affected lot.",
                "Root Cause: Verify capping machine spindle torque calibration and bottle neck thread dimensions.",
                "Preventive Action: Implement automated inline cap-torque monitoring sensor."
            ]
        )
    else:
        return (
            "Quality defect requiring standard pharmaceutical QA investigation.",
            [
                "Immediate Containment: Place remaining batch inventory on quarantine hold.",
                "Root Cause: Perform 5-Why analysis and review batch manufacturing execution records.",
                "Preventive Action: Conduct refresher training on QMS deviation handling procedures."
            ]
        )


def _synthesize_formal_defect_summary(text: str, patch: dict[str, str], current_form: dict[str, str]) -> str:
    merged = current_form | patch
    product = merged.get("productName") or "Pharmaceutical product"
    batch = merged.get("batchLotNumber")
    batch_str = f" (Batch {batch})" if batch else ""
    customer = merged.get("customerName")
    cust_str = f" reported by {customer}" if customer else ""

    lowered = text.lower()
    if "discolor" in lowered:
        defect_desc = "discolored units observed within primary packaging, indicating potential active ingredient degradation or moisture ingress"
    elif any(k in lowered for k in ("foreign", "particle", "contaminat")):
        defect_desc = "foreign particle contamination observed within bulk material, representing a potential critical quality defect"
    elif any(k in lowered for k in ("leak", "seal", "bottle", "cap", "torque")):
        defect_desc = "container closure integrity failure resulting in liquid leakage and loose cap torque"
    elif any(k in lowered for k in ("broken", "chip")):
        defect_desc = "physical breakage and tablet integrity failure observed during receipt inspection"
    else:
        defect_desc = "quality deviation and specification non-conformance reported during incoming inspection"

    return f"Formal QMS Quality Complaint{cust_str} regarding {product}{batch_str}. Investigation confirmed {defect_desc}. Immediate QA quarantine, batch holding, and laboratory analysis initiated."


def _map_updates_to_form_fields(raw_updates: dict[str, str]) -> dict[str, str]:
    patch = {}
    for key, value in raw_updates.items():
        if not value:
            continue
        mapped_key = FIELD_ALIASES.get(key.lower(), key)
        if mapped_key in ALLOWED_FIELDS:
            patch[mapped_key] = value
    return patch


def extract_fields(state: IntakeState) -> dict[str, Any]:
    current_form = state.get("current_form", {})
    user_text = state.get("text", "")

    if not os.getenv("GROQ_API_KEY"):
        patch = _deterministic_extract(user_text)
        if not patch.get("defectSummary") or len(patch.get("defectSummary", "")) < 20:
            patch["defectSummary"] = _synthesize_formal_defect_summary(user_text, patch, current_form)

        root_cause, capaS = _generate_default_capa(user_text)
        return {
            "patch": patch,
            "intent": "update" if current_form else "create",
            "summary": "Local structured extraction applied.",
            "root_cause": root_cause,
            "capa_recommendations": capaS,
        }

    from langchain_groq import ChatGroq

    prompt = """You extract pharmaceutical customer-complaint details into a controlled QMS form.
Return only fields explicitly present or inferred from the user's latest message. For a correction or update, return intent as "update" and only the changed fields.

CRITICAL DEFECT SUMMARY SYNTHESIS RULE:
If "defectSummary" is not explicitly dictated word-for-word by the user as a full formal report, you MUST synthesize a formal 2-3 sentence QMS Defect Summary for "defectSummary" describing:
- The product name and batch number
- The observed physical/chemical/packaging defect
- The quality assurance impact requiring investigation.

Also recommend:
1. "risk": A high-level risk assessment statement (e.g. "Critical - foreign particle contamination requiring QA quarantine").
2. "root_cause_hypothesis": A 1-sentence scientific hypothesis for QA root cause investigation.
3. "capa_recommendations": 2 to 3 actionable Corrective And Preventive Action (CAPA) steps.

Valid form field keys MUST be chosen strictly from:
customerName, complaintSource, productName, strengthGrade, batchLotNumber, manufacturingDate, expiryDate, affectedQuantity, originatingSite, impactedMaterial, complaintType, complaintDate, defectSummary, detailedDescription, severity, priority.

Current form: {current_form}
User message: {text}""".format(current_form=current_form, text=user_text)

    model_names_to_try = [
        os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

    seen = set()
    models = [m for m in model_names_to_try if m and not (m in seen or seen.add(m))]

    last_exception = None
    for model_name in models:
        try:
            model = ChatGroq(model=model_name, temperature=0)
            result = model.with_structured_output(StructuredExtraction).invoke(prompt)
            patch = _map_updates_to_form_fields(result.updates)

            # Always merge deterministic high-precision regex extraction for complete coverage
            det_patch = _deterministic_extract(user_text)
            for k, v in det_patch.items():
                if v and not patch.get(k):
                    patch[k] = v

            # Synthesize formal defect summary if missing or brief
            existing_defect = patch.get("defectSummary") or current_form.get("defectSummary")
            if not existing_defect or len(existing_defect) < 20:
                patch["defectSummary"] = _synthesize_formal_defect_summary(user_text, patch, current_form)

            # Set detailedDescription to full narrative if missing
            if not patch.get("detailedDescription") and not current_form.get("detailedDescription"):
                patch["detailedDescription"] = user_text

            root_cause = result.root_cause_hypothesis
            capaS = result.capa_recommendations

            if not root_cause or not capaS:
                fallback_rc, fallback_capas = _generate_default_capa(user_text)
                root_cause = root_cause or fallback_rc
                capaS = capaS or fallback_capas

            return {
                "patch": patch,
                "intent": result.intent,
                "summary": result.summary or ("Updated complaint details." if result.intent == "update" else "Parsed new complaint details."),
                "risk": result.risk,
                "root_cause": root_cause,
                "capa_recommendations": capaS,
                "dropdown_actions": dict(result.dropdown_actions),
            }
        except Exception as e:
            last_exception = e

    patch = _deterministic_extract(user_text)
    if not patch.get("defectSummary") or len(patch.get("defectSummary", "")) < 20:
        patch["defectSummary"] = _synthesize_formal_defect_summary(user_text, patch, current_form)

    rc, capaS = _generate_default_capa(user_text)
    return {
        "patch": patch,
        "intent": "update" if current_form else "create",
        "summary": f"Fallback extraction applied (API note: {str(last_exception)})",
        "root_cause": rc,
        "capa_recommendations": capaS,
        "dropdown_actions": {},
    }


def normalize_patch(state: IntakeState) -> dict[str, Any]:
    patch = dict(state.get("patch", {}))
    if "severity" in patch:
        patch["severity"] = patch["severity"].title()
    if "priority" in patch:
        patch["priority"] = patch["priority"].title()
    return {"patch": patch}


def validate_completeness(state: IntakeState) -> dict[str, Any]:
    merged = state["current_form"] | state.get("patch", {})
    labels = {"productName": "Product name", "batchLotNumber": "Batch / lot number", "defectSummary": "Defect summary", "customerName": "Customer name"}
    missing = [label for field, label in labels.items() if not merged.get(field)]
    risk = state.get("risk")
    if not risk and merged.get("severity") in {"High", "Critical"}:
        risk = "High - quality defect requires QA triage"
    return {"missing_fields": missing, "risk": risk}


def build_message(state: IntakeState) -> dict[str, Any]:
    patch = state.get("patch", {})
    fields = ", ".join(patch) or "the complaint narrative"
    message = state.get("summary") or f"I updated {fields}."
    if state.get("missing_fields"):
        message += f" Please provide: {', '.join(state['missing_fields'])}."
    if state.get("risk"):
        message += " I also added an initial risk flag for human review."
    return {"summary": message}


def build_intake_graph():
    graph = StateGraph(IntakeState)
    graph.add_node("extract_fields", extract_fields)
    graph.add_node("normalize_patch", normalize_patch)
    graph.add_node("validate_completeness", validate_completeness)
    graph.add_node("build_message", build_message)
    graph.add_edge(START, "extract_fields")
    graph.add_edge("extract_fields", "normalize_patch")
    graph.add_edge("normalize_patch", "validate_completeness")
    graph.add_edge("validate_completeness", "build_message")
    graph.add_edge("build_message", END)
    return graph.compile()


intake_graph = build_intake_graph()


def run_intake(text: str, current_form: dict[str, str]) -> dict[str, Any]:
    return intake_graph.invoke({"text": text, "current_form": current_form})


def llm_is_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def configured_model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
