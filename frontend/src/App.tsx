import { useState } from "react";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./features/auth/LoginPage";
import { AnalyticsDashboard } from "./features/analytics/AnalyticsDashboard";
import { LiveSession } from "./features/session/LiveSession";
import { SessionSummary } from "./features/session/SessionSummary";
import { SessionHistory } from "./features/session/SessionHistory";
import { CustomerKiosk } from "./features/kiosk/CustomerKiosk";
import { ComplianceDashboard } from "./features/session/ComplianceDashboard";

type View = "session" | "summary" | "analytics" | "history" | "compliance" | "team";

type AuthUser = {
  token: string;
  role: "staff" | "manager";
  name: string;
  branch: string;
};

export function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [activeView, setActiveView] = useState<View>("session");

  // ── Kiosk Route Bypass ──
  if (window.location.pathname === '/kiosk') {
    return <CustomerKiosk />;
  }

  // ── Auth gate ──
  if (!user) {
    return <LoginPage onLogin={setUser} />;
  }

  const handleViewChange = (view: View) => {
    setActiveView(view);
  };

  return (
    <AppShell activeView={activeView} onViewChange={handleViewChange}>
      {activeView === "session" && <LiveSession authToken={user.token} onEndSession={() => setActiveView("summary")} />}
      {activeView === "summary" && <SessionSummary />}
      {activeView === "analytics" && <AnalyticsDashboard />}
      {activeView === "history" && <SessionHistory />}
      {activeView === "compliance" && <ComplianceDashboard />}
    </AppShell>
  );
}

