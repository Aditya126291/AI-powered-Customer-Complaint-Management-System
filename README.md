# AIVOA Complaint Copilot

An AI-assisted customer complaint intake prototype for API and finished dosage form (FDF) quality teams.

## Current milestone

- React + Redux complaint form with full manual editing
- Copilot chat with field-level updates and visible missing-data/risk feedback
- FastAPI + LangGraph workflow: extract → normalize → validate → response

## Run locally

```powershell
pnpm install
pnpm --dir frontend dev
```

In another terminal:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --reload --app-dir backend
```

### Enable Groq

1. Create a Groq API key in the [Groq Console](https://console.groq.com/keys).
2. Copy `.env.example` to a new `.env` file in the project root.
3. Set `GROQ_API_KEY` in that local file, then restart the API server.

The `.env` file is ignored by Git. Never paste the key into source files or commit it.

Open http://localhost:5173. Paste a message such as:

> Apollo Pharmacy reported discolored Amoxicillin Capsules 500 mg. Batch number AMX240602. Manufacturing date March 2026. Expiry date February 2028. Affected quantity is 48 capsules.

Set `GROQ_API_KEY` before starting the API to use Groq. The assignment's required `gemma2-9b-it` model was decommissioned by Groq in October 2025, so the app uses Groq's official replacement, `llama-3.1-8b-instant`, by default. You can override this with `GROQ_MODEL` in `.env`. Without a key, the graph uses a deterministic local extractor, so the complete demo still runs offline.

The next milestone persists complaints and their audit events in PostgreSQL.
