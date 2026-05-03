import { Lock, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { cn } from "../../shared/lib/utils";

type AuthUser = {
  token: string;
  role: "staff" | "manager";
  name: string;
  branch: string;
  username?: string;
  deskId?: string | null;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type LoginPageProps = {
  onLogin: (user: AuthUser) => void;
};

export function LoginPage({ onLogin }: LoginPageProps) {
  const [activeTab, setActiveTab] = useState<"staff" | "manager">("staff");
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const username = employeeId.trim();

    try {
      const resp = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setError(data.detail || "Invalid credentials");
        setLoading(false);
        return;
      }

      const user = await resp.json();
      onLogin(user as AuthUser);
    } catch (err: any) {
      setError(err.message || "Network error: Unable to connect to the backend.");
    }
    setLoading(false);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-container-low text-on-surface antialiased">
      <main className="w-full max-w-[420px] px-4">
        {/* Login Card */}
        <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-6 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)]">

          {/* Header & Logo */}
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded bg-primary">
              <svg className="h-6 w-6 text-on-primary" viewBox="0 0 24 24" fill="currentColor">
                <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z" />
              </svg>
            </div>
            <h1 className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-on-surface">
              Institutional Access
            </h1>
            <p className="text-[13px] leading-[18px] text-on-surface-variant">
              Authentication Gateway
            </p>
          </div>

          {/* Role Selection Tabs */}
          <div className="mb-6 flex rounded border border-outline-variant bg-surface-container p-[2px]">
            <button
              type="button"
              onClick={() => setActiveTab("staff")}
              className={cn(
                "flex flex-1 items-center justify-center rounded px-3 py-2 text-[13px] leading-[18px] transition-all",
                activeTab === "staff"
                  ? "border border-outline-variant bg-surface-container-lowest text-on-surface shadow-sm font-medium"
                  : "text-on-surface-variant hover:text-on-surface"
              )}
            >
              Frontline Staff
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("manager")}
              className={cn(
                "flex flex-1 items-center justify-center rounded px-3 py-2 text-[13px] leading-[18px] transition-all",
                activeTab === "manager"
                  ? "border border-outline-variant bg-surface-container-lowest text-on-surface shadow-sm font-medium"
                  : "text-on-surface-variant hover:text-on-surface"
              )}
            >
              Branch Manager
            </button>
          </div>

          {/* Authentication Form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            {/* Employee ID Input */}
            <div>
              <label
                htmlFor="employee-id"
                className="mb-1 block text-[13px] leading-[18px] text-on-surface"
              >
                Employee ID
              </label>
              <input
                id="employee-id"
                type="text"
                autoComplete="username"
                autoFocus
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                placeholder={activeTab === "staff" ? "staff1-staff5 or 104851-104855" : "manager1 or 200100"}
                className="h-8 w-full rounded border border-outline-variant bg-surface-container-lowest px-2 text-[13px] leading-[18px] text-on-surface outline-none placeholder:text-outline-variant focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Password Input */}
            <div>
              <div className="mb-1 flex items-center justify-between">
                <label
                  htmlFor="login-password"
                  className="block text-[13px] leading-[18px] text-on-surface"
                >
                  Password
                </label>
                <a
                  href="#"
                  className="text-[13px] leading-[18px] text-primary hover:underline focus:outline-none"
                >
                  Forgot?
                </a>
              </div>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="h-8 w-full rounded border border-outline-variant bg-surface-container-lowest px-2 text-[13px] leading-[18px] text-on-surface outline-none placeholder:text-outline-variant focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="rounded border border-error/20 bg-error-container px-3 py-2 text-[13px] text-on-error-container">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <div className="mt-6 pt-2">
              <button
                type="submit"
                disabled={loading || !employeeId || !password}
                className="flex h-8 w-full items-center justify-center rounded bg-primary-container text-[14px] font-medium text-on-primary transition-colors hover:bg-primary focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50"
              >
                <Lock className="mr-2 h-[18px] w-[18px]" />
                {loading ? "Authenticating…" : "Secure Login"}
              </button>
            </div>
          </form>

          {/* Footer Context */}
          <div className="mt-6 text-center">
            <p className="flex items-center justify-center gap-1 text-[13px] leading-[18px] text-outline">
              <ShieldCheck className="h-[14px] w-[14px]" />
              End-to-end encrypted session
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
