import { type ChangeEvent } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { resetForm, updateField } from '../features/complaint/complaintSlice';
import { addMessage, clearCopilotState } from '../features/copilot/copilotSlice';
import type { ComplaintForm as ComplaintFormType } from '../features/complaint/types';

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

  const handleSave = () => {
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

    const productDetails = form.productName
      ? `${form.productName}${form.batchLotNumber ? ` (Batch: ${form.batchLotNumber})` : ''}`
      : 'Customer complaint';

    // Dispatch acknowledgement message to chat log
    dispatch(
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        text: `✅ ${productDetails} has been successfully committed to the QMS ledger! The form has been reset for new intake.`,
      })
    );

    // Clear copilot risk/missing fields & reset form
    dispatch(clearCopilotState());
    dispatch(resetForm());
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
        <span className="status-pill">{status}</span>
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
        <button className="primary" onClick={handleSave}>▣ Save complaint</button>
      </div>
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
