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
  User,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "../../shared/ui/badge";
import { Button } from "../../shared/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../shared/ui/card";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

// Types matching backend response
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
      customerName: string;
      pan: string;
      phone: string;
      accountType: string;
      product: string;
      amount: string;
      cardLast4: string;
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

export function SessionHistory() {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterService, setFilterService] = useState("all");
  const [selectedSession, setSelectedSession] = useState<DetailViewSession>(null);

  // Fetch sessions from backend
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetch(`${API_BASE}/sessions`)
      .then((resp) => (resp.ok ? resp.json() : Promise.reject(resp)))
      .then((data: { sessions?: SessionRecord[] }) => {
        if (!cancelled) {
          setSessions(data.sessions ?? []);
        }
      })
      .catch(() => {
        console.warn("Sessions fetch failed — no history loaded.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredSessions = sessions.filter((session) => {
    const s = session.summary;
    const customer = s.entities?.customerName ?? "";
    const matchesSearch =
      !searchQuery ||
      customer.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.session_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.service.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter =
      filterService === "all" || s.service.includes(filterService);
    return matchesSearch && matchesFilter;
  });

  const uniqueServices = [...new Set(sessions.map((s) => s.summary.service).filter(Boolean))];

  // Compute summary stats
  const totalSessions = sessions.length;
  const totalDurationSecs = sessions.reduce((acc, s) => {
    const parts = (s.summary.duration ?? "").split(":");
    if (parts.length === 2) {
      try {
        return acc + parseInt(parts[0]) * 60 + parseInt(parts[1]);
      } catch { /* ignore */ }
    }
    return acc;
  }, 0);
  const avgDurationSecs = totalSessions > 0 ? Math.round(totalDurationSecs / totalSessions) : 0;
  const avgDuration = `${String(Math.floor(avgDurationSecs / 60)).padStart(2, "0")}:${String(avgDurationSecs % 60).padStart(2, "0")}`;
  const formsFilled = sessions.filter((s) => (s.summary.formsFilled?.length ?? 0) > 0).length;
  const escalations = sessions.filter((s) => s.summary.status === "Escalated").length;

  // ── Detail View ──
  if (selectedSession) {
    const s = selectedSession.summary;
    const entities = s.entities ?? {};

    return (
      <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
        {/* Back button */}
        <button
          onClick={() => setSelectedSession(null)}
          className="mb-4 flex items-center gap-1 text-sm font-medium text-blue-700 hover:text-blue-900 transition-colors"
        >
          ← Back to History
        </button>

        <div className="mb-5 flex flex-col gap-3 border-b border-outline-variant pb-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-h1 font-semibold">Session Detail</h2>
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
          {/* Transcript Summary */}
          <div className="space-y-4">
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

            {(s.formsFilled ?? []).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Forms Completed</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {s.formsFilled.map((form) => (
                      <div
                        key={form}
                        className="flex items-center gap-2 rounded border border-green-200 bg-green-50 px-3 py-2 text-sm font-medium text-green-800"
                      >
                        <FileText className="h-4 w-4" />
                        {form}
                        <Badge tone="green">✓ Filled</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar: Session metadata */}
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
                  <span className="text-on-surface-variant">Language</span>
                  <Badge tone="blue">{s.language}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-on-surface-variant">Service</span>
                  <span className="font-medium">{s.service}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-on-surface-variant">Duration</span>
                  <span className="font-mono font-medium">{s.duration}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-on-surface-variant">Sentiment</span>
                  <Badge
                    tone={
                      s.sentiment === "positive"
                        ? "green"
                        : s.sentiment === "negative"
                        ? "red"
                        : "amber"
                    }
                  >
                    {s.sentiment}
                  </Badge>
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

            {Object.entries(entities).some(([, value]) => value) && (
              <Card>
                <CardHeader>
                  <CardTitle>Extracted Entities</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    {Object.entries(entities).map(([key, value]) =>
                      value ? (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-caps uppercase text-outline">
                            {key.replace(/([A-Z])/g, " $1")}
                          </span>
                          <span className="font-mono font-medium">{value}</span>
                        </div>
                      ) : null
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    );
  }

  // ── Loading State ──
  if (loading) {
    return (
      <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
        <div className="flex flex-col items-center justify-center gap-3 py-24">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-sm text-on-surface-variant">Loading session history…</p>
        </div>
      </main>
    );
  }

  // ── Main List View ──
  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
      <div className="mb-5 flex flex-col gap-3 border-b border-outline-variant pb-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-h1 font-semibold">Session History</h2>
          <p className="mt-1 text-sm text-on-surface-variant">
            Browse past customer interactions, transcripts, and form records.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Calendar className="h-4 w-4" />
            This Week
          </Button>
          <Button variant="outline">
            <Download className="h-4 w-4" />
            Export All
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex h-9 flex-1 min-w-[200px] max-w-sm items-center gap-2 rounded border border-outline-variant bg-white px-3">
          <Search className="h-4 w-4 text-outline" />
          <input
            type="text"
            placeholder="Search by customer, session ID, or service..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="min-w-0 flex-1 border-0 bg-transparent text-sm outline-none"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-outline" />
          <select
            value={filterService}
            onChange={(e) => setFilterService(e.target.value)}
            className="h-9 rounded border border-outline-variant bg-white px-3 text-sm outline-none"
          >
            <option value="all">All Services</option>
            {uniqueServices.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="text-sm text-on-surface-variant">
          {filteredSessions.length} session{filteredSessions.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Stats Row */}
      <div className="mb-4 grid gap-3 md:grid-cols-4">
        {[
          { label: "Total Sessions", value: totalSessions, icon: MessageSquare },
          { label: "Avg Duration", value: avgDuration, icon: Clock },
          { label: "Forms Filled", value: formsFilled, icon: FileText },
          { label: "Escalations", value: escalations, icon: User },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-caps uppercase text-outline">{stat.label}</div>
                  <div className="mt-1 text-2xl font-semibold tabular-nums">{stat.value}</div>
                </div>
                <stat.icon className="h-8 w-8 text-primary-container opacity-60" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Session List */}
      {filteredSessions.length === 0 ? (
        <Card>
          <CardContent>
            <div className="flex flex-col items-center justify-center gap-2 py-12 text-on-surface-variant">
              <MessageSquare className="h-10 w-10 opacity-30" />
              <p className="text-sm">No sessions found matching your search.</p>
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
                  <th className="border-b border-outline-variant px-4 py-3 text-left">Language</th>
                  <th className="border-b border-outline-variant px-4 py-3 text-left">Duration</th>
                  <th className="border-b border-outline-variant px-4 py-3 text-left">Status</th>
                  <th className="border-b border-outline-variant px-4 py-3 text-left"></th>
                </tr>
              </thead>
              <tbody>
                {filteredSessions.map((session) => {
                  const s = session.summary;
                  return (
                    <tr
                      key={session.session_id}
                      className="cursor-pointer hover:bg-surface-container-low transition-colors"
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
                        <div className="flex items-center gap-2">
                          {s.service}
                          {(s.formsFilled?.length ?? 0) > 0 && (
                            <FileText className="h-3 w-3 text-green-600" />
                          )}
                        </div>
                      </td>
                      <td className="border-b border-outline-variant px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <Globe className="h-3 w-3 text-outline" />
                          {s.language}
                        </div>
                      </td>
                      <td className="border-b border-outline-variant px-4 py-3 font-mono text-on-surface-variant">
                        {s.duration}
                      </td>
                      <td className="border-b border-outline-variant px-4 py-3">
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
