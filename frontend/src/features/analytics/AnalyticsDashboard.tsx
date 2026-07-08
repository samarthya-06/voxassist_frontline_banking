import { AlertTriangle, Download, Filter, Loader2, RefreshCw, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "../../shared/ui/badge";
import { Button } from "../../shared/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../shared/ui/card";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { API_BASE } from "../../config/env";
import { setAnalytics, setAnalyticsLoading, setAnalyticsError } from "./analyticsSlice";

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

type TimeRange = "today" | "week" | "month" | "year" | "custom_day" | "custom_month" | "custom_year";

const ANALYTICS_FILTER_OPTIONS: Array<{ value: TimeRange; label: string }> = [
  { value: "today", label: "Today" },
  { value: "week", label: "This Week" },
  { value: "month", label: "This Month" },
  { value: "year", label: "This Year" },
  { value: "custom_day", label: "Select Date" },
  { value: "custom_month", label: "Select Month" },
  { value: "custom_year", label: "Select Year" },
];

type AnalyticsDashboardProps = {
  authToken: string;
};

export function AnalyticsDashboard({ authToken }: AnalyticsDashboardProps) {
  const dispatch = useAppDispatch();
  const analytics = useAppSelector((state) => state.analytics);
  const [timeRange, setTimeRange] = useState<TimeRange>("today");
  const todayIso = new Date().toISOString().slice(0, 10);
  const [selectedDate, setSelectedDate] = useState(todayIso);
  const [selectedMonth, setSelectedMonth] = useState(todayIso.slice(0, 7));
  const [selectedYear, setSelectedYear] = useState(todayIso.slice(0, 4));
  const [refreshing, setRefreshing] = useState(false);

  const buildParams = useCallback(() => {
    const params = new URLSearchParams();
    if (timeRange === "custom_day") {
      params.set("date", selectedDate);
    } else if (timeRange === "custom_month") {
      params.set("month", selectedMonth);
    } else if (timeRange === "custom_year") {
      params.set("year", selectedYear);
    } else {
      params.set("range", timeRange);
    }
    return params;
  }, [selectedDate, selectedMonth, selectedYear, timeRange]);

  const fetchAnalytics = useCallback(() => {
    dispatch(setAnalyticsLoading(true));
    setRefreshing(true);

    fetch(`${API_BASE}/analytics/branch?${buildParams().toString()}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    })
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
  }, [authToken, buildParams, dispatch]);

  const exportAnalytics = useCallback(async (format: "csv" | "pdf") => {
    const params = buildParams();
    params.set("format", format);
    const resp = await fetch(`${API_BASE}/analytics/branch/export?${params.toString()}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    if (!resp.ok) {
      dispatch(setAnalyticsError("Export failed. Please refresh and try again."));
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `voxassist-analytics.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }, [authToken, buildParams, dispatch]);

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
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex h-9 items-center gap-2 rounded border border-outline-variant bg-white px-3 text-sm font-medium text-on-surface">
            <Filter className="h-4 w-4 text-outline" />
            <span className="text-outline">Filter</span>
            <select
              value={timeRange}
              onChange={(event) => setTimeRange(event.target.value as TimeRange)}
              className="min-w-[8rem] border-0 bg-transparent font-semibold outline-none"
              aria-label="Analytics time filter"
            >
              {ANALYTICS_FILTER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {timeRange === "custom_day" && (
            <input
              type="date"
              value={selectedDate}
              onChange={(event) => setSelectedDate(event.target.value)}
              className="h-9 rounded border border-outline-variant bg-white px-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              aria-label="Filter analytics by day"
            />
          )}
          {timeRange === "custom_month" && (
            <input
              type="month"
              value={selectedMonth}
              onChange={(event) => setSelectedMonth(event.target.value)}
              className="h-9 rounded border border-outline-variant bg-white px-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              aria-label="Filter analytics by month"
            />
          )}
          {timeRange === "custom_year" && (
            <input
              type="number"
              value={selectedYear}
              onChange={(event) => setSelectedYear(event.target.value)}
              min="2020"
              max="2100"
              className="h-9 w-24 rounded border border-outline-variant bg-white px-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              aria-label="Filter analytics by year"
            />
          )}
          <Button
            variant="outline"
            onClick={fetchAnalytics}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </Button>
          <Button onClick={() => exportAnalytics("csv")} variant="outline">
            <Download className="h-4 w-4" />
            CSV
          </Button>
          <Button onClick={() => exportAnalytics("pdf")}>
            <Download className="h-4 w-4" />
            PDF
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
