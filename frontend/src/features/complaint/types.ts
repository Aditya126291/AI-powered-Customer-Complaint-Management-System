export type Severity = 'Low' | 'Medium' | 'High' | 'Critical' | 'Needs QA Review' | '';
export type Priority = 'Low' | 'Medium' | 'High' | 'Urgent' | 'Needs QA Review' | '';

export interface ComplaintForm {
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
  severity: Severity;
  priority: Priority;
}

export const emptyComplaint: ComplaintForm = {
  customerName: '', complaintSource: '', productName: '', strengthGrade: '', batchLotNumber: '',
  manufacturingDate: '', expiryDate: '', affectedQuantity: '', originatingSite: '', impactedMaterial: '',
  complaintType: '', complaintDate: '', defectSummary: '', detailedDescription: '', severity: '', priority: '',
};
