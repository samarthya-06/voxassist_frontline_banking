import {
  Bell,
  Menu,
  Search,
  Settings,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "../hooks";
import { mergeEntities } from "../../features/session/sessionSlice";
import { cn } from "../../shared/lib/utils";

type View = "session" | "summary" | "analytics" | "history" | "compliance" | "team";

type AppShellProps = {
  activeView: View;
  onViewChange: (view: View) => void;
  children: React.ReactNode;
};

const nav = [
  { id: "session" as const, label: "Dashboard" },
  { id: "summary" as const, label: "Records" },
  { id: "compliance" as const, label: "Compliance" },
  { id: "analytics" as const, label: "Insights" },
];

type TopTab = { id: View; label: string };
const topTabs: TopTab[] = [
  { id: "session", label: "Dashboard" },
  { id: "analytics", label: "Analytics" },
  { id: "history", label: "History" },
];

function useCallTimer() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function AppShell({ activeView, onViewChange, children }: AppShellProps) {
  const dispatch = useAppDispatch();
  const timer = useCallTimer();
  const language = useAppSelector((state) => state.session.language);
  const customerName = useAppSelector((state) => state.session.entities.customerName);
  const escalationAlert = useAppSelector((state) => state.session.escalationAlert);
  const connectionStatus = useAppSelector((state) => state.session.connectionStatus);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [customerNameDraft, setCustomerNameDraft] = useState(customerName);

  useEffect(() => {
    setCustomerNameDraft(customerName);
  }, [customerName]);

  const commitCustomerName = () => {
    const name = customerNameDraft.trim();
    dispatch(mergeEntities({ customerName: name }));
  };

  // Close sidebar on route change
  const handleNavClick = (view: View) => {
    onViewChange(view);
    setSidebarOpen(false);
  };

  // Close sidebar on escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSidebarOpen(false);
    };
    if (sidebarOpen) {
      document.addEventListener("keydown", handleEsc);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [sidebarOpen]);

  useEffect(() => {
    document.body.dataset.sidebarOpen = sidebarOpen ? "true" : "false";
    return () => {
      delete document.body.dataset.sidebarOpen;
    };
  }, [sidebarOpen]);

  // ── Sidebar Content (shared between desktop drawer + mobile drawer) ──
  const sidebarContent = (
    <>
      <div className="mb-8 flex items-center gap-3 px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-high border border-outline-variant overflow-hidden">
          <img
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuCwWrnUbci8XNI9HEm1XmoJ5sZvxAqeGEPGIeVRTZNHsjO2fxUvsYlpiL-BYUwkyiqMMkO89zB6Pt3LyTo9se29-nV8pn_TOeKby4pvFeo8gT_Plfjirp6Kr-adzVYHdGFFhrMYqAtZn_3zeSFjk_yZthcRsTmkWOIrfOjYYihv2zh4s_QobhIvCkkMyBZh-UgIJL3UNGgO9zbjMGWxPEGnPQNa7btYbPL6A2IFsJUeDPNrK4FI-mwni5_MatBUR_t14FrCmvlBxcCC"
            alt="Manager Profile"
            className="w-full h-full object-cover"
          />
        </div>
        <div>
          <div className="text-sm font-bold text-blue-900 capitalize">Branch Portal</div>
          <div className="text-[10px] text-slate-500">Central District</div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {nav.map((item) => {
          const active = item.id === activeView;
          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className={cn(
                "relative flex h-11 items-center px-6 text-left text-xs font-semibold uppercase tracking-[0.04em] text-slate-600 transition-colors hover:bg-slate-100",
                active && "border-r-4 border-blue-900 bg-blue-50 text-blue-900"
              )}
            >
              {item.label}
              {/* Escalation badge on Insights */}
              {item.id === "analytics" && escalationAlert && (
                <span className="absolute right-3 top-2 flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background text-on-surface">
      {/* ── Sidebar Drawer (slide-over, triggered by hamburger) ── */}
      {sidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
          {/* Drawer */}
          <aside
            className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-slate-50 py-4 shadow-xl animate-slide-in-left"
          >
            {/* Close button */}
            <div className="mb-2 flex justify-end px-4">
              <button
                onClick={() => setSidebarOpen(false)}
                className="rounded p-1.5 text-slate-500 hover:bg-slate-100 transition-colors"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            {sidebarContent}
          </aside>
        </>
      )}

      {/* ── Main Content Area (full width, no permanent sidebar) ── */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* ── Top Navigation ── */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 gap-4">
          <div className="flex items-center gap-4 md:gap-6">
            {/* Hamburger Menu Button — always visible */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded p-1.5 text-slate-600 hover:bg-slate-100 transition-colors"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>

            <span className="text-lg font-black text-blue-900">VoxAssist Frontline</span>
            <nav className="hidden items-center gap-6 md:flex">
              {topTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => onViewChange(tab.id)}
                  className={cn(
                    "flex h-14 items-center text-sm transition-colors hover:bg-slate-50",
                    activeView === tab.id
                      ? "border-b-2 border-blue-900 font-semibold text-blue-900"
                      : "text-slate-500"
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Center: Account search + language + timer */}
          <div className="hidden md:flex items-center gap-3 rounded border border-outline-variant bg-surface px-3 py-1.5">
            {activeView === "session" && (
              <>
                <div className="flex items-center gap-2">
                  <UserRound className="h-4 w-4 text-outline" />
                  <input
                    type="text"
                    value={customerNameDraft}
                    onChange={(event) => setCustomerNameDraft(event.target.value)}
                    onBlur={commitCustomerName}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") event.currentTarget.blur();
                    }}
                    placeholder="Customer name"
                    className="w-40 border-none bg-transparent p-0 text-sm font-medium text-on-surface placeholder:text-outline focus:outline-none focus:ring-0"
                  />
                </div>
                <div className="h-4 w-px bg-outline-variant" />
              </>
            )}
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-outline" />
              <input
                type="text"
                defaultValue="1234-****"
                placeholder="Acct #"
                className="w-24 border-none bg-transparent p-0 text-sm font-mono text-on-surface focus:outline-none focus:ring-0"
              />
            </div>
            <div className="h-4 w-px bg-outline-variant" />
            <div className="flex items-center gap-1.5 rounded bg-primary-fixed px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-on-primary-fixed">
              <span className={cn(
                "h-1.5 w-1.5 rounded-full",
                connectionStatus === "connected" ? "bg-green-500 animate-pulse" : "bg-primary animate-pulse"
              )} />
              {language} Auto
            </div>
            <div className="h-4 w-px bg-outline-variant" />
            <div className="font-mono text-sm font-semibold text-on-surface tabular-nums">
              {timer}
            </div>
          </div>

          {/* Right: Action icons + avatar */}
          <div className="flex items-center gap-2">
            <button
              aria-label="Notifications"
              className={cn(
                "relative rounded p-1.5 transition-colors hover:bg-slate-50",
                escalationAlert ? "text-red-500" : "text-slate-500"
              )}
            >
              <Bell className="h-5 w-5" />
              {escalationAlert && (
                <span className="absolute right-1 top-1 flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
                </span>
              )}
            </button>
            <button
              aria-label="Settings"
              className="rounded p-1.5 text-slate-500 transition-colors hover:bg-slate-50"
            >
              <Settings className="h-5 w-5" />
            </button>
            <div className="ml-1 h-8 w-8 overflow-hidden rounded-full border border-outline-variant">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBrIUljdupBDsqdKdTKszRzHp5kq5-58hHoOQSo59-SAO5EzFrloW_HO6qEmiWyQE9CkLUrE8H7ULWcRzzyneNp77lywGVO_b5S3MpZwwz5lzZQ492njkuRC4keo-38yhwKVIFgE5Vt6JVE5IBiaOybR9PORetOjFTleXoFX9jDAW0rpVO_lU4lsWmRtyyw39K7-gw2ddOLlCiO79gkJadagXC8VcJmmDyV3G_E9i-ahHxEO930LViIJZRWIhQo8uolp_R1kawhMFdH"
                alt="Staff Avatar"
                className="h-full w-full object-cover"
              />
            </div>
          </div>
        </header>

        {/* ── Mobile Tab Bar ── */}
        <nav className="flex items-center border-b border-slate-200 bg-white md:hidden">
          {topTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onViewChange(tab.id)}
              className={cn(
                "flex-1 py-3 text-center text-xs font-medium uppercase tracking-wider transition-colors",
                activeView === tab.id
                  ? "border-b-2 border-blue-900 font-semibold text-blue-900"
                  : "text-slate-500"
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {children}
      </div>
    </div>
  );
}
