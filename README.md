# AIVOA Complaint Copilot — AI-Powered Customer Complaint Management System

An AI-assisted customer complaint intake prototype for API and finished dosage form (FDF) quality assurance teams.

## Key Features

- **React + Redux UI**: Clean 2-panel QMS complaint form with real-time field-level updates.
- **FastAPI + LangGraph AI Agent**: Structured state graph workflow (`extract_fields` → `normalize_patch` → `validate_completeness` → `build_message`).
- **Groq API (`llama-3.3-70b-versatile`)**: Entity extraction, natural language parsing, and conversational editing.
- **Document OCR/Parsing**: Extracts complaint data directly from `.pdf`, `.docx`, `.txt`, and `.eml` files.
- **MySQL / PostgreSQL Database Persistence**: Full database integration storing committed QMS complaints and risk assessments.
- **QMS Complaints Ledger**: Built-in saved complaints drawer & viewer modal.

---

## Technical Architecture & Database

The backend uses **SQLAlchemy ORM** configured to target **MySQL** or **PostgreSQL** as specified in the mandatory tech stack requirements.

### Database Configuration (`.env`)

Set your database connection string in `.env`:

```env
# For MySQL Database (PyMySQL driver)
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/qms_complaints

# For PostgreSQL Database (psycopg2 driver)
# DATABASE_URL=postgresql://postgres:password@localhost:5432/qms_complaints
```

---

## Run Locally

### 1. Frontend Setup
```powershell
npm install --prefix frontend
npm run dev --prefix frontend
```

### 2. Backend Setup
```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --reload --app-dir backend
```

Open `http://localhost:5173` to launch the application!
