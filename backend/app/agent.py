"""LangGraph workflow for safe, structured complaint intake."""

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
    dropdown_actions: dict[str, Literal["lower", "increase", "unclear"]] = Field(
        default_factory=dict,
        description="Relative dropdown change intents. Keys may only be severity or priority. Use lower or increase when the user asks to adjust a value without naming the final option."
    )


class IntakeState(TypedDict, total=False):
    text: str
    current_form: dict[str, str]
    patch: dict[str, str]
    intent: str
    summary: str
    missing_fields: list[str]
    risk: str | None
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
    # Imported lazily so FastAPI can still start before the graph runs.
    from .main import extract_patch

    return extract_patch(text)


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
    """Use Groq when configured; fallback gracefully if API issues occur."""
    if not os.getenv("GROQ_API_KEY"):
        patch = _deterministic_extract(state["text"])
        return {"patch": patch, "intent": "update" if state["current_form"] else "create", "summary": "Local structured extraction applied."}

    from langchain_groq import ChatGroq

    prompt = """You extract pharmaceutical customer-complaint details into a controlled QMS form.
Return only fields explicitly present in the user's latest message. For a correction or update, return intent as "update" and only the changed fields.
Never invent batch, dates, quantities, customer details, or risk facts. Risk is a human-review recommendation, not a decision.

Valid form field keys MUST be chosen strictly from:
- customerName
- complaintSource
- productName
- strengthGrade
- batchLotNumber
- manufacturingDate
- expiryDate
- affectedQuantity
- originatingSite
- impactedMaterial
- complaintType
- complaintDate
- defectSummary
- detailedDescription
- severity
- priority

For severity, use only Low, Medium, High, Critical, or Needs QA Review.
For priority, use only Low, Medium, High, Urgent, or Needs QA Review.
When the user asks to lower or increase Severity or Priority without naming an exact option, record that in dropdown_actions instead of guessing an exact label. Identify the target dropdown from the user's meaning, including paraphrases such as less serious, de-escalate, make it more urgent, or raise the risk level.

Current form: {current_form}
User message: {text}""".format(current_form=state["current_form"], text=state["text"])

    model_names_to_try = [
        os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

    # De-duplicate preserving order
    seen = set()
    models = [m for m in model_names_to_try if m and not (m in seen or seen.add(m))]

    last_exception = None
    for model_name in models:
        try:
            model = ChatGroq(model=model_name, temperature=0)
            result = model.with_structured_output(StructuredExtraction).invoke(prompt)
            patch = _map_updates_to_form_fields(result.updates)
            dropdown_actions = {
                field: action for field, action in result.dropdown_actions.items()
                if field in {"severity", "priority"} and action in {"lower", "increase", "unclear"}
            }
            
            # Fallback for empty patch: run deterministic extraction if LLM missed simple pattern
            if not patch:
                patch = _deterministic_extract(state["text"])

            return {
                "patch": patch,
                "intent": result.intent,
                "summary": result.summary or ("Updated complaint details." if result.intent == "update" else "Parsed new complaint details."),
                "risk": result.risk,
                "dropdown_actions": dropdown_actions,
            }
        except Exception as e:
            last_exception = e

    # Fallback to local extraction if all model attempts fail
    patch = _deterministic_extract(state["text"])
    return {
        "patch": patch,
        "intent": "update" if state["current_form"] else "create",
        "summary": "Fallback extraction applied.",
        "dropdown_actions": _relative_actions_from_text(state["text"]),
    }


def _relative_actions_from_text(text: str) -> dict[str, str]:
    """Safety net when a provider is unavailable; the LLM remains the primary interpreter."""
    lowered = text.lower()
    if any(word in lowered for word in ("lower", "decrease", "reduce", "less", "downgrade", "de-escalate")):
        action = "lower"
    elif any(word in lowered for word in ("increase", "raise", "higher", "escalate", "more urgent")):
        action = "increase"
    else:
        return {}

    targets: dict[str, str] = {}
    if any(word in lowered for word in ("severity", "critical", "serious", "risk")):
        targets["severity"] = action
    if any(word in lowered for word in ("priority", "urgent")):
        targets["priority"] = action
    return targets


def normalize_patch(state: IntakeState) -> dict[str, Any]:
    patch = dict(state.get("patch", {}))
    dropdown_actions = state.get("dropdown_actions") or _relative_actions_from_text(state["text"])

    # A relative request gets a stable business fallback, regardless of wording:
    # lower -> Medium and increase -> High for both controlled dropdowns.
    for field, action in dropdown_actions.items():
        if field in {"severity", "priority"}:
            if action == "lower":
                patch[field] = "Medium"
            elif action == "increase":
                patch[field] = "High"
            elif action == "unclear" and field not in patch:
                patch[field] = "Needs QA Review"

    severity_values = {"Low", "Medium", "High", "Critical", "Needs QA Review"}
    priority_values = {"Low", "Medium", "High", "Urgent", "Needs QA Review"}
    if "severity" in patch:
        value = patch["severity"].strip().title()
        patch["severity"] = value if value in severity_values else "Needs QA Review"
    if "priority" in patch:
        value = patch["priority"].strip().title()
        patch["priority"] = value if value in priority_values else "Needs QA Review"
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
    """Expose configuration state without ever returning a secret."""
    return bool(os.getenv("GROQ_API_KEY"))


def configured_model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
