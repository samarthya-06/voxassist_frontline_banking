import { AlertTriangle, Calendar, Download, Loader2, RefreshCw, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { useAppDispatch, useAppSelector } from "../../hooks";
import { setAnalytics, setAnalyticsLoading, setAnalyticsError } from "./analyticsSlice";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

function Bar({ label, value }: { label: string; value: number }) {
  const width = Math.min(Math.max(value, 0), 100);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="tabular-nums text-on-surface-variant">{value}%</span>
      </div>
      <div className="h-2 rounded bg-surface-container">
        <div
          className="h-full rounded bg-primary-container transition-all duration-500"
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

type TimeRange = "today" | "week" | "month";

export function AnalyticsDashboard() {
  const dispatch = useAppDispatch();
  const analytics = useAppSelector((state) => state.analytics);
  const [timeRange, setTimeRange] = useState<TimeRange>("today");
  const [refreshing, setRefreshing] = useState(false);

  const fetchAnalytics = useCallback(() => {
    dispatch(setAnalyticsLoading(true));
    setRefreshing(true);

    const rangeParam = timeRange === "today" ? "today" : timeRange === "week" ? "week" : timeRange === "month" ? "month" : "all";
    fetch(`${API_BASE}/analytics/branch?range=${rangeParam}`)
      .then((resp) => (resp.ok ? resp.json() : Promise.reject(resp)))
      .then((data) => {
        dispatch(setAnalytics(data));
      })
      .catch(() => {
        dispatch(setAnalyticsError("Failed to load analytics data."));
      })
      .finally(() => {
        setRefreshing(false);
      });
  }, [dispatch, timeRange]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  if (analytics.loading && !refreshing) {
    return (
      <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
        <div className="flex flex-col items-center justify-center gap-3 py-24">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-sm text-on-surface-variant">Loading analytics…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-surface p-6">
      <div className="mb-5 flex flex-col gap-3 border-b border-outline-variant pb-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-h1 font-semibold">Analytics Dashboard</h2>
          <p className="mt-1 text-sm text-on-surface-variant">Real-time branch demand, language mix, and escalation signals.</p>
        </div>
        <div className="flex gap-2">
          {/* Time Range Buttons */}
          {([
            ["today", "Today"],
            ["week", "This Week"],
            ["month", "This Month"],
          ] as [TimeRange, string][]).map(([key, label]) => (
            <Button
              key={key}
              variant={timeRange === key ? "primary" : "outline"}
              onClick={() => setTimeRange(key)}
            >
              <Calendar className="h-4 w-4" />
              {label}
            </Button>
          ))}
          <Button
            variant="outline"
            onClick={fetchAnalytics}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </Button>
          <Button>
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {analytics.error && (
        <div className="mb-4 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {analytics.error}
        </div>
      )}

      <div className="mb-4 grid gap-3 md:grid-cols-4">
        {[
          ["Sessions", String(analytics.sessions), "total"],
          ["Avg Handle Time", analytics.avgHandleTime, "avg"],
          ["Auto-Fill Accuracy", analytics.autoFillAccuracy, "rate"],
          ["Compliance Blocks", String(analytics.complianceBlocks), "flagged"]
        ].map(([label, value, delta]) => (
          <Card key={label}>
            <CardContent>
              <div className="text-caps uppercase text-outline">{label}</div>
              <div className="mt-2 flex items-end justify-between">
                <div className="text-2xl font-semibold tabular-nums">{value}</div>
                <Badge tone="blue">
                  <TrendingUp className="mr-1 h-3 w-3" />
                  {delta}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Frequently Requested Services</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {analytics.topServices.length > 0 ? (
              analytics.topServices.map((item) => (
                <Bar key={item.label} {...item} />
              ))
            ) : (
              <p className="text-sm text-on-surface-variant">No service data available yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Common Branch Languages</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {analytics.languages.length > 0 ? (
              analytics.languages.map((item) => (
                <Bar key={item.label} {...item} />
              ))
            ) : (
              <p className="text-sm text-on-surface-variant">No language data available yet.</p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Sentiment Escalation Alerts</CardTitle>
            <Badge tone="amber">Manager View</Badge>
          </CardHeader>
          <CardContent className="overflow-x-auto p-0">
            {analytics.alerts.length > 0 ? (
              <table className="w-full min-w-[640px] border-collapse text-sm">
                <thead className="bg-surface-container-low text-caps uppercase text-outline">
                  <tr>
                    <th className="border-b border-outline-variant px-4 py-3 text-left">Counter</th>
                    <th className="border-b border-outline-variant px-4 py-3 text-left">Signal</th>
                    <th className="border-b border-outline-variant px-4 py-3 text-left">Sentiment</th>
                    <th className="border-b border-outline-variant px-4 py-3 text-left">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.alerts.map((alert) => (
                    <tr key={alert.customer} className="hover:bg-surface-container-low">
                      <td className="border-b border-outline-variant px-4 py-3 font-medium">{alert.customer}</td>
                      <td className="border-b border-outline-variant px-4 py-3 text-on-surface-variant">{alert.reason}</td>
                      <td className="border-b border-outline-variant px-4 py-3">
                        <Badge tone="red">
                          <AlertTriangle className="mr-1 h-3 w-3" />
                          {alert.sentiment}
                        </Badge>
                      </td>
                      <td className="border-b border-outline-variant px-4 py-3">
                        <Button size="sm" variant="outline">Step In</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="flex flex-col items-center justify-center gap-2 px-4 py-8 text-on-surface-variant">
                <AlertTriangle className="h-8 w-8 opacity-30" />
                <p className="text-sm">No escalation alerts at this time.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
