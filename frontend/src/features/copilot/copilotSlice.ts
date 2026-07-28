import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { ComplaintForm } from '../complaint/types';

export interface ChatMessage { id: string; role: 'assistant' | 'user'; text: string; }

interface CopilotState {
  messages: ChatMessage[];
  processing: boolean;
  missingFields: string[];
  risk: string | null;
  rootCause: string | null;
  capaRecommendations: string[];
}

const INITIAL_WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  text: 'Ready to process a new complaint. Paste the customer report or drop a document below.',
};

const initialState: CopilotState = {
  processing: false,
  missingFields: [],
  risk: null,
  rootCause: null,
  capaRecommendations: [],
  messages: [INITIAL_WELCOME],
};

const copilotSlice = createSlice({
  name: 'copilot',
  initialState,
  reducers: {
    addMessage(state, action: PayloadAction<ChatMessage>) {
      state.messages.push(action.payload);
    },
    setProcessing(state, action: PayloadAction<boolean>) {
      state.processing = action.payload;
    },
    setAiResult(
      state,
      action: PayloadAction<{
        missingFields: string[];
        risk: string | null;
        rootCause?: string | null;
        capaRecommendations?: string[];
        patch?: Partial<ComplaintForm>;
      }>
    ) {
      state.missingFields = action.payload.missingFields;
      state.risk = action.payload.risk;
      state.rootCause = action.payload.rootCause || null;
      state.capaRecommendations = action.payload.capaRecommendations || [];
    },
    clearCopilotState(state) {
      state.missingFields = [];
      state.risk = null;
      state.rootCause = null;
      state.capaRecommendations = [];
    },
    resetChat(state) {
      state.messages = [{ id: crypto.randomUUID(), role: 'assistant', text: 'Fresh chat started. Form and copilot context have been reset.' }];
      state.missingFields = [];
      state.risk = null;
      state.rootCause = null;
      state.capaRecommendations = [];
      state.processing = false;
    },
  },
});

export const { addMessage, setProcessing, setAiResult, clearCopilotState, resetChat } = copilotSlice.actions;
export default copilotSlice.reducer;
