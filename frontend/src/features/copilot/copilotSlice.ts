import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { ComplaintForm } from '../complaint/types';

export interface ChatMessage { id: string; role: 'assistant' | 'user'; text: string; }
interface CopilotState { messages: ChatMessage[]; processing: boolean; missingFields: string[]; risk: string | null; }
const initialState: CopilotState = {
  processing: false, missingFields: [], risk: null,
  messages: [{ id: 'welcome', role: 'assistant', text: 'Ready to process a new complaint. Paste the customer report or describe the update you want to make.' }],
};
const copilotSlice = createSlice({
  name: 'copilot', initialState,
  reducers: {
    addMessage(state, action: PayloadAction<ChatMessage>) { state.messages.push(action.payload); },
    setProcessing(state, action: PayloadAction<boolean>) { state.processing = action.payload; },
    setAiResult(state, action: PayloadAction<{ missingFields: string[]; risk: string | null; patch?: Partial<ComplaintForm> }>) {
      state.missingFields = action.payload.missingFields; state.risk = action.payload.risk;
    },
  },
});
export const { addMessage, setProcessing, setAiResult } = copilotSlice.actions;
export default copilotSlice.reducer;
