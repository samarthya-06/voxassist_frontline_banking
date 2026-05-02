import { createSlice, PayloadAction } from "@reduxjs/toolkit";

type BarDatum = {
  label: string;
  value: number;
};

type AlertDatum = {
  customer: string;
  reason: string;
  sentiment: string;
};

export type AnalyticsState = {
  topServices: BarDatum[];
  languages: BarDatum[];
  alerts: AlertDatum[];
  sessions: number;
  avgHandleTime: string;
  autoFillAccuracy: string;
  complianceBlocks: number;
  loading: boolean;
  error: string | null;
};

const initialState: AnalyticsState = {
  topServices: [],
  languages: [],
  alerts: [],
  sessions: 0,
  avgHandleTime: "00:00",
  autoFillAccuracy: "0%",
  complianceBlocks: 0,
  loading: true,
  error: null,
};

const analyticsSlice = createSlice({
  name: "analytics",
  initialState,
  reducers: {
    setAnalytics: (state, action: PayloadAction<Partial<AnalyticsState>>) => ({
      ...state,
      ...action.payload,
      topServices: action.payload.topServices ?? state.topServices,
      languages: action.payload.languages ?? state.languages,
      alerts: action.payload.alerts ?? state.alerts,
      loading: false,
      error: null,
    }),
    setAnalyticsLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setAnalyticsError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.loading = false;
    },
  }
});

export const { setAnalytics, setAnalyticsLoading, setAnalyticsError } = analyticsSlice.actions;

export default analyticsSlice.reducer;
