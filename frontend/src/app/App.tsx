import { useState } from "react";
import { AppShell } from "./layout/AppShell";
import { LoginPage } from "../features/auth/LoginPage";
import { AnalyticsDashboard } from "../features/analytics/AnalyticsDashboard";
import { LiveSession } from "../features/session/LiveSession";
import { SessionSummary } from "../features/session/SessionSummary";
import { SessionHistory } from "../features/session/SessionHistory";
import { CustomerKiosk } from "../features/kiosk/CustomerKiosk";
import { ComplianceDashboard } from "../features/session/ComplianceDashboard";

type View = "session" | "summary" | "analytics" | "history" | "compliance" | "team";

type AuthUser = {
  token: string;
  role: "staff" | "manager";
  name: string;
  branch: string;
  username?: string;
  deskId?: string | null;
};

export function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [activeView, setActiveView] = useState<View>("session");
  const [activeSessionId, setActiveSessionId] = useState(() => `session-${Date.now()}`);
  const [lastSessionId, setLastSessionId] = useState(activeSessionId);

  // ── Kiosk Route Bypass ──
  if (window.location.pathname === '/kiosk') {
    return <CustomerKiosk />;
  }

  // ── Auth gate ──
  if (!user) {
    return <LoginPage onLogin={setUser} />;
  }

  const handleViewChange = (view: View) => {
    if (view === "session" && activeView !== "session") {
      const nextSessionId = `session-${Date.now()}`;
      setActiveSessionId(nextSessionId);
      setLastSessionId(nextSessionId);
    }
    setActiveView(view);
  };

  return (
    <AppShell activeView={activeView} onViewChange={handleViewChange}>
      {activeView === "session" && (
        <LiveSession
          authToken={user.token}
          sessionId={activeSessionId}
          onEndSession={() => {
            setLastSessionId(activeSessionId);
            setActiveView("summary");
          }}
        />
      )}
      {activeView === "summary" && <SessionSummary authToken={user.token} sessionId={lastSessionId} />}
      {activeView === "analytics" && <AnalyticsDashboard authToken={user.token} />}
      {activeView === "history" && <SessionHistory authToken={user.token} />}
      {activeView === "compliance" && <ComplianceDashboard authToken={user.token} />}
    </AppShell>
  );
}
