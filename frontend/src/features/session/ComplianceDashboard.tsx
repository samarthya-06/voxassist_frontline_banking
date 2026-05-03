import {
  Calendar,
  ChevronRight,
  Clock,
  Download,
  FileText,
  Filter,
  Globe,
  Loader2,
  MessageSquare,
  Search,
  ShieldAlert,
  User,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "../../shared/ui/badge";
import { Button } from "../../shared/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../shared/ui/card";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type SessionRecord = {
  session_id: string;
  timestamp: string;
  summary: {
    service: string;
    status: string;
    language: string;
    duration: string;
    sentiment: string;
    entities: {
      customerName?: string;
      pan?: string;
      phone?: string;
      accountType?: string;
      product?: string;
      amount?: string;
      cardLast4?: string;
    };
    english: string[];
    customerLanguage: string[];
    formsFilled: string[];
    complianceFlags: number;
  };
};

type DetailViewSession = SessionRecord | null;

function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso);
    return date.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return iso;
  }
}

type ComplianceDashboardProps = {
  authToken: string;
};

export function ComplianceDashboard({ authToken }: ComplianceDashboardProps) {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSession, setSelectedSession] = useState<DetailViewSession>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetch(`${API_BASE}/sessions`, {
      headers: { Authorization: `Bearer ${authToken}` },
    })
      .then((resp) => (resp.ok ? resp.json() : Promise.reject(resp)))
      .then((data: { sessions?: SessionRecord[] }) => {
        if (!cancelled) {
          setSessions(data.sessions ?? []);
        }
      })
      .catch(() => {
        console.warn("Sessions fetch failed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [authToken]);

  // ONLY show sessions with compliance flags
  const complianceSessions = sessions.filter((s) => (s.summary.complianceFlags ?? 0) > 0);

  const filteredSessions = complianceSessions.filter((session) => {
    const s = session.summary;
    const customer = s.entities?.customerName ?? "";
    return (
      !searchQuery ||
      customer.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.session_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.service.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  const totalFlags = complianceSessions.reduce((acc, s) => acc + (s.summary.complianceFlags || 0), 0);
  const flaggedSessionsCount = complianceSessions.length;

  if (selectedSession) {
    const s = selectedSession.summary;
    const entities = s.entities ?? {};

    return (
      <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
        <button
          onClick={() => setSelectedSession(null)}
          className="mb-4 flex items-center gap-1 text-sm font-medium text-blue-700 hover:text-blue-900 transition-colors"
        >
          ← Back to Compliance Dashboard
        </button>

        <div className="mb-5 flex flex-col gap-3 border-b border-outline-variant pb-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-h1 font-semibold text-red-700">Compliance Incident Detail</h2>
            <p className="mt-1 text-sm text-on-surface-variant">
              {selectedSession.session_id} · {formatTimestamp(selectedSession.timestamp)}
            </p>
          </div>
          <Button variant="outline">
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="space-y-4">
            <Card className="border-red-200 bg-red-50/50">
              <CardHeader>
                <CardTitle className="text-red-800 flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5" />
                  Compliance Review Required
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-red-900 mb-4">
                  This session triggered {s.complianceFlags} compliance flag(s). Please review the transcript summary below to ensure no regulatory guidelines were violated (e.g. guaranteeing returns, mis-selling, unauthorized fee waivers).
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Bilingual Summary</CardTitle>
                <Badge
                  tone={
                    s.status === "Completed"
                      ? "green"
                      : s.status === "Escalated"
                      ? "red"
                      : "amber"
                  }
                >
                  {s.status}
                </Badge>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div className="rounded border border-outline-variant p-4">
                  <div className="mb-3 text-caps uppercase text-outline">
                    English Record
                  </div>
                  <ul className="list-disc space-y-2 pl-4 text-sm text-on-surface-variant">
                    {(s.english ?? []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div className="rounded border border-outline-variant p-4">
                  <div className="mb-3 text-caps uppercase text-outline">
                    Customer Copy ({s.language})
                  </div>
                  <ul className="list-disc space-y-2 pl-4 text-sm text-on-surface-variant">
                    {(s.customerLanguage ?? []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Session Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-on-surface-variant">Customer</span>
                  <span className="font-medium">{entities.customerName || "Unknown"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-on-surface-variant">Service</span>
                  <span className="font-medium">{s.service}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-on-surface-variant">Compliance Flags</span>
                  <span className={`font-medium ${(s.complianceFlags ?? 0) > 0 ? "text-red-600" : "text-green-600"}`}>
                    {(s.complianceFlags ?? 0) > 0
                      ? `${s.complianceFlags} flag(s)`
                      : "Clean"}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
        <div className="flex flex-col items-center justify-center gap-3 py-24">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-sm text-on-surface-variant">Loading compliance records…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
      <div className="mb-5 flex flex-col gap-3 border-b border-outline-variant pb-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-h1 font-semibold">Compliance Monitoring</h2>
          <p className="mt-1 text-sm text-on-surface-variant">
            Review sessions that triggered AI compliance guardrails.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex h-9 flex-1 min-w-[200px] max-w-sm items-center gap-2 rounded border border-outline-variant bg-white px-3">
          <Search className="h-4 w-4 text-outline" />
          <input
            type="text"
            placeholder="Search flagged sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="min-w-0 flex-1 border-0 bg-transparent text-sm outline-none"
          />
        </div>
        <div className="text-sm text-on-surface-variant">
          {filteredSessions.length} incident{filteredSessions.length !== 1 ? "s" : ""}
        </div>
      </div>

      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <Card className="border-red-200">
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-caps uppercase text-red-600">Total Flagged Sessions</div>
                <div className="mt-1 text-2xl font-semibold tabular-nums text-red-700">{flaggedSessionsCount}</div>
              </div>
              <ShieldAlert className="h-8 w-8 text-red-500 opacity-60" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-red-200">
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-caps uppercase text-red-600">Total Flags Raised</div>
                <div className="mt-1 text-2xl font-semibold tabular-nums text-red-700">{totalFlags}</div>
              </div>
              <MessageSquare className="h-8 w-8 text-red-500 opacity-60" />
            </div>
          </CardContent>
        </Card>
      </div>

      {filteredSessions.length === 0 ? (
        <Card>
          <CardContent>
            <div className="flex flex-col items-center justify-center gap-2 py-12 text-on-surface-variant">
              <ShieldAlert className="h-10 w-10 text-green-500 opacity-80" />
              <p className="text-sm font-medium text-green-700">All Clear</p>
              <p className="text-sm">No compliance incidents found.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full min-w-[800px] border-collapse text-sm">
              <thead className="bg-surface-container-low text-caps uppercase text-outline">
                <tr>
                  <th className="border-b border-outline-variant px-4 py-3 text-left">Session</th>
                  <th className="border-b border-outline-variant px-4 py-3 text-left">Customer</th>
                  <th className="border-b border-outline-variant px-4 py-3 text-left">Service</th>
                  <th className="border-b border-outline-variant px-4 py-3 text-left">Flags</th>
                  <th className="border-b border-outline-variant px-4 py-3 text-left"></th>
                </tr>
              </thead>
              <tbody>
                {filteredSessions.map((session) => {
                  const s = session.summary;
                  return (
                    <tr
                      key={session.session_id}
                      className="cursor-pointer hover:bg-red-50/30 transition-colors"
                      onClick={() => setSelectedSession(session)}
                    >
                      <td className="border-b border-outline-variant px-4 py-3">
                        <div className="font-mono text-xs text-outline">{session.session_id}</div>
                        <div className="text-xs text-on-surface-variant">{formatTimestamp(session.timestamp)}</div>
                      </td>
                      <td className="border-b border-outline-variant px-4 py-3 font-medium">
                        {s.entities?.customerName || "Unknown"}
                      </td>
                      <td className="border-b border-outline-variant px-4 py-3 text-on-surface-variant">
                        {s.service}
                      </td>
                      <td className="border-b border-outline-variant px-4 py-3">
                         <span className="font-semibold text-red-600">{s.complianceFlags}</span>
                      </td>
                      <td className="border-b border-outline-variant px-4 py-3">
                        <ChevronRight className="h-4 w-4 text-outline" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
