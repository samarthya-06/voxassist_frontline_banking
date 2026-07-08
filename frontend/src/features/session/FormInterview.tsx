import {
  CheckCircle,
  CreditCard,
  Download,
  FileText,
  HandCoins,
  Landmark,
  MessageSquare,
  Mic,
  PiggyBank,
  Sparkles,
  UserCheck,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAppSelector } from "../../app/hooks";
import { API_BASE } from "../../config/env";
import { cn } from "../../shared/lib/utils";

// ── Icon mapping for form types ─────────────────────────────────────────────
const FORM_ICONS: Record<string, React.ReactNode> = {
  UserCheck: <UserCheck className="h-6 w-6" />,
  Landmark: <Landmark className="h-6 w-6" />,
  PiggyBank: <PiggyBank className="h-6 w-6" />,
  HandCoins: <HandCoins className="h-6 w-6" />,
  CreditCard: <CreditCard className="h-6 w-6" />,
};

// ── Form type color mapping ─────────────────────────────────────────────────
const FORM_COLORS: Record<string, { bg: string; border: string; text: string; accent: string }> = {
  kyc: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", accent: "bg-blue-600" },
  account_opening: { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", accent: "bg-emerald-600" },
  fd_application: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", accent: "bg-amber-600" },
  loan_application: { bg: "bg-purple-50", border: "border-purple-200", text: "text-purple-700", accent: "bg-purple-600" },
  card_application: { bg: "bg-rose-50", border: "border-rose-200", text: "text-rose-700", accent: "bg-rose-600" },
};

const FORM_CARDS = [
  { type: "kyc", title: "KYC Verification", icon: "UserCheck", desc: "Identity verification" },
  { type: "account_opening", title: "Account Opening", icon: "Landmark", desc: "New bank account" },
  { type: "fd_application", title: "Fixed Deposit", icon: "PiggyBank", desc: "FD application" },
  { type: "loan_application", title: "Loan Application", icon: "HandCoins", desc: "Personal / Home / Vehicle" },
  { type: "card_application", title: "Card Application", icon: "CreditCard", desc: "Debit / Credit card" },
];

type Props = {
  onStartForm: (formType: string) => void;
  onCancelForm: () => void;
  onGeneratePdf: () => void;
  isRecording: boolean;
};

export function FormInterview({ onStartForm, onCancelForm, onGeneratePdf, isRecording }: Props) {
  const form = useAppSelector((s) => s.session.formInterview);
  const [justFilled, setJustFilled] = useState<string | null>(null);
  const fieldListRef = useRef<HTMLDivElement>(null);

  // Flash animation when a field gets filled
  useEffect(() => {
    if (form.lastFilledKey) {
      setJustFilled(form.lastFilledKey);
      const timer = setTimeout(() => setJustFilled(null), 1500);
      return () => clearTimeout(timer);
    }
  }, [form.lastFilledKey, form.lastFilledValue]);

  // Auto-scroll field list when new field is filled
  useEffect(() => {
    if (fieldListRef.current) {
      fieldListRef.current.scrollTop = fieldListRef.current.scrollHeight;
    }
  }, [form.filledCount]);

  const colors = form.formType ? FORM_COLORS[form.formType] || FORM_COLORS.kyc : FORM_COLORS.kyc;

  // ── No active form: Show form selector ────────────────────────────────
  if (!form.active) {
    return (
      <div className="flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" />
          <span className="text-[11px] font-bold uppercase tracking-[0.05em] text-on-surface-variant">
            AI Form Filling
          </span>
        </div>

        <p className="text-[12px] text-on-surface-variant leading-[16px]">
          Select a form below. The AI will ask the customer questions by voice and auto-fill the form in English.
        </p>

        {/* Form type cards */}
        <div className="grid grid-cols-2 gap-2">
          {FORM_CARDS.map((card) => {
            const c = FORM_COLORS[card.type] || FORM_COLORS.kyc;
            return (
              <button
                key={card.type}
                onClick={() => onStartForm(card.type)}
                className={cn(
                  "group flex flex-col items-center gap-1.5 rounded-lg border p-3 transition-all",
                  "hover:shadow-md hover:scale-[1.02] active:scale-[0.98]",
                  c.bg, c.border
                )}
              >
                <div className={cn("rounded-full p-2", c.bg, c.text)}>
                  {FORM_ICONS[card.icon]}
                </div>
                <span className={cn("text-[12px] font-semibold leading-tight text-center", c.text)}>
                  {card.title}
                </span>
                <span className="text-[10px] text-gray-500">{card.desc}</span>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // ── Active form interview ─────────────────────────────────────────────
  const definition = form.formDefinition;
  if (!definition) return null;

  return (
    <div className="flex flex-col gap-3">
      {/* Header with title and cancel */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={cn("rounded-full p-1.5", colors.bg, colors.text)}>
            {FORM_ICONS[definition.icon] || <FileText className="h-4 w-4" />}
          </div>
          <div>
            <h3 className="text-[13px] font-semibold text-on-surface leading-tight">{definition.title}</h3>
            <span className="text-[10px] text-on-surface-variant">AI Voice Auto-Fill</span>
          </div>
        </div>
        <button
          onClick={onCancelForm}
          className="rounded p-1 text-outline hover:bg-red-50 hover:text-red-600 transition-colors"
          title="Cancel form"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between text-[10px]">
          <span className="font-semibold text-on-surface-variant">
            {form.isComplete ? "Complete!" : `Field ${form.filledCount + 1} of ${form.totalFields}`}
          </span>
          <span className={cn("font-bold", colors.text)}>{Math.round(form.progress)}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-700 ease-out",
              form.isComplete ? "bg-green-500" : colors.accent
            )}
            style={{ width: `${form.progress}%` }}
          />
        </div>
      </div>

      {/* Current AI question */}
      {!form.isComplete && form.currentQuestion && (
        <div className={cn(
          "flex items-start gap-2 rounded-lg border p-3",
          colors.bg, colors.border
        )}>
          <div className="mt-0.5 shrink-0">
            {isRecording ? (
              <Mic className={cn("h-4 w-4 animate-pulse text-red-500")} />
            ) : (
              <MessageSquare className={cn("h-4 w-4", colors.text)} />
            )}
          </div>
          <div className="flex flex-col gap-1">
            <span className={cn("text-[10px] font-bold uppercase tracking-wider", colors.text)}>
              AI asking: {form.currentField?.label}
            </span>
            <span className="text-[12px] font-medium text-on-surface leading-[16px]">
              &ldquo;{form.currentQuestion}&rdquo;
            </span>
            {form.currentQuestionTranslated && form.currentQuestionTranslated !== form.currentQuestion && (
              <span className="text-[11px] italic text-on-surface-variant leading-[14px]">
                &ldquo;{form.currentQuestionTranslated}&rdquo;
              </span>
            )}
          </div>
        </div>
      )}

      {/* Listening indicator */}
      {isRecording && !form.isComplete && (
        <div className="flex items-center justify-center gap-2 rounded-full bg-red-50 px-4 py-1.5 text-[11px] font-medium text-red-700">
          <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
          Listening for answer&hellip;
        </div>
      )}

      {/* Filled fields list */}
      <div
        ref={fieldListRef}
        className="flex max-h-[260px] flex-col gap-1.5 overflow-y-auto"
      >
        {definition.fields.map((field) => {
          const value = form.filledFields[field.key];
          const isFilled = !!value;
          const isJustFilled = justFilled === field.key;
          const isCurrent = form.currentField?.key === field.key;

          return (
            <div
              key={field.key}
              className={cn(
                "flex items-center gap-2 rounded border px-3 py-2 transition-all duration-500",
                isJustFilled && "ring-2 ring-green-400 bg-green-50 border-green-300 animate-pulse",
                isFilled && !isJustFilled && "bg-surface-container-lowest border-green-200",
                isCurrent && !isFilled && "bg-primary-fixed/30 border-primary/30",
                !isFilled && !isCurrent && "bg-gray-50 border-gray-200 opacity-60"
              )}
            >
              {/* Status indicator */}
              <div className="shrink-0">
                {isFilled ? (
                  <CheckCircle className={cn(
                    "h-4 w-4",
                    isJustFilled ? "text-green-500 animate-bounce" : "text-green-500"
                  )} />
                ) : isCurrent ? (
                  <div className="h-4 w-4 rounded-full border-2 border-primary animate-pulse" />
                ) : (
                  <div className="h-4 w-4 rounded-full border border-gray-300" />
                )}
              </div>

              {/* Field label and value */}
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                  {field.label}
                </span>
                {isFilled ? (
                  <div className="flex items-center gap-1">
                    <span className="truncate text-[12px] font-medium text-on-surface">
                      {value}
                    </span>
                    {isJustFilled && <Sparkles className="h-3 w-3 shrink-0 text-amber-500 animate-spin" />}
                  </div>
                ) : isCurrent ? (
                  <span className="text-[11px] text-primary italic">Waiting for answer&hellip;</span>
                ) : (
                  <span className="text-[11px] text-gray-400">&mdash;</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Completion state */}
      {form.isComplete && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3">
            <CheckCircle className="h-5 w-5 shrink-0 text-green-600" />
            <div>
              <span className="text-[12px] font-semibold text-green-800">Form Complete!</span>
              <p className="text-[11px] text-green-700">All {form.totalFields} fields have been auto-filled by AI voice.</p>
            </div>
          </div>

          {/* PDF actions */}
          {form.pdfReady && form.pdfUrl ? (
            <a
              href={`${API_BASE}${form.pdfUrl}`}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "flex items-center justify-center gap-2 rounded-lg px-4 py-2.5",
                "bg-primary text-white font-semibold text-[13px]",
                "hover:bg-primary-container hover:text-on-primary-fixed transition-colors",
                "shadow-md hover:shadow-lg"
              )}
            >
              <Download className="h-4 w-4" />
              Download PDF
            </a>
          ) : (
            <button
              onClick={onGeneratePdf}
              className={cn(
                "flex items-center justify-center gap-2 rounded-lg px-4 py-2.5",
                "bg-primary text-white font-semibold text-[13px]",
                "hover:bg-primary-container hover:text-on-primary-fixed transition-colors",
                "shadow-md hover:shadow-lg active:scale-95"
              )}
            >
              <FileText className="h-4 w-4" />
              Generate PDF
            </button>
          )}
        </div>
      )}
    </div>
  );
}
