import time
import requests
import json

BASE_URL = "http://localhost:8000"

print("Waiting for server startup...")
time.sleep(3)

# 1. Test Health endpoint with database info
r = requests.get(f"{BASE_URL}/api/health")
print("Health Status:", r.status_code, r.json())

# 2. Test Committing a complaint to Database
sample_form = {
    "customerName": "Zenith Life Sciences / ABC Formulations",
    "complaintSource": "Email",
    "productName": "Metformin Hydrochloride API",
    "strengthGrade": "IP/BP Grade",
    "batchLotNumber": "MFH260712A",
    "manufacturingDate": "25 June 2026",
    "expiryDate": "Not Provided",
    "affectedQuantity": "25 kg (1 HDPE Drum)",
    "originatingSite": "API Synthesis Unit - Block B",
    "impactedMaterial": "Primary Packaging (HDPE Drum)",
    "complaintType": "Foreign Matter Contamination",
    "complaintDate": "26 July 2026",
    "defectSummary": "Multiple dark foreign particles found inside bulk powder.",
    "detailedDescription": "Dark foreign particles observed during incoming QC inspection.",
    "severity": "Critical",
    "priority": "High"
}

r_commit = requests.post(f"{BASE_URL}/api/complaints/commit", json={"form": sample_form, "risk": "Critical QA Impact"})
print("Commit Status:", r_commit.status_code)
saved_data = r_commit.json()
print("Saved Record:", json.dumps(saved_data, indent=2))

# 3. Test Retrieving saved complaints list from Database
r_list = requests.get(f"{BASE_URL}/api/complaints")
print("List Complaints Status:", r_list.status_code)
records = r_list.json()
print(f"Total Saved Records in DB: {len(records)}")

if len(records) > 0:
    print("Database Persistence Test PASSED SUCCESSFULLY!")
else:
    print("Database Persistence Test FAILED!")
