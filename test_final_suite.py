import requests
import json
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("       RUNNING FINAL COMPREHENSIVE SUITE TEST")
print("=" * 60)

results = []

def record(test_name, passed, details):
    status = "PASS" if passed else "FAIL"
    results.append((test_name, status, details))
    print(f"[{status}] {test_name}")
    if not passed:
        print(f"       Details: {details}")

# -------------------------------------------------------------
# TEST 1: Health Check
# -------------------------------------------------------------
try:
    r = requests.get(f"{BASE_URL}/api/health", timeout=5)
    data = r.json()
    passed = r.status_code == 200 and data.get("llm_configured") == True
    record("1. Backend Health & Groq LLM Status", passed, f"Status={r.status_code}, Model={data.get('model')}")
except Exception as e:
    record("1. Backend Health & Groq LLM Status", False, str(e))

# -------------------------------------------------------------
# TEST 2: Natural Language Initial Complaint Intake
# -------------------------------------------------------------
prompt_1 = "Apollo Pharmacy reported discolored capsules in Amoxicillin Capsules 500 mg. Batch number AMX240602. Manufacturing date March 2026. Expiry date February 2028. Please log this complaint"
current_form = {}

try:
    r = requests.post(f"{BASE_URL}/api/copilot/process", json={"text": prompt_1, "current_form": current_form})
    data = r.json()
    patch = data.get("patch", {})
    
    passed = (
        r.status_code == 200
        and patch.get("batchLotNumber") == "AMX240602"
        and "Amoxicillin" in patch.get("productName", "")
        and "Apollo Pharmacy" in patch.get("customerName", "")
    )
    record("2. Natural Language Intake (Entity Extraction)", passed, f"Extracted Patch: {patch}")
    if passed:
        current_form.update(patch)
except Exception as e:
    record("2. Natural Language Intake (Entity Extraction)", False, str(e))

# -------------------------------------------------------------
# TEST 3: Conversational Field Editing (Update Intent)
# -------------------------------------------------------------
prompt_2 = "ah sorry the batch number is BMX240602 and affected quantity is 48 capsules"

try:
    r = requests.post(f"{BASE_URL}/api/copilot/process", json={"text": prompt_2, "current_form": current_form})
    data = r.json()
    patch = data.get("patch", {})
    
    passed = (
        r.status_code == 200
        and patch.get("batchLotNumber") == "BMX240602"
        and "48" in patch.get("affectedQuantity", "")
    )
    record("3. Conversational Update (Partial Field Edit)", passed, f"Updated Fields: {patch}")
    if passed:
        current_form.update(patch)
except Exception as e:
    record("3. Conversational Update (Partial Field Edit)", False, str(e))

# -------------------------------------------------------------
# TEST 4: Document Upload — PDF Document Extraction
# -------------------------------------------------------------
pdf_path = r"sample_documents\Zenith_Life_Sciences_Complaint_Report.pdf"

try:
    with open(pdf_path, "rb") as f:
        files = {"file": ("Zenith_Life_Sciences_Complaint_Report.pdf", f, "application/pdf")}
        r = requests.post(f"{BASE_URL}/api/copilot/upload", files=files, data={"current_form": "{}"})
    
    data = r.json()
    patch = data.get("patch", {})
    risk = data.get("risk")
    
    passed = (
        r.status_code == 200
        and patch.get("batchLotNumber") == "MFH260712A"
        and "Metformin" in patch.get("productName", "")
        and risk is not None
    )
    record("4. PDF Document Upload Extraction", passed, f"Source={data.get('sourceFile')}, Product={patch.get('productName')}, Risk={risk}")
except Exception as e:
    record("4. PDF Document Upload Extraction", False, str(e))

# -------------------------------------------------------------
# TEST 5: Document Upload — Text File Extraction
# -------------------------------------------------------------
txt_path = r"sample_documents\Apollo_Pharmacy_Discolored_Capsules.txt"

try:
    with open(txt_path, "rb") as f:
        files = {"file": ("Apollo_Pharmacy_Discolored_Capsules.txt", f, "text/plain")}
        r = requests.post(f"{BASE_URL}/api/copilot/upload", files=files, data={"current_form": "{}"})
    
    data = r.json()
    patch = data.get("patch", {})
    
    passed = (
        r.status_code == 200
        and patch.get("batchLotNumber") == "AMX240602"
        and "Apollo Pharmacy" in patch.get("customerName", "")
    )
    record("5. Text Document Upload Extraction", passed, f"Extracted: {patch.get('productName')} / Batch: {patch.get('batchLotNumber')}")
except Exception as e:
    record("5. Text Document Upload Extraction", False, str(e))

# -------------------------------------------------------------
# TEST 6: Frontend Dev Server Ping (Vite Port 5173)
# -------------------------------------------------------------
try:
    r = requests.get("http://localhost:5173/", timeout=5)
    passed = r.status_code == 200
    record("6. Frontend React App Availability", passed, f"Port 5173 status code: {r.status_code}")
except Exception as e:
    record("6. Frontend React App Availability", False, str(e))

print("=" * 60)
print("                   TEST SUMMARY REPORT")
print("=" * 60)
all_passed = all(status == "PASS" for _, status, _ in results)
for test_name, status, details in results:
    print(f"{status:4} | {test_name}")

if all_passed:
    print("\nALL TESTS PASSED SUCCESSFULLY! SYSTEM IS 100% OPERATIONAL.")
else:
    print("\nSOME TESTS FAILED. PLEASE CHECK LOGS ABOVE.")
