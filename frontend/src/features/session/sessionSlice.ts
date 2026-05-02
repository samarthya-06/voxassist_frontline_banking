import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type Speaker = "customer" | "staff" | "assistant";

export type TranscriptItem = {
  id: string;
  speaker: Speaker;
  sourceLanguage: string;
  originalText: string;
  translatedText: string;
  confidence: number;
  timestamp: string;
};

export type BankingEntities = {
  customerName: string;
  pan: string;
  accountType: string;
  product: string;
  phone: string;
  amount: string;
  cardLast4: string;
};

export type ComplianceAlert = {
  severity: "info" | "warning" | "block";
  message: string;
};

export type SopCitation = {
  documentId: string;
  chunkId: string;
  title: string;
  source: string;
  category: string;
  branchId: string | null;
  effectiveFrom: string | null;
  effectiveTo: string | null;
  version: string | null;
  score: number;
  excerpt: string;
};

export type SopResult = {
  title: string;
  answer: string;
  source: string;
  citations?: SopCitation[];
  confidence?: number;
  effectiveFrom?: string | null;
  effectiveTo?: string | null;
  branchId?: string | null;
  requiresStaffVerification?: boolean;
};

// ── Form Interview Types ──────────────────────────────────────────────────
export type FormFieldDef = {
  key: string;
  label: string;
  question: string;
  fieldType: string;
  options: string[] | null;
  required: boolean;
};

export type FormDefinition = {
  formType: string;
  title: string;
  description: string;
  icon: string;
  totalFields: number;
  fields: FormFieldDef[];
};

export type FormCurrentField = {
  key: string;
  label: string;
  fieldType: string;
  options: string[] | null;
};

export type FormInterviewState = {
  active: boolean;
  formType: string | null;
  formDefinition: FormDefinition | null;
  currentField: FormCurrentField | null;
  currentQuestion: string | null;
  currentQuestionTranslated: string | null;
  progress: number;
  filledFields: Record<string, string>;
  totalFields: number;
  filledCount: number;
  isComplete: boolean;
  pdfReady: boolean;
  pdfUrl: string | null;
  lastFilledKey: string | null;
  lastFilledValue: string | null;
};

type SessionState = {
  connectionStatus: "idle" | "connecting" | "connected" | "offline";
  listenMode: "customer" | "staff";
  isRecording: boolean;
  isMuted: boolean;
  language: string;
  languageCode: string;
  transcript: TranscriptItem[];
  entities: BankingEntities;
  actionChips: string[];
  complianceAlert: ComplianceAlert | null;
  sopResult: SopResult | null;
  bilingualSummary: {
    english: string[];
    customerLanguage: string[];
  };
  escalationAlert: string | null;
  formInterview: FormInterviewState;
};

const initialFormInterview: FormInterviewState = {
  active: false,
  formType: null,
  formDefinition: null,
  currentField: null,
  currentQuestion: null,
  currentQuestionTranslated: null,
  progress: 0,
  filledFields: {},
  totalFields: 0,
  filledCount: 0,
  isComplete: false,
  pdfReady: false,
  pdfUrl: null,
  lastFilledKey: null,
  lastFilledValue: null,
};

const initialState: SessionState = {
  connectionStatus: "idle",
  listenMode: "customer",
  isRecording: false,
  isMuted: false,
  language: "Marathi",
  languageCode: "mr-IN",
  transcript: [],
  entities: {
    customerName: "",
    pan: "",
    accountType: "",
    product: "",
    phone: "",
    amount: "",
    cardLast4: ""
  },
  actionChips: [],
  complianceAlert: null,
  sopResult: null,
  bilingualSummary: {
    english: [],
    customerLanguage: []
  },
  escalationAlert: null,
  formInterview: initialFormInterview,
};

const sessionSlice = createSlice({
  name: "session",
  initialState,
  reducers: {
    setConnectionStatus: (state, action: PayloadAction<SessionState["connectionStatus"]>) => {
      state.connectionStatus = action.payload;
    },
    setListenMode: (state, action: PayloadAction<SessionState["listenMode"]>) => {
      state.listenMode = action.payload;
    },
    setRecording: (state, action: PayloadAction<boolean>) => {
      state.isRecording = action.payload;
    },
    setMuted: (state, action: PayloadAction<boolean>) => {
      state.isMuted = action.payload;
    },
    resetSession: () => initialState,
    addTranscript: (state, action: PayloadAction<TranscriptItem>) => {
      state.transcript.push(action.payload);
    },
    mergeEntities: (state, action: PayloadAction<Partial<BankingEntities>>) => {
      state.entities = { ...state.entities, ...action.payload };
    },
    setActionChips: (state, action: PayloadAction<string[]>) => {
      state.actionChips = action.payload;
    },
    setComplianceAlert: (state, action: PayloadAction<ComplianceAlert | null>) => {
      state.complianceAlert = action.payload;
    },
    setSopResult: (state, action: PayloadAction<SopResult | null>) => {
      state.sopResult = action.payload;
    },
    setSummary: (state, action: PayloadAction<SessionState["bilingualSummary"]>) => {
      state.bilingualSummary = action.payload;
    },
    setDetectedLanguage: (state, action: PayloadAction<{ language: string; code: string }>) => {
      state.language = action.payload.language;
      state.languageCode = action.payload.code;
    },
    setEscalationAlert: (state, action: PayloadAction<string | null>) => {
      state.escalationAlert = action.payload;
    },

    // ── Form Interview Reducers ─────────────────────────────────────────
    startFormInterview: (
      state,
      action: PayloadAction<{
        formDefinition: FormDefinition;
        formState: { formType: string; totalFields: number; filledCount: number; progress: number; filledFields: Record<string, string> };
        currentField: FormCurrentField;
        questionText: string;
        questionTranslated: string;
      }>
    ) => {
      const { formDefinition, formState, currentField, questionText, questionTranslated } = action.payload;
      state.formInterview = {
        active: true,
        formType: formDefinition.formType,
        formDefinition,
        currentField,
        currentQuestion: questionText,
        currentQuestionTranslated: questionTranslated,
        progress: formState.progress,
        filledFields: formState.filledFields,
        totalFields: formState.totalFields,
        filledCount: formState.filledCount,
        isComplete: false,
        pdfReady: false,
        pdfUrl: null,
        lastFilledKey: null,
        lastFilledValue: null,
      };
    },

    updateFormField: (
      state,
      action: PayloadAction<{
        filledFieldKey: string;
        filledFieldValue: string;
        formState: { filledCount: number; progress: number; filledFields: Record<string, string>; totalFields: number };
        currentField: FormCurrentField | null;
        questionText: string | null;
        questionTranslated: string | null;
      }>
    ) => {
      const { filledFieldKey, filledFieldValue, formState, currentField, questionText, questionTranslated } = action.payload;
      state.formInterview.filledFields = formState.filledFields;
      state.formInterview.filledCount = formState.filledCount;
      state.formInterview.progress = formState.progress;
      state.formInterview.totalFields = formState.totalFields;
      state.formInterview.currentField = currentField;
      state.formInterview.currentQuestion = questionText;
      state.formInterview.currentQuestionTranslated = questionTranslated;
      state.formInterview.lastFilledKey = filledFieldKey;
      state.formInterview.lastFilledValue = filledFieldValue;
    },

    setFormComplete: (
      state,
      action: PayloadAction<{
        filledFieldKey: string;
        filledFieldValue: string;
        formState: { filledCount: number; progress: number; filledFields: Record<string, string>; totalFields: number };
      }>
    ) => {
      const { filledFieldKey, filledFieldValue, formState } = action.payload;
      state.formInterview.filledFields = formState.filledFields;
      state.formInterview.filledCount = formState.filledCount;
      state.formInterview.progress = 100;
      state.formInterview.totalFields = formState.totalFields;
      state.formInterview.isComplete = true;
      state.formInterview.currentField = null;
      state.formInterview.currentQuestion = null;
      state.formInterview.currentQuestionTranslated = null;
      state.formInterview.lastFilledKey = filledFieldKey;
      state.formInterview.lastFilledValue = filledFieldValue;
    },

    setFormPdfReady: (state, action: PayloadAction<string>) => {
      state.formInterview.pdfReady = true;
      state.formInterview.pdfUrl = action.payload;
    },

    cancelFormInterview: (state) => {
      state.formInterview = initialFormInterview;
    },
  }
});

export const {
  addTranscript,
  mergeEntities,
  setActionChips,
  setComplianceAlert,
  setConnectionStatus,
  setDetectedLanguage,
  setEscalationAlert,
  setListenMode,
  setMuted,
  setRecording,
  resetSession,
  setSopResult,
  setSummary,
  startFormInterview,
  updateFormField,
  setFormComplete,
  setFormPdfReady,
  cancelFormInterview,
} = sessionSlice.actions;

export default sessionSlice.reducer;
