const legacyApiBase = import.meta.env.VITE_VOXASSIST_API_URL;
const legacyWsUrl = import.meta.env.VITE_VOXASSIST_WS_URL;

function normalizeBaseUrl(value: string | undefined, fallback: string) {
  return (value || fallback).replace(/\/+$/, "");
}

function wsBaseFromLegacy(value: string | undefined) {
  if (!value) return undefined;
  return value.replace(/\/ws\/session\/[^/?#]+.*$/, "").replace(/\/+$/, "");
}

export const API_BASE = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE || legacyApiBase,
  "http://localhost:8000",
);

export const WS_BASE = normalizeBaseUrl(
  import.meta.env.VITE_WS_BASE || wsBaseFromLegacy(legacyWsUrl),
  "ws://localhost:8000",
);

export function buildSessionWsUrl(sessionId: string, token?: string) {
  const url = new URL(`${WS_BASE}/ws/session/${encodeURIComponent(sessionId)}`);
  if (token) url.searchParams.set("token", token);
  return url.toString();
}
