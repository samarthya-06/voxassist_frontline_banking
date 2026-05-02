import {
  AlertTriangle,
  Ban,
  ChevronDown,
  ChevronRight,
  Mic,
  MicOff,
  PhoneOff,
  Quote,
  ReceiptText,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  Volume2,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAppDispatch, useAppSelector } from "../../hooks";
import { cn } from "../../lib/utils";
import { FormInterview } from "./FormInterview";
import { setListenMode, setMuted, resetSession } from "./sessionSlice";
import { useVoiceSession } from "./useVoiceSession";

const CUSTOMER_LANGUAGES = [
  { language: "Marathi", code: "mr-IN" },
  { language: "Hindi", code: "hi-IN" },
  { language: "English", code: "en-IN" },
  { language: "Gujarati", code: "gu-IN" },
  { language: "Kannada", code: "kn-IN" },
  { language: "Tamil", code: "ta-IN" },
  { language: "Telugu", code: "te-IN" },
  { language: "Bengali", code: "bn-IN" },
  { language: "Malayalam", code: "ml-IN" },
  { language: "Punjabi", code: "pa-IN" },
];

const LOW_CONFIDENCE_THRESHOLD = 0.75;

type FormSuggestion = {
  type: string;
  title: string;
  reason: string;
};

const FORM_INTENTS: Array<FormSuggestion & { keywords: string[] }> = [
  {
    type: "account_opening",
    title: "Account Opening",
    reason: "Customer appears to want a new account.",
    keywords: ["open account", "new account", "account opening", "savings account", "current account", "bank account"],
  },
  {
    type: "loan_application",
    title: "Loan Application",
    reason: "Customer appears to be asking about applying for a loan.",
    keywords: ["loan apply", "apply loan", "apply for loan", "loan application", "home loan", "personal loan", "vehicle loan", "borrow"],
  },
  {
    type: "kyc",
    title: "KYC Verification",
    reason: "Customer appears to need identity or KYC verification.",
    keywords: ["kyc", "verification", "verify identity", "identity verification", "address update", "pan update"],
  },
  {
    type: "fd_application",
    title: "Fixed Deposit",
    reason: "Customer appears to be asking about a fixed deposit.",
    keywords: ["fixed deposit", "fd", "term deposit", "deposit application"],
  },
  {
    type: "card_application",
    title: "Card Application",
    reason: "Customer appears to need a debit or credit card form.",
    keywords: ["card application", "apply card", "credit card", "debit card", "new card", "replacement card"],
  },
];

type LiveSessionProps = {
  authToken: string;
  onEndSession?: () => void;
};

export function LiveSession({ authToken, onEndSession }: LiveSessionProps) {
  const dispatch = useAppDispatch();
  const session = useAppSelector((state) => state.session);
  const {
    startRecording,
    stopRecording,
    replayLast,
    searchSop,
    setLanguage,
    waveformCanvasRef,
    startFormInterview,
    cancelFormInterview,
    generateFormPdf,
  } = useVoiceSession(authToken);
  const [sopExpanded, setSopExpanded] = useState(true);
  const [sopQuery, setSopQuery] = useState("");
  const [formSuggestion, setFormSuggestion] = useState<FormSuggestion | null>(null);
  const suggestedFormsRef = useRef<Set<string>>(new Set());

  const toggleRecording = () => {
    if (session.isRecording) stopRecording(session.listenMode);
    else startRecording(session.listenMode);
  };

  // ── Spacebar Push-to-Talk shortcut ──
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" && !e.repeat && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        if (!session.isRecording) startRecording(session.listenMode);
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        if (session.isRecording) stopRecording(session.listenMode);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [session.isRecording, session.listenMode, startRecording, stopRecording]);

  useEffect(() => {
    if (session.formInterview.active) {
      setFormSuggestion(null);
      return;
    }

    const latest = session.transcript[session.transcript.length - 1];
    if (!latest) return;

    const searchableText = [
      latest.originalText,
      latest.translatedText,
      ...session.actionChips,
    ].join(" ").toLowerCase();

    const match = FORM_INTENTS.find((intent) =>
      intent.keywords.some((keyword) => searchableText.includes(keyword))
    );
    if (!match || suggestedFormsRef.current.has(match.type)) return;

    suggestedFormsRef.current.add(match.type);
    setFormSuggestion({
      type: match.type,
      title: match.title,
      reason: match.reason,
    });
  }, [session.actionChips, session.formInterview.active, session.transcript]);

  const isComplianceBlock = session.complianceAlert?.severity === "block";
  const reRecord = (speaker: "customer" | "staff") => {
    dispatch(setListenMode(speaker));
    if (!session.isRecording) startRecording(speaker);
  };
  const actionIcon = (chip: string) => {
    const label = chip.toLowerCase();
    if (label.includes("block") || label.includes("card")) return <Ban className="h-4 w-4" />;
    if (label.includes("txn") || label.includes("transaction") || label.includes("receipt")) return <ReceiptText className="h-4 w-4" />;
    return <Sparkles className="h-4 w-4" />;
  };

  const toggleMute = () => {
    const newMuted = !session.isMuted;
    dispatch(setMuted(newMuted));
    if (newMuted && session.isRecording) {
      stopRecording(session.listenMode);
    }
  };

  const handleEndSession = () => {
    if (session.isRecording) stopRecording(session.listenMode);
    dispatch(resetSession());
    onEndSession?.();
  };

  return (
    <>
      {/* ── 3-column workspace ── */}
      <main className="flex min-h-0 flex-1 flex-col bg-surface-container-low p-4 pb-28">
        <div className="flex min-h-0 flex-1 gap-4">


          {/* ══════════════════════════════════════════════════════════════════
            LEFT: Live Transcript
        ══════════════════════════════════════════════════════════════════ */}
          <section className="flex flex-1 min-w-0 flex-col rounded-xl border border-outline-variant bg-surface shadow-md overflow-hidden">
            <header className="flex h-[52px] shrink-0 items-center justify-between border-b border-outline-variant bg-surface-bright px-4">
              <h2 className="text-[16px] font-semibold leading-5 text-on-surface">Live Transcript</h2>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <select
                    value={session.languageCode}
                    onChange={(event) => {
                      const option = CUSTOMER_LANGUAGES.find((item) => item.code === event.target.value);
                      if (option) setLanguage(option.language, option.code);
                    }}
                    className="h-8 appearance-none rounded border border-outline-variant bg-surface py-1 pl-2 pr-7 text-[12px] font-medium text-on-surface outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary"
                  >
                    {CUSTOMER_LANGUAGES.map((item) => (
                      <option key={item.code} value={item.code}>
                        {item.language}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2 top-2 h-4 w-4 text-outline" />
                </div>
                <Quote className="h-4 w-4 text-outline" />
              </div>
            </header>

            <div className="flex flex-1 flex-col gap-4 overflow-y-auto bg-surface-bright p-5">
              {session.transcript.map((item) => (
                <div key={item.id}>
                  {item.speaker === "customer" && (
                    <>
                      {/* Customer original text bubble */}
                      <div className="flex max-w-[85%] flex-col gap-1 self-start">
                        <span className="ml-1 text-[11px] font-bold uppercase tracking-[0.05em] text-outline">
                          Customer ({item.sourceLanguage})
                        </span>
                        <div className="rounded rounded-tl-none border border-outline-variant/50 bg-surface-variant px-3 py-2 text-[13px] leading-[18px] text-on-surface-variant">
                          {item.originalText}
                        </div>
                        {item.confidence < LOW_CONFIDENCE_THRESHOLD && (
                          <div className="mt-1 flex flex-wrap items-center gap-2 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-[12px] text-amber-900">
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                            <span className="font-medium">Low ASR confidence ({Math.round(item.confidence * 100)}%)</span>
                            <button
                              type="button"
                              onClick={() => reRecord("customer")}
                              className="ml-auto inline-flex items-center gap-1 rounded border border-amber-300 bg-white px-2 py-0.5 font-semibold text-amber-900 transition-colors hover:bg-amber-100"
                            >
                              <RefreshCw className="h-3 w-3" />
                              Re-record
                            </button>
                          </div>
                        )}
                      </div>
                      {/* Auto-translation bubble */}
                      <div className="mt-1 ml-4 flex max-w-[85%] flex-col gap-0.5 border-l-2 border-primary-container pl-3">
                        <span className="text-[11px] font-bold uppercase tracking-[0.05em] text-primary-container">
                          Auto-Translation
                        </span>
                        <div className="text-[13px] leading-[18px] italic text-on-surface">
                          "{item.translatedText}"
                        </div>
                      </div>
                    </>
                  )}
                  {item.speaker === "assistant" && (
                    <div className="mx-auto flex max-w-[90%] flex-col gap-1">
                      <span className="text-center text-[11px] font-bold uppercase tracking-[0.05em] text-outline">
                        AI Assistant
                      </span>
                      <div className="rounded border border-secondary-container bg-white px-3 py-2 text-[13px] leading-[18px] text-on-surface">
                        {item.originalText}
                      </div>
                    </div>
                  )}
                  {item.speaker === "staff" && (
                    <>
                      <div className="ml-auto flex max-w-[85%] flex-col items-end gap-1">
                        <span className="mr-1 text-[11px] font-bold uppercase tracking-[0.05em] text-outline">
                          Staff
                        </span>
                        <div className="rounded rounded-tr-none border border-primary/30 bg-primary-fixed px-3 py-2 text-[13px] leading-[18px] text-on-primary-fixed">
                          {item.originalText}
                        </div>
                        {item.confidence < LOW_CONFIDENCE_THRESHOLD && (
                          <div className="mt-1 flex flex-wrap items-center gap-2 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-[12px] text-amber-900">
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                            <span className="font-medium">Low ASR confidence ({Math.round(item.confidence * 100)}%)</span>
                            <button
                              type="button"
                              onClick={() => reRecord("staff")}
                              className="ml-auto inline-flex items-center gap-1 rounded border border-amber-300 bg-white px-2 py-0.5 font-semibold text-amber-900 transition-colors hover:bg-amber-100"
                            >
                              <RefreshCw className="h-3 w-3" />
                              Re-record
                            </button>
                          </div>
                        )}
                      </div>
                      {/* Auto-translation for staff (shown to customer) */}
                      <div className="mt-1 ml-auto mr-4 flex max-w-[85%] flex-col items-end gap-0.5 border-r-2 border-primary-container pr-3">
                        <span className="text-[11px] font-bold uppercase tracking-[0.05em] text-primary-container">
                          Auto-Translation
                        </span>
                        <div className="text-[13px] leading-[18px] italic text-on-surface">
                          "{item.translatedText}"
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}

              {/* Recording indicator */}
              {session.isRecording && (
                <div className="flex items-center gap-2 self-center rounded-full bg-red-50 px-4 py-1.5 text-[12px] font-medium text-red-700">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
                  Listening ({session.listenMode})…
                </div>
              )}
            </div>
          </section>

          {/* ══════════════════════════════════════════════════════════════════
            MIDDLE: Agentic Workspace
        ══════════════════════════════════════════════════════════════════ */}
          <section className="flex flex-1 min-w-0 flex-col rounded-xl border border-outline-variant bg-surface shadow-md overflow-hidden">
            <header className="flex h-[52px] shrink-0 items-center justify-between border-b border-outline-variant bg-surface-bright px-4">
              <h2 className="text-[16px] font-semibold leading-5 text-on-surface">Agentic Workspace</h2>
              <button
                onClick={replayLast}
                title="Replay last TTS"
                className="rounded p-1 text-outline hover:bg-surface-container hover:text-primary transition-colors"
              >
                <Volume2 className="h-4 w-4" />
              </button>
            </header>

            <div className="flex flex-1 flex-col gap-6 overflow-y-auto bg-surface-bright p-5">
              {/* Suggested Actions */}
              <div className="flex flex-col gap-2">
                <span className="text-[11px] font-bold uppercase tracking-[0.05em] text-on-surface-variant">
                  Suggested Actions
                </span>
                {session.actionChips.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {session.actionChips.map((chip, index) => (
                      <button
                        key={chip}
                        onClick={() => searchSop(chip)}
                        className={cn(
                          "flex min-h-10 flex-1 basis-[160px] items-center justify-center gap-2 rounded px-3 py-2 text-[14px] font-medium transition-colors",
                          index === 0
                            ? "bg-primary text-on-primary hover:bg-primary-container"
                            : "border border-primary bg-surface text-primary hover:bg-surface-container-low"
                        )}
                      >
                        {actionIcon(chip)}
                        <span className="truncate">{chip}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="rounded border border-dashed border-outline-variant bg-surface px-3 py-2 text-[13px] text-on-surface-variant">
                    Waiting for AI suggestions
                  </div>
                )}
              </div>

              {/* ═══ AI Form Interview ═══ */}
              <FormInterview
                onStartForm={startFormInterview}
                onCancelForm={cancelFormInterview}
                onGeneratePdf={generateFormPdf}
                isRecording={session.isRecording}
              />

            </div>
          </section>

          {/* ══════════════════════════════════════════════════════════════════
            RIGHT: SOPs & Guardrails
        ══════════════════════════════════════════════════════════════════ */}
          <section
            className={cn(
              "flex flex-1 min-w-0 flex-col rounded-xl border border-outline-variant bg-surface shadow-md overflow-hidden transition-all",
              isComplianceBlock && "ring-2 ring-error animate-pulse"
            )}
          >
            <header className="flex h-[52px] shrink-0 items-center justify-between border-b border-outline-variant bg-surface-bright px-4">
              <h2 className="text-[16px] font-semibold leading-5 text-on-surface">SOPs &amp; Guardrails</h2>
              <ShieldAlert className={cn("h-4 w-4", isComplianceBlock ? "text-error" : "text-outline")} />
            </header>

            <div className="flex flex-1 flex-col gap-4 overflow-y-auto bg-surface-bright p-5">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-outline" />
                <input
                  type="text"
                  value={sopQuery}
                  onChange={(e) => setSopQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && searchSop(sopQuery)}
                  placeholder="Search policies..."
                  className="w-full rounded border border-outline-variant bg-surface py-1.5 pl-9 pr-3 text-[13px] text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Compliance alert */}
              {session.complianceAlert && (
                <div className="flex items-start gap-3 rounded border border-error/20 bg-error-container p-3">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-error" />
                  <div className="flex flex-col gap-1">
                    <span className="text-[14px] font-bold text-on-surface">
                      Non-compliant statement detected
                    </span>
                    <span className="text-[13px] leading-[18px] text-on-surface opacity-90">
                      {session.complianceAlert.message}
                    </span>
                  </div>
                </div>
              )}

              {/* Escalation alert */}
              {session.escalationAlert && (
                <div className="flex items-start gap-3 rounded border border-amber-300 bg-amber-50 p-3">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <div className="flex flex-col gap-1">
                    <span className="text-[14px] font-bold text-amber-900">
                      Escalation Alert
                    </span>
                    <span className="text-[13px] leading-[18px] text-amber-800">
                      {session.escalationAlert}
                    </span>
                  </div>
                </div>
              )}

              {/* SOP Accordions */}
              <div className="overflow-hidden rounded border border-outline-variant">
                <button
                  onClick={() => setSopExpanded((v) => !v)}
                  className="flex w-full items-center justify-between border-b border-outline-variant bg-surface-container-low px-3 py-2 text-[14px] font-medium text-on-surface"
                >
                  Card Blocking Protocol
                  {sopExpanded ? (
                    <ChevronDown className="h-4 w-4 text-outline" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-outline" />
                  )}
                </button>
                {sopExpanded && (
                  <div className="flex flex-col gap-2 bg-surface p-3 text-[13px] leading-[18px] text-on-surface-variant">
                    <p>1. Authenticate customer using 2 out of 3 points (DOB, Address, Last TXN).</p>
                    <p>2. Confirm which card is lost (last 4 digits).</p>
                    <p>3. Initiate block via system and read confirmation statement.</p>
                  </div>
                )}
              </div>

              <div className="overflow-hidden rounded border border-outline-variant">
                <button className="flex w-full items-center justify-between bg-surface-container-low px-3 py-2 text-[14px] font-medium text-on-surface">
                  Premature FD Withdrawal
                  <ChevronRight className="h-4 w-4 text-outline" />
                </button>
              </div>

              {/* Live SOP result from RAG */}
              {session.sopResult && (
                <div className="rounded border border-secondary-container bg-surface-container-low p-3 text-[13px]">
                  <div className="flex items-start justify-between gap-3">
                    <div className="font-semibold text-on-surface">{session.sopResult.title}</div>
                    {typeof session.sopResult.confidence === "number" && (
                      <span className="shrink-0 rounded border border-outline-variant bg-white px-2 py-0.5 text-[11px] font-bold text-on-surface-variant">
                        {Math.round(session.sopResult.confidence * 100)}%
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-on-surface-variant">{session.sopResult.answer}</p>
                  {session.sopResult.requiresStaffVerification && (
                    <div className="mt-3 flex items-start gap-2 rounded border border-amber-300 bg-amber-50 px-2 py-1.5 text-[12px] font-medium text-amber-900">
                      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                      Verify against CBS or the latest approved circular before final customer advice.
                    </div>
                  )}
                  <div className="mt-3 text-[11px] font-bold uppercase tracking-[0.05em] text-outline">
                    {session.sopResult.source}
                  </div>
                  {(session.sopResult.effectiveFrom || session.sopResult.branchId) && (
                    <div className="mt-1 text-[11px] text-outline">
                      {session.sopResult.effectiveFrom && <>Effective {session.sopResult.effectiveFrom}</>}
                      {session.sopResult.branchId && <> - Branch {session.sopResult.branchId}</>}
                    </div>
                  )}
                  {session.sopResult.citations && session.sopResult.citations.length > 0 && (
                    <div className="mt-3 space-y-2 border-t border-outline-variant pt-3">
                      <div className="text-[11px] font-bold uppercase tracking-[0.05em] text-outline">
                        Citations
                      </div>
                      {session.sopResult.citations.slice(0, 3).map((citation) => (
                        <div key={citation.chunkId} className="rounded border border-outline-variant bg-white p-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="truncate font-semibold text-on-surface">{citation.title}</span>
                            <span className="shrink-0 text-[11px] font-bold text-outline">
                              {Math.round(citation.score * 100)}%
                            </span>
                          </div>
                          <div className="mt-1 text-[11px] text-outline">
                            {citation.source}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        </div>
      </main>

      {/* ══════════════════════════════════════════════════════════════════
          BOTTOM BAR: Push-to-Talk controls
      ══════════════════════════════════════════════════════════════════ */}
      <footer className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-center gap-8 border-t border-slate-200 bg-white px-10 py-3 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <button
          aria-label={session.isMuted ? "Unmute" : "Mute"}
          onClick={toggleMute}
          className={cn(
            "flex flex-col items-center justify-center rounded-lg px-6 py-2 text-[10px] font-bold uppercase tracking-wider transition-all active:scale-95",
            session.isMuted
              ? "bg-red-50 text-red-600 ring-1 ring-red-200"
              : "text-slate-600 hover:text-blue-900 hover:bg-slate-50"
          )}
        >
          {session.isMuted ? <MicOff className="mb-1 h-6 w-6" /> : <Mic className="mb-1 h-6 w-6" />}
          {session.isMuted ? "Unmute" : "Mute"}
        </button>

        <button
          aria-label="Push-to-Talk"
          onClick={toggleRecording}
          disabled={session.isMuted}
          className={cn(
            "relative flex flex-col items-center justify-center rounded-md px-12 py-3 text-xs font-bold uppercase tracking-wider text-white shadow-lg transition-transform active:scale-95",
            session.isMuted
              ? "cursor-not-allowed bg-slate-400 shadow-none"
              : session.isRecording
                ? "bg-red-700 shadow-red-700/20"
                : "bg-blue-900 shadow-blue-900/20"
          )}
        >
          {session.isRecording && (
            <span className="absolute inset-0 animate-ping rounded-md bg-red-500 opacity-20" />
          )}
          <canvas
            ref={waveformCanvasRef}
            width={180}
            height={52}
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute inset-x-3 top-1/2 h-11 -translate-y-1/2 opacity-0 transition-opacity",
              session.isRecording && "opacity-70"
            )}
          />
          <Mic className="relative z-10 mb-1 h-7 w-7" />
          <span className="relative z-10">{session.isMuted ? "Muted" : session.isRecording ? "Recording…" : "Push-to-Talk"}</span>
        </button>

        <button
          aria-label="End Session"
          onClick={handleEndSession}
          className="flex flex-col items-center justify-center rounded-lg px-6 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-600 transition-all hover:bg-red-50 hover:text-red-600 active:scale-95"
        >
          <PhoneOff className="mb-1 h-6 w-6" />
          End Session
        </button>
      </footer>

      {formSuggestion && !session.formInterview.active && (
        <div className="fixed bottom-24 right-6 z-[60] w-[min(360px,calc(100vw-32px))] rounded border border-primary/30 bg-white p-4 shadow-xl">
          <div className="flex items-start gap-3">
            <div className="rounded bg-primary-fixed p-2 text-primary">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[11px] font-bold uppercase tracking-[0.05em] text-primary">
                Suggested Form
              </div>
              <div className="mt-1 text-[14px] font-semibold text-on-surface">
                {formSuggestion.title}
              </div>
              <p className="mt-1 text-[13px] leading-[18px] text-on-surface-variant">
                {formSuggestion.reason}
              </p>
              <button
                type="button"
                onClick={() => {
                  startFormInterview(formSuggestion.type);
                  setFormSuggestion(null);
                }}
                className="mt-3 rounded bg-primary px-3 py-1.5 text-[13px] font-semibold text-on-primary transition-colors hover:bg-primary-container"
              >
                Start form
              </button>
            </div>
            <button
              type="button"
              aria-label="Dismiss form suggestion"
              onClick={() => setFormSuggestion(null)}
              className="rounded p-1 text-outline transition-colors hover:bg-surface-container-low hover:text-on-surface"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
