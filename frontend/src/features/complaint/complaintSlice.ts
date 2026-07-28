import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { emptyComplaint, type ComplaintForm } from './types';

interface ComplaintState { form: ComplaintForm; status: 'Draft' | 'Pending Triage' | 'Saved'; changedFields: string[]; }
const initialState: ComplaintState = { form: emptyComplaint, status: 'Pending Triage', changedFields: [] };

const complaintSlice = createSlice({
  name: 'complaint', initialState,
  reducers: {
    updateField(state, action: PayloadAction<{ field: keyof ComplaintForm; value: string }>) {
      const { field, value } = action.payload;
      state.form[field] = value as never;
      if (!state.changedFields.includes(field)) state.changedFields.push(field);
    },
    applyPatch(state, action: PayloadAction<Partial<ComplaintForm>>) {
      Object.entries(action.payload).forEach(([field, value]) => {
        if (value !== undefined && value !== '') {
          state.form[field as keyof ComplaintForm] = value as never;
          if (!state.changedFields.includes(field)) state.changedFields.push(field);
        }
      });
    },
    resetForm: () => initialState,
    markSaved(state) { state.status = 'Saved'; state.changedFields = []; },
  },
});
export const { updateField, applyPatch, resetForm, markSaved } = complaintSlice.actions;
export default complaintSlice.reducer;
