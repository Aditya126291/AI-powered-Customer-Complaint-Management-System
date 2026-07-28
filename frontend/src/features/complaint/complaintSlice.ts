import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { emptyComplaint, type ComplaintForm } from './types';

interface ComplaintState {
  form: ComplaintForm;
  status: 'Draft' | 'Pending Triage' | 'Saved';
  changedFields: string[];
  lastSavedNumber: string | null;
  activeSavedDbId: number | null;
}

const initialState: ComplaintState = {
  form: emptyComplaint,
  status: 'Pending Triage',
  changedFields: [],
  lastSavedNumber: null,
  activeSavedDbId: null,
};

const complaintSlice = createSlice({
  name: 'complaint',
  initialState,
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
    markSaved(state, action: PayloadAction<{ id: number; complaintNumber: string }>) {
      state.status = 'Saved';
      state.changedFields = [];
      state.activeSavedDbId = action.payload.id;
      state.lastSavedNumber = action.payload.complaintNumber;
    },
  },
});

export const { updateField, applyPatch, resetForm, markSaved } = complaintSlice.actions;
export default complaintSlice.reducer;
