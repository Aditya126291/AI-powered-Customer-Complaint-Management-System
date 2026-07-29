from __future__ import annotations

import os
import re
from typing import Any, TypedDict

from pydantic import BaseModel, Field


def llm_is_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def configured_model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class StructuredExtraction(BaseModel):
    intent: str = Field(description="Either 'create' for new intake or 'update' for targeted field edits")
    updates: dict[str, str] = Field(description="Map of QMS form field names to extracted string values")
    risk_assessment: str = Field(description="High-level risk narrative for human QA review")
    root_cause_hypothesis: str = Field(description="Scientific hypothesis for QA root cause investigation")
    capa_recommendations: list[str] = Field(description="2-3 actionable CAPA steps (Containment, Root Cause, Preventive)")


class IntakeState(TypedDict, total=False):
    text: str
    current_form: dict[str, Any]
    patch: dict[str, Any]
    missing_fields: list[str]
    summary: str
    intent: str
    risk: str
    root_cause: str
    capa_recommendations: list[str]


ALLOWED_FIELDS = {
    "customerName",
    "complaintSource",
    "productName",
    "strengthGrade",
    "batchLotNumber",
    "manufacturingDate",
    "expiryDate",
    "affectedQuantity",
    "originatingSite",
    "impactedMaterial",
    "complaintType",
    "complaintDate",
    "defectSummary",
    "detailedDescription",
    "severity",
    "priority",
    "riskAssessment",
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


def _deterministic_extract(text: str, is_update: bool = False) -> dict[str, str]:
    from .main import extract_patch
    return extract_patch(text, is_update=is_update)


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
    is_update = bool(current_form and any(v for v in current_form.values() if v))

    if not os.getenv("GROQ_API_KEY"):
        patch = _deterministic_extract(user_text, is_update=is_update)
        if not is_update and (not patch.get("defectSummary") or len(patch.get("defectSummary", "")) < 20):
            patch["defectSummary"] = _synthesize_formal_defect_summary(user_text, patch, current_form)

        root_cause, capaS = _generate_default_capa(user_text)
        summary_msg = f"Updated {', '.join(patch.keys())} in form." if (is_update and patch) else "Extracted complaint details into the form."
        return {
            "patch": patch,
            "intent": "update" if is_update else "create",
            "summary": summary_msg,
            "root_cause": root_cause,
            "capa_recommendations": capaS,
        }

    from langchain_groq import ChatGroq

    prompt = """You extract pharmaceutical customer-complaint details into a controlled QMS form.
Return ONLY fields explicitly present or updated in the user's latest message. For a correction or targeted edit, return intent as "update" and ONLY the specific changed fields without returning unchanged fields.

Valid form field keys MUST be chosen strictly from:
customerName, complaintSource, productName, strengthGrade, batchLotNumber, manufacturingDate, expiryDate, affectedQuantity, originatingSite, impactedMaterial, complaintType, complaintDate, defectSummary, detailedDescription, severity, priority.

Current form state: {current_form}
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

            # Merge deterministic high-precision regex extraction
            det_patch = _deterministic_extract(user_text, is_update=is_update)
            for k, v in det_patch.items():
                if v and not patch.get(k):
                    patch[k] = v

            if not is_update:
                # Synthesize formal defect summary if missing or brief during initial creation
                existing_defect = patch.get("defectSummary") or current_form.get("defectSummary")
                if not existing_defect or len(existing_defect) < 20:
                    patch["defectSummary"] = _synthesize_formal_defect_summary(user_text, patch, current_form)

                # Set detailedDescription to full narrative if missing during initial creation
                if not patch.get("detailedDescription") and not current_form.get("detailedDescription"):
                    patch["detailedDescription"] = user_text

            root_cause = result.root_cause_hypothesis
            capaS = result.capa_recommendations
            risk_val = result.risk_assessment

            if not root_cause or not capaS:
                rc_def, capa_def = _generate_default_capa(user_text)
                if not root_cause:
                    root_cause = rc_def
                if not capaS:
                    capaS = capa_def

            summary_msg = f"Updated {', '.join(patch.keys())} in form." if (is_update and patch) else "Extracted complaint details into the form."

            return {
                "patch": patch,
                "intent": result.intent or ("update" if is_update else "create"),
                "summary": summary_msg,
                "risk": risk_val or "High - Quality complaint requiring QA review",
                "root_cause": root_cause,
                "capa_recommendations": capaS,
            }
        except Exception as err:
            last_exception = err
            continue

    patch = _deterministic_extract(user_text, is_update=is_update)
    if not is_update and (not patch.get("defectSummary") or len(patch.get("defectSummary", "")) < 20):
        patch["defectSummary"] = _synthesize_formal_defect_summary(user_text, patch, current_form)

    root_cause, capaS = _generate_default_capa(user_text)
    summary_msg = f"Updated {', '.join(patch.keys())} in form." if (is_update and patch) else "Extracted complaint details into the form."

    return {
        "patch": patch,
        "intent": "update" if is_update else "create",
        "summary": summary_msg,
        "root_cause": root_cause,
        "capa_recommendations": capaS,
    }


def normalize_patch(state: IntakeState) -> dict[str, Any]:
    return {"patch": state.get("patch", {})}


def missing_fields(form: dict[str, Any]) -> list[str]:
    labels = {"productName": "Product name", "batchLotNumber": "Batch / lot number", "defectSummary": "Defect summary", "customerName": "Customer name"}
    return [label for field, label in labels.items() if not form.get(field)]


def validate_completeness(state: IntakeState) -> dict[str, Any]:
    patch = state.get("patch", {})
    current_form = state.get("current_form", {})
    merged_form = current_form | patch
    missing = missing_fields(merged_form)
    return {"missing_fields": missing}


def build_message(state: IntakeState) -> dict[str, Any]:
    missing = state.get("missing_fields", [])
    if missing:
        missing_str = ", ".join(missing)
        msg = f"Parsed complaint details. Missing key fields for triage: {missing_str}."
    else:
        msg = "Parsed new complaint details. All primary triage fields populated."
    return {"summary": msg}


from langgraph.graph import END, START, StateGraph  # noqa: E402

graph_builder = StateGraph(IntakeState)
graph_builder.add_node("extract_fields", extract_fields)
graph_builder.add_node("normalize_patch", normalize_patch)
graph_builder.add_node("validate_completeness", validate_completeness)
graph_builder.add_node("build_message", build_message)

graph_builder.add_edge(START, "extract_fields")
graph_builder.add_edge("extract_fields", "normalize_patch")
graph_builder.add_edge("normalize_patch", "validate_completeness")
graph_builder.add_edge("validate_completeness", "build_message")
graph_builder.add_edge("build_message", END)

intake_graph = graph_builder.compile()


def run_intake(text: str, current_form: dict[str, Any] | None = None) -> dict[str, Any]:
    initial_state: IntakeState = {
        "text": text,
        "current_form": current_form or {},
    }
    return intake_graph.invoke(initial_state)
