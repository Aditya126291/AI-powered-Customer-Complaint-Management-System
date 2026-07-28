import { useEffect, useState, type ChangeEvent } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { markSaved, resetForm, updateField } from '../features/complaint/complaintSlice';
import { commitComplaintToDb, fetchSavedComplaints, updateSavedComplaintInDb } from '../features/copilot/api';
import { addMessage, clearCopilotState } from '../features/copilot/copilotSlice';
import type { ComplaintForm as ComplaintFormType } from '../features/complaint/types';
import { SavedComplaintsModal } from './SavedComplaintsModal';

type FieldProps = { label: string; field: keyof ComplaintFormType; type?: 'text' | 'date'; placeholder?: string; };

function Field({ label, field, type = 'text', placeholder }: FieldProps) {
  const dispatch = useAppDispatch();
  const form = useAppSelector((s) => s.complaint.form);
  const changed = useAppSelector((s) => s.complaint.changedFields.includes(field));
  return (
    <label className="field">
      <span>{label}</span>
      <input
        className={changed ? 'ai-updated' : ''}
        type={type}
        value={form[field]}
        placeholder={placeholder}
        onChange={(e: ChangeEvent<HTMLInputElement>) => dispatch(updateField({ field, value: e.target.value }))}
      />
    </label>
  );
}

function SelectField({ label, field, options }: { label: string; field: 'severity' | 'priority'; options: string[] }) {
  const dispatch = useAppDispatch();
  const value = useAppSelector((s) => s.complaint.form[field]);
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => dispatch(updateField({ field, value: e.target.value }))}>
        <option value="">Select…</option>
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

export function ComplaintForm() {
  const dispatch = useAppDispatch();
  const form = useAppSelector((s) => s.complaint.form);
  const status = useAppSelector((s) => s.complaint.status);
  const activeSavedDbId = useAppSelector((s) => s.complaint.activeSavedDbId);
  const lastSavedNumber = useAppSelector((s) => s.complaint.lastSavedNumber);
  const risk = useAppSelector((s) => s.copilot.risk);

  const [savedModalOpen, setSavedModalOpen] = useState(false);
  const [savedCount, setSavedCount] = useState(0);

  const refreshCount = async () => {
    try {
      const records = await fetchSavedComplaints();
      setSavedCount(records.length);
    } catch {
      // Ignore
    }
  };

  useEffect(() => {
    void refreshCount();
  }, []);

  // Auto-sync edits to database if record has already been saved and user is still editing
  useEffect(() => {
    if (activeSavedDbId && status === 'Saved') {
      const timer = setTimeout(() => {
        void updateSavedComplaintInDb(activeSavedDbId, form, risk).then(() => {
          void refreshCount();
        });
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [form, activeSavedDbId, status, risk]);

  const handleSaveOrUpdate = async () => {
    const isFormEmpty = Object.values(form).every((v) => !v || v.trim() === '');
    if (isFormEmpty) {
      dispatch(
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          text: '⚠️ Cannot save: The complaint form is empty. Please enter or extract complaint details first.',
        })
      );
      return;
    }

    try {
      if (activeSavedDbId) {
        // Update existing record
        const updatedRecord = await updateSavedComplaintInDb(activeSavedDbId, form, risk);
        void refreshCount();
        dispatch(
          addMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            text: `📝 Updated Record No. ${updatedRecord.complaintNumber} in Database! Edits reflected in Saved Complaints.`,
          })
        );
      } else {
        // Commit new record
        const savedRecord = await commitComplaintToDb(form, risk);
        void refreshCount();

        const productInfo = savedRecord.productName
          ? `${savedRecord.productName}${savedRecord.batchLotNumber ? ` (Batch: ${savedRecord.batchLotNumber})` : ''}`
          : 'Customer complaint';

        dispatch(markSaved({ id: savedRecord.id, complaintNumber: savedRecord.complaintNumber }));

        dispatch(
          addMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            text: `✅ Saved to QMS Database! ${productInfo} assigned Record No. ${savedRecord.complaintNumber}.\n\nFurther edits will auto-sync to this record until you click "File another complaint".`,
          })
        );
      }
    } catch (error) {
      dispatch(
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          text: error instanceof Error ? error.message : 'Could not save complaint to database.',
        })
      );
    }
  };

  const handleReset = () => {
    dispatch(clearCopilotState());
    dispatch(resetForm());
    dispatch(
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        text: '↻ Form has been reset.',
      })
    );
  };

  return (
    <section className="form-card">
      <header className="form-header">
        <div>
          <h1>Log Customer Complaint</h1>
          <p>API & FDF Quality Assurance Module</p>
        </div>
        <div className="header-actions">
          <button className="ledger-btn" onClick={() => setSavedModalOpen(true)}>
            📁 Saved Complaints ({savedCount})
          </button>
          <span className={`status-pill ${status === 'Saved' ? 'status-saved' : ''}`}>
            {status === 'Saved' ? `Saved (${lastSavedNumber})` : status}
          </span>
        </div>
      </header>

      <FormSection title="1. Origin & customer details">
        <Field label="Complaint Source" field="complaintSource" placeholder="e.g., Apollo Pharmacy" />
        <Field label="Customer Name" field="customerName" placeholder="Awaiting AI extraction…" />
      </FormSection>

      <FormSection title="2. Product & batch identification">
        <Field label="Product Name (API/FDF)" field="productName" placeholder="Awaiting AI extraction…" />
        <Field label="Product Strength / Grade" field="strengthGrade" placeholder="e.g., 500 mg" />
        <Field label="Batch / Lot Number" field="batchLotNumber" placeholder="Awaiting AI extraction…" />
        <Field label="Affected Quantity" field="affectedQuantity" placeholder="e.g., 48 capsules" />
        <Field label="Manufacturing Date" field="manufacturingDate" placeholder="e.g., March 2026" />
        <Field label="Expiry Date" field="expiryDate" placeholder="e.g., February 2028" />
      </FormSection>

      <FormSection title="3. Facility & material impact">
        <Field label="Originating Site Block" field="originatingSite" placeholder="Awaiting AI classification…" />
        <Field label="Impacted Non-Product Material" field="impactedMaterial" placeholder="e.g., primary packaging" />
      </FormSection>

      <FormSection title="4. Complaint details">
        <Field label="Complaint Type" field="complaintType" placeholder="e.g., Product defect" />
        <Field label="Complaint Date" field="complaintDate" placeholder="e.g., 28 July 2026" />
        <label className="field field-wide">
          <span>Structured Defect Summary</span>
          <textarea
            value={form.defectSummary}
            placeholder="AI will synthesize the complaint into a formal QMS description…"
            onChange={(e) => dispatch(updateField({ field: 'defectSummary', value: e.target.value }))}
          />
        </label>
      </FormSection>

      <FormSection title="5. Initial assessment & priority">
        <SelectField label="Initial Severity" field="severity" options={['Low', 'Medium', 'High', 'Critical', 'Needs QA Review']} />
        <SelectField label="Priority" field="priority" options={['Low', 'Medium', 'High', 'Urgent', 'Needs QA Review']} />
      </FormSection>

      <div className="form-actions">
        <button className="secondary" onClick={handleReset}>↻ Reset form</button>
        <button className="primary" onClick={() => void handleSaveOrUpdate()}>
          {status === 'Saved' ? '✓ Update saved complaint' : '▣ Save complaint'}
        </button>
      </div>

      <SavedComplaintsModal isOpen={savedModalOpen} onClose={() => { setSavedModalOpen(false); void refreshCount(); }} />
    </section>
  );
}

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset>
      <legend>{title}</legend>
      <div className="field-grid">{children}</div>
    </fieldset>
  );
}
