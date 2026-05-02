import { Download, Mail, MessageSquareText, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { useAppSelector } from "../../hooks";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type HistoryItem = {
  id: string;
  customer: string;
  language: string;
  service: string;
  status: string;
};

type CustomerHistoryDoc = {
  id?: string;
  session_id?: string;
  customer?: string;
  language?: string;
  service?: string;
  status?: string;
  summary?: {
    type?: string;
    service?: string;
    status?: string;
    language?: string;
    english?: string[];
    entities?: {
      customerName?: string;
    };
  };
};

export function SessionSummary() {
  const summary = useAppSelector((state) => state.session.bilingualSummary);
  const entities = useAppSelector((state) => state.session.entities);
  const language = useAppSelector((state) => state.session.language);
  const [downloading, setDownloading] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    fetch(`${API_BASE}/customer/history`)
      .then((resp) => (resp.ok ? resp.json() : Promise.reject(resp)))
      .then((data: { sessions?: CustomerHistoryDoc[] }) => {
        if (cancelled) return;

        const rows = (data.sessions ?? []).map((item, index) => ({
          id: item.session_id ?? item.id ?? `session-${index + 1}`,
          customer: item.summary?.entities?.customerName ?? item.customer ?? "Unknown customer",
          language: item.summary?.language ?? item.language ?? language,
          service: item.summary?.service ?? item.summary?.type ?? item.service ?? item.summary?.english?.[0] ?? "General banking",
          status: item.summary?.status ?? item.status ?? "Completed",
        }));
        setHistory(rows);
      })
      .catch(() => {
        console.warn("Customer history fetch failed — no history loaded.");
      });

    return () => {
      cancelled = true;
    };
  }, [language]);

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const resp = await fetch(`${API_BASE}/session/demo-session/receipt`, { method: "POST" });
      if (resp.ok) {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "session_receipt.pdf";
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {
      console.warn("PDF download failed — backend may not be running.");
    }
    setDownloading(false);
  };

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
      <div className="mb-5 flex flex-col gap-3 border-b border-outline-variant pb-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-h1 font-semibold">Session Records</h2>
          <p className="mt-1 text-sm text-on-surface-variant">Bilingual summaries, receipts, and previous branch visits.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Mail className="h-4 w-4" />
            Email
          </Button>
          <Button variant="outline">
            <MessageSquareText className="h-4 w-4" />
            SMS
          </Button>
          <Button onClick={downloadPdf} disabled={downloading}>
            <Download className="h-4 w-4" />
            {downloading ? "Generating…" : "PDF Receipt"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        {/* Current Interaction Summary */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Current Interaction Summary</CardTitle>
            <Badge tone="green">Ready for records</Badge>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="rounded border border-outline-variant p-4">
              <div className="mb-3 text-caps uppercase text-outline">English Record</div>
              <ul className="list-disc space-y-2 pl-4 text-sm text-on-surface-variant">
                {summary.english.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="rounded border border-outline-variant p-4">
              <div className="mb-3 text-caps uppercase text-outline">Customer Copy ({language})</div>
              <ul className="list-disc space-y-2 pl-4 text-sm text-on-surface-variant">
                {summary.customerLanguage.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Extracted Entities Summary */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Extracted Entities</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {Object.entries(entities).map(([key, value]) =>
                  value ? (
                    <div key={key} className="space-y-0.5">
                      <div className="text-caps uppercase text-outline">{key.replace(/([A-Z])/g, " $1")}</div>
                      <div className="font-medium text-on-surface">{value}</div>
                    </div>
                  ) : null
                )}
              </div>
            </CardContent>
          </Card>

          {/* Customer History Lookup */}
          <Card>
            <CardHeader>
              <CardTitle>Customer History Lookup</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-3 flex h-9 items-center gap-2 rounded border border-outline-variant bg-white px-2">
                <Search className="h-4 w-4 text-outline" />
                <input className="min-w-0 flex-1 border-0 bg-transparent text-sm outline-none" value="1234-****" readOnly />
              </div>
              <div className="space-y-2">
                {history.length > 0 ? history.map((item) => (
                  <article key={item.id} className="rounded border border-outline-variant p-3 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold">{item.customer}</div>
                      <Badge tone="slate">{item.language}</Badge>
                    </div>
                    <div className="mt-2 text-on-surface-variant">{item.service}</div>
                    <div className="mt-1 text-xs text-outline">{item.id} · {item.status}</div>
                  </article>
                )) : (
                  <div className="rounded border border-dashed border-outline-variant p-3 text-sm text-on-surface-variant">
                    No previous sessions found
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
