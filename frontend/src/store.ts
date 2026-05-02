import { configureStore } from "@reduxjs/toolkit";
import sessionReducer from "./features/session/sessionSlice";
import analyticsReducer from "./features/analytics/analyticsSlice";

export const store = configureStore({
  reducer: {
    session: sessionReducer,
    analytics: analyticsReducer
  }
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
