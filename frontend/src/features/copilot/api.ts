import type { ComplaintForm } from '../complaint/types';

export interface AiResponse { message: string; patch: Partial<ComplaintForm>; missingFields: string[]; risk: string | null; }
export interface UploadedDocumentResponse extends AiResponse { sourceFile: string; extractedCharacters: number; textTruncated: boolean; }

export interface SavedComplaintRecord {
  id: number;
  complaintNumber: string;
  customerName: string;
  complaintSource: string;
  productName: string;
  strengthGrade: string;
  batchLotNumber: string;
  manufacturingDate: string;
  expiryDate: string;
  affectedQuantity: string;
  originatingSite: string;
  impactedMaterial: string;
  complaintType: string;
  complaintDate: string;
  defectSummary: string;
  detailedDescription: string;
  severity: string;
  priority: string;
  riskAssessment: string;
  status: string;
  createdAt: string;
}

async function readResponse<T>(response: Response): Promise<T> {
  if (response.ok) return response.json() as Promise<T>;
  const body = await response.json().catch(() => null) as { detail?: string } | null;
  throw new Error(body?.detail ?? 'The AI service could not process that request.');
}

export async function processComplaint(text: string, currentForm: ComplaintForm): Promise<AiResponse> {
  const response = await fetch('/api/copilot/process', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, current_form: currentForm }),
  });
  return readResponse<AiResponse>(response);
}

export async function uploadComplaint(file: File, currentForm: ComplaintForm): Promise<UploadedDocumentResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('current_form', JSON.stringify(currentForm));
  const response = await fetch('/api/copilot/upload', { method: 'POST', body: formData });
  return readResponse<UploadedDocumentResponse>(response);
}

export async function commitComplaintToDb(form: ComplaintForm, risk: string | null): Promise<SavedComplaintRecord> {
  const response = await fetch('/api/complaints/commit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ form, risk }),
  });
  return readResponse<SavedComplaintRecord>(response);
}

export async function fetchSavedComplaints(): Promise<SavedComplaintRecord[]> {
  const response = await fetch('/api/complaints');
  return readResponse<SavedComplaintRecord[]>(response);
}

export async function deleteSavedComplaint(id: number): Promise<void> {
  const response = await fetch(`/api/complaints/${id}`, { method: 'DELETE' });
  await readResponse<{ status: string }>(response);
}
