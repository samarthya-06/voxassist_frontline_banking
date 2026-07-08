import { useEffect, useRef, useState, useCallback } from "react";
import { buildSessionWsUrl } from "../../config/env";
import { DEFAULT_CUSTOMER_LANGUAGE, DEFAULT_CUSTOMER_LANGUAGE_CODE } from "../../config/languages";
import type { SopResult } from "../session/sessionSlice";

type KioskConnectionStatus = "idle" | "connecting" | "connected" | "offline";

type BrowserSpeechRecognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type SpeechRecognitionResultEvent = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      0: { transcript: string };
    };
  };
};

interface KioskState {
  connectionStatus: KioskConnectionStatus;
  language: string;
  languageCode: string;
  isListening: boolean;
  isSessionActive: boolean;
  isSpeaking: boolean;
  assistantText: string | null;
  lastError: string | null;
  pdfUrl: string | null;

  // Form State
  formActive: boolean;
  questionTranslated: string | null;
  questionText: string | null;
  progress: number;
  filledCount: number;
  totalFields: number;
  isComplete: boolean;

  // Transcript State
  lastCustomerTranscriptNative: string | null;
  lastCustomerTranscriptEnglish: string | null;
  lastStaffTranscriptEnglish: string | null;
  lastStaffTranscriptNative: string | null;
  sopResult: SopResult | null;
}

function buildWsUrl(sessionId: string, authToken: string) {
  return buildSessionWsUrl(sessionId, authToken);
}

export function useKioskSession(sessionId: string | null, authToken: string | null) {
  const [state, setState] = useState<KioskState>({
    connectionStatus: "idle",
    language: DEFAULT_CUSTOMER_LANGUAGE.language,
    languageCode: DEFAULT_CUSTOMER_LANGUAGE.code,
    isListening: false,
    isSessionActive: false,
    isSpeaking: false,
    assistantText: null,
    lastError: null,
    pdfUrl: null,
    formActive: false,
    questionTranslated: null,
    questionText: null,
    progress: 0,
    filledCount: 0,
    totalFields: 0,
    isComplete: false,
    lastCustomerTranscriptNative: null,
    lastCustomerTranscriptEnglish: null,
    lastStaffTranscriptEnglish: null,
    lastStaffTranscriptNative: null,
    sopResult: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const usingSpeechRecognitionRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadFrameRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const shouldReconnectRef = useRef(true);
  const sessionActiveRef = useRef(false);
  const pausedRef = useRef(false);
  const recordingUtteranceRef = useRef(false);
  const speechStartedAtRef = useRef(0);
  const lastSpeechAtRef = useRef(0);
  const languageCodeRef = useRef(DEFAULT_CUSTOMER_LANGUAGE_CODE);
  const recognitionStartedRef = useRef(false);
  const recognitionFallbackTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const lastAssistantTextRef = useRef("");
  const lastSpeechEndedAtRef = useRef(0);
  const isProcessingRef = useRef(false);
  const lastAssistantDurationRef = useRef(0);
  const assistantPlayStartRef = useRef(0);
  const audioPlaybackQueueRef = useRef<Promise<void>>(Promise.resolve());

  const resumeListening = useCallback(() => {
    if (!sessionActiveRef.current) return;
    isProcessingRef.current = false;
    pausedRef.current = false;
    if (usingSpeechRecognitionRef.current) {
      setState((prev) => ({ ...prev, isSpeaking: false, isListening: false }));
      window.setTimeout(() => startRecognitionIfNeeded(), 500);
    } else {
      setState((prev) => ({ ...prev, isSpeaking: false, isListening: false }));
    }
  }, []);

  const playAudioBase64 = useCallback(async (
    audioB64: string | null | undefined,
    fallbackText = "",
    langCode?: string,
    options: { resumeAfter?: boolean } = {},
  ) => {
    const resumeAfter = options.resumeAfter ?? true;
    pausedRef.current = true;
    lastAssistantTextRef.current = fallbackText;
    assistantPlayStartRef.current = performance.now();
    recognitionRef.current?.stop();
    setState((prev) => ({ ...prev, isSpeaking: true, isListening: false }));

    if (!audioB64) {
      await speakWithBrowser(fallbackText, langCode || languageCodeRef.current);
      lastAssistantDurationRef.current = performance.now() - assistantPlayStartRef.current;
      lastSpeechEndedAtRef.current = performance.now();
      await delay(400);
      if (resumeAfter) resumeListening();
      return;
    }

    try {
      const audioBlob = base64ToBlob(audioB64, "audio/wav");
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      await new Promise<void>((resolve) => {
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          resolve();
        };
        audio.onerror = () => {
          URL.revokeObjectURL(audioUrl);
          resolve();
        };
        audio.play().catch(async () => {
          await speakWithBrowser(fallbackText, langCode || languageCodeRef.current);
          resolve();
        });
      });
    } finally {
      lastAssistantDurationRef.current = performance.now() - assistantPlayStartRef.current;
      lastSpeechEndedAtRef.current = performance.now();
      await delay(400);
      if (resumeAfter) resumeListening();
    }
  }, [resumeListening]);

  const enqueueAudio = useCallback((
    audioB64: string | null | undefined,
    fallbackText = "",
    langCode?: string,
    resumeAfter = true,
  ) => {
    audioPlaybackQueueRef.current = audioPlaybackQueueRef.current
      .catch(() => { })
      .then(() => playAudioBase64(audioB64, fallbackText, langCode, { resumeAfter }));
  }, [playAudioBase64]);

  const handleMessage = useCallback((event: MessageEvent) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case "transcript":
        if (data.item.speaker === "customer") {
          setState((prev) => ({
            ...prev,
            lastCustomerTranscriptNative: data.item.originalText,
            // Bug-3 fix: strip any RAG expansion suffix before displaying the
            // translated text — the English hint appended for retrieval must
            // never appear on the kiosk screen.
            lastCustomerTranscriptEnglish: sanitizeTranscriptText(data.item.translatedText),
            lastStaffTranscriptEnglish: null,
            lastStaffTranscriptNative: null,
          }));
          if (data.assistantResponse) {
            setState((prev) => ({
              ...prev,
              assistantText: data.assistantResponse,
              lastError: null,
            }));
            if (data.assistantAudio) {
              enqueueAudio(data.assistantAudio, data.assistantResponse, languageCodeRef.current);
            } else if (data.assistantAudioPending) {
              pausedRef.current = true;
              recognitionRef.current?.stop();
              setState((prev) => ({ ...prev, isSpeaking: true, isListening: false }));
            } else {
              enqueueAudio(null, data.assistantResponse, languageCodeRef.current);
            }
          }
        } else if (data.item.speaker === "assistant") {
          setState((prev) => ({
            ...prev,
            assistantText: data.item.originalText,
            lastError: null,
          }));
          if (data.assistantAudio) {
            enqueueAudio(data.assistantAudio, data.item.originalText, languageCodeRef.current);
          } else if (data.assistantAudioPending) {
            pausedRef.current = true;
            recognitionRef.current?.stop();
            setState((prev) => ({ ...prev, isSpeaking: true, isListening: false }));
          } else {
            enqueueAudio(null, data.item.originalText, languageCodeRef.current);
          }
        } else if (data.item.speaker === "staff") {
          // Bug-5 fix: do NOT overwrite assistantText here.
          // The kiosk display shows the AI's response to the customer (assistantText).
          // Overwriting it with the staff's translated speech replaces the AI answer
          // with the Marathi version of what the staff member just said, which is wrong.
          // Staff speech is tracked only via the dedicated transcript fields below.
          setState((prev) => ({
            ...prev,
            lastStaffTranscriptEnglish: data.item.originalText,
            lastStaffTranscriptNative: data.item.translatedText,
            lastCustomerTranscriptNative: null,
            lastCustomerTranscriptEnglish: null,
            lastError: null,
          }));
          if (data.translatedAudioPending) {
            pausedRef.current = true;
            recognitionRef.current?.stop();
            setState((prev) => ({ ...prev, isSpeaking: true, isListening: false }));
          }
        }
        break;

      case "tts_audio":
        if (data.audience === "staff") break;
        enqueueAudio(data.audio_b64, data.text || "", languageCodeRef.current, data.isFinalChunk ?? true);
        break;

      case "language_detected":
        languageCodeRef.current = data.code;
        setState((prev) => ({
          ...prev,
          language: data.language,
          languageCode: data.code,
        }));
        break;

      case "form_started":
        setState((prev) => ({
          ...prev,
          formActive: true,
          isComplete: false,
          assistantText: data.questionTranslated,
          questionText: data.questionText,
          questionTranslated: data.questionTranslated,
          progress: data.formState.progress,
          filledCount: data.formState.filledCount,
          totalFields: data.formState.totalFields,
          // Clear previous transcript context when a new question is asked
          lastCustomerTranscriptNative: null,
          lastCustomerTranscriptEnglish: null,
          lastStaffTranscriptEnglish: null,
          lastStaffTranscriptNative: null,
        }));
        enqueueAudio(data.questionAudio, data.questionTranslated, languageCodeRef.current);
        break;

      case "form_field_filled":
        setState((prev) => ({
          ...prev,
          assistantText: data.questionTranslated,
          questionText: data.questionText,
          questionTranslated: data.questionTranslated,
          progress: data.formState.progress,
          filledCount: data.formState.filledCount,
          totalFields: data.formState.totalFields,
          // Clear previous transcript context when moving to the next question
          lastCustomerTranscriptNative: null,
          lastCustomerTranscriptEnglish: null,
          lastStaffTranscriptEnglish: null,
          lastStaffTranscriptNative: null,
        }));
        enqueueAudio(data.questionAudio, data.questionTranslated, languageCodeRef.current);
        break;

      case "form_complete":
        setState((prev) => ({
          ...prev,
          isComplete: true,
          progress: 100,
          questionText: null,
          questionTranslated: null,
          assistantText: data.completionTranslated || "Your form is complete.",
        }));
        enqueueAudio(data.completionAudio, data.completionTranslated || "Your form is complete.", languageCodeRef.current);
        wsRef.current?.send(JSON.stringify({ type: "generate_form_pdf" }));
        break;

      case "form_cancelled":
        setState((prev) => ({
          ...prev,
          formActive: false,
          isComplete: false,
          questionText: null,
          questionTranslated: null,
          progress: 0,
        }));
        break;

      case "form_pdf_ready":
        setState((prev) => ({
          ...prev,
          pdfUrl: data.downloadUrl,
        }));
        break;

      case "form_error":
        setState((prev) => ({
          ...prev,
          lastError: data.message,
        }));
        resumeListening();
        break;

      case "sop":
        setState((prev) => ({
          ...prev,
          sopResult: data.result,
        }));
        break;

      case "recording_status":
        if (data.mode === "customer") {
          setState((prev) => ({ ...prev, isListening: Boolean(data.active) }));
        }
        break;
    }
  }, [enqueueAudio, resumeListening]);

  useEffect(() => {
    if (!sessionId || !authToken) {
      setState(prev => ({ ...prev, connectionStatus: "offline" }));
      return;
    }

    shouldReconnectRef.current = true;

    const reconnect = () => {
      setState(prev => ({ ...prev, connectionStatus: "connecting" }));
      const ws = new WebSocket(buildWsUrl(sessionId, authToken));
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptRef.current = 0;
        setState(prev => ({ ...prev, connectionStatus: "connected" }));
      };

      ws.onclose = () => {
        setState(prev => ({ ...prev, connectionStatus: "offline", isListening: false }));
        if (!shouldReconnectRef.current) return;

        const delay = Math.min(30000, 2000 * 2 ** reconnectAttemptRef.current);
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = window.setTimeout(() => reconnect(), delay);
      };

      ws.onerror = () => {
        setState(prev => ({ ...prev, connectionStatus: "offline", isListening: false }));
      };

      ws.onmessage = handleMessage;
    };

    reconnect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      stopVoiceLoop();
    };
  }, [sessionId, authToken, handleMessage]);

  const startConversation = useCallback(async () => {
    if (state.connectionStatus !== "connected") return;
    sessionActiveRef.current = true;
    pausedRef.current = true;
    setState((prev) => ({
      ...prev,
      isSessionActive: true,
      lastError: null,
      assistantText: "शुभ सकाळ, आमच्या बँकेत आपले स्वागत आहे. आज मी आपली कशी मदत करू शकतो?",
    }));

    try {
      await startVoiceLoop();
      wsRef.current?.send(JSON.stringify({ type: "start_customer_session", languageCode: languageCodeRef.current || DEFAULT_CUSTOMER_LANGUAGE_CODE }));
    } catch {
      setState((prev) => ({
        ...prev,
        lastError: "Microphone access is needed for the kiosk conversation.",
        isSessionActive: false,
      }));
      sessionActiveRef.current = false;
      pausedRef.current = false;
    }
  }, [state.connectionStatus]);

  const stopConversation = useCallback(() => {
    sessionActiveRef.current = false;
    pausedRef.current = true;
    wsRef.current?.send(JSON.stringify({ type: "stop_listening", mode: "customer" }));
    stopVoiceLoop();
    setState((prev) => ({
      ...prev,
      isSessionActive: false,
      isListening: false,
      isSpeaking: false,
    }));
  }, []);

  async function startVoiceLoop() {
    if (streamRef.current) return;

    if (!navigator.mediaDevices?.getUserMedia) {
      wsRef.current?.send(JSON.stringify({ type: "demo_text", mode: "customer" }));
      return;
    }

    if (startSpeechRecognitionLoop()) return;

    await startAudioVadLoop();
  }

  async function startAudioVadLoop() {
    if (streamRef.current) return;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    streamRef.current = stream;

    const audioCtx = new AudioContext();
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 1024;
    audioCtx.createMediaStreamSource(stream).connect(analyser);
    audioCtxRef.current = audioCtx;
    analyserRef.current = analyser;
    runVadLoop();
  }

  function stopVoiceLoop() {
    if (recognitionFallbackTimerRef.current) window.clearTimeout(recognitionFallbackTimerRef.current);
    recognitionFallbackTimerRef.current = null;
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    usingSpeechRecognitionRef.current = false;
    recognitionStartedRef.current = false;
    if (vadFrameRef.current) cancelAnimationFrame(vadFrameRef.current);
    vadFrameRef.current = null;
    stopUtteranceRecording(false);
    audioCtxRef.current?.close().catch(() => { });
    audioCtxRef.current = null;
    analyserRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  function startSpeechRecognitionLoop() {
    const Recognition = getSpeechRecognitionConstructor();
    if (!Recognition) return false;

    usingSpeechRecognitionRef.current = true;
    recognitionStartedRef.current = false;
    const recognition = new Recognition();
    recognitionRef.current = recognition;
    recognition.lang = languageCodeRef.current || DEFAULT_CUSTOMER_LANGUAGE_CODE;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      recognitionStartedRef.current = true;
      if (recognitionFallbackTimerRef.current) window.clearTimeout(recognitionFallbackTimerRef.current);
      recognitionFallbackTimerRef.current = null;
      if (!pausedRef.current) {
        setState((prev) => ({ ...prev, isListening: true, lastError: null }));
      }
    };

    recognition.onend = () => {
      setState((prev) => ({ ...prev, isListening: false }));
      if (sessionActiveRef.current && !pausedRef.current && !isProcessingRef.current) {
        window.setTimeout(() => startRecognitionIfNeeded(), 800);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed") {
        setState((prev) => ({ ...prev, lastError: "Microphone permission is needed for voice conversation." }));
      } else if (event.error === "network" || event.error === "service-not-allowed") {
        void switchToAudioVadFallback();
      }
    };

    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = result?.[0]?.transcript ?? "";
        if (result?.isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }
      const previewText = interimTranscript.trim();
      if (previewText) {
        setState((prev) => ({
          ...prev,
          // Bug-3 fix: interim previews from browser Speech Recognition can
          // contain partial words that look like expansion terms; sanitize
          // before showing on the kiosk display.
          lastCustomerTranscriptNative: sanitizeTranscriptText(previewText) ?? previewText,
          lastCustomerTranscriptEnglish: "",
        }));
      }

      const text = finalTranscript.trim();
      if (!text) return;
      if (shouldIgnoreRecognizedText(text, lastAssistantTextRef.current, lastSpeechEndedAtRef.current)) {
        window.setTimeout(() => {
          pausedRef.current = false;
          startRecognitionIfNeeded();
        }, 1000);
        return;
      }
      // Prevent double-sends while backend is processing
      if (isProcessingRef.current) return;

      isProcessingRef.current = true;
      pausedRef.current = true;
      recognition.stop();
      setState((prev) => ({
        ...prev,
        isListening: false,
        lastCustomerTranscriptNative: text,
        lastCustomerTranscriptEnglish: "",
      }));
      wsRef.current?.send(JSON.stringify({
        type: "customer_text",
        mode: "customer",
        text,
        languageCode: languageCodeRef.current || DEFAULT_CUSTOMER_LANGUAGE_CODE,
      }));
    };

    startRecognitionIfNeeded();
    recognitionFallbackTimerRef.current = window.setTimeout(() => {
      if (sessionActiveRef.current && !pausedRef.current && !recognitionStartedRef.current) {
        void switchToAudioVadFallback();
      }
    }, 1800);
    return true;
  }

  function startRecognitionIfNeeded() {
    const recognition = recognitionRef.current;
    if (!recognition || !sessionActiveRef.current || pausedRef.current) return;
    try {
      recognitionStartedRef.current = false;
      recognition.lang = languageCodeRef.current || DEFAULT_CUSTOMER_LANGUAGE_CODE;
      recognition.start();
      if (recognitionFallbackTimerRef.current) window.clearTimeout(recognitionFallbackTimerRef.current);
      recognitionFallbackTimerRef.current = window.setTimeout(() => {
        if (sessionActiveRef.current && !pausedRef.current && !recognitionStartedRef.current) {
          void switchToAudioVadFallback();
        }
      }, 1800);
    } catch {
      // Browser throws if recognition is already running.
    }
  }

  async function switchToAudioVadFallback() {
    if (!usingSpeechRecognitionRef.current) return;
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    usingSpeechRecognitionRef.current = false;
    recognitionStartedRef.current = false;
    if (recognitionFallbackTimerRef.current) window.clearTimeout(recognitionFallbackTimerRef.current);
    recognitionFallbackTimerRef.current = null;

    try {
      await startAudioVadLoop();
    } catch {
      setState((prev) => ({
        ...prev,
        isListening: false,
        lastError: "Microphone permission is needed for voice conversation.",
      }));
    }
  }

  function runVadLoop() {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const data = new Uint8Array(analyser.fftSize);
    const silenceMs = 750;
    const minSpeechMs = 350;
    const maxUtteranceMs = 24000;
    const threshold = 0.025;

    const tick = () => {
      if (!sessionActiveRef.current || !analyserRef.current) return;

      analyser.getByteTimeDomainData(data);
      const rms = getRms(data);
      const now = performance.now();
      // Scale cooldown with assistant speech duration (minimum 2.2s)
      const dynamicCooldown = Math.max(900, Math.min(lastAssistantDurationRef.current * 0.25, 3000));
      const coolingDownFromAssistant = now - lastSpeechEndedAtRef.current < dynamicCooldown;
      const hasSpeech = !coolingDownFromAssistant && !isProcessingRef.current && rms > threshold;

      if (!pausedRef.current && hasSpeech) {
        lastSpeechAtRef.current = now;
        if (!recordingUtteranceRef.current) {
          startUtteranceRecording();
          speechStartedAtRef.current = now;
        }
      }

      if (recordingUtteranceRef.current) {
        const silentLongEnough = now - lastSpeechAtRef.current > silenceMs;
        const spokeLongEnough = now - speechStartedAtRef.current > minSpeechMs;
        const hitMaxLength = now - speechStartedAtRef.current > maxUtteranceMs;
        if ((silentLongEnough && spokeLongEnough) || hitMaxLength) {
          stopUtteranceRecording(true);
        }
      }

      vadFrameRef.current = requestAnimationFrame(tick);
    };

    vadFrameRef.current = requestAnimationFrame(tick);
  }

  function startUtteranceRecording() {
    const stream = streamRef.current;
    if (!stream || recordingUtteranceRef.current) return;

    chunksRef.current = [];
    const recorder = new MediaRecorder(stream);
    recorderRef.current = recorder;
    recordingUtteranceRef.current = true;
    setState((prev) => ({ ...prev, isListening: true, lastError: null }));
    wsRef.current?.send(JSON.stringify({ type: "start", mode: "customer" }));

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };

    recorder.onstop = async () => {
      recordingUtteranceRef.current = false;
      setState((prev) => ({ ...prev, isListening: false }));
      if (chunksRef.current.length === 0 || isProcessingRef.current) {
        if (!isProcessingRef.current) resumeListening();
        return;
      }

      isProcessingRef.current = true;
      pausedRef.current = true;
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
      const wavBytes = await blobToWav(blob);
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "audio_meta", mode: "customer" }));
        wsRef.current.send(wavBytes);
      } else {
        isProcessingRef.current = false;
        resumeListening();
      }
    };

    recorder.start(250);
  }

  function stopUtteranceRecording(shouldSend: boolean) {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    if (!shouldSend) chunksRef.current = [];
    recorder.stop();
  }

  return {
    ...state,
    startConversation,
    stopConversation,
  };
}

function base64ToBlob(b64: string, mimeType: string): Blob {
  const bytes = atob(b64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  return new Blob([arr], { type: mimeType });
}

function getSpeechRecognitionConstructor() {
  const speechWindow = window as typeof window & {
    SpeechRecognition?: new () => BrowserSpeechRecognition;
    webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
  };
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

function delay(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

/**
 * Strip RAG query-expansion suffixes that the backend appends to improve
 * retrieval quality.  These strings must never appear on the kiosk screen.
 *
 * The patterns below mirror the expansions in
 * ai_orchestrator._normalize_customer_query_for_rag() and
 * _english_hint_for_native_text().  Keep this list in sync with those
 * methods when new expansion patterns are added.
 */
const RAG_EXPANSION_SUFFIXES: readonly string[] = [
  // Cheque bounce expansion
  " cheque bounce cheque return insufficient funds charges drawer payee cibil",
  // Stop-payment expansion
  " cheque stop payment charges",
  // Generic hint tail produced by _english_hint_for_native_text when no
  // specific intent is matched — strip anything from "banking service
  // information" onward to avoid cluttering the display.
  " banking service information documents charges eligibility",
];

/**
 * Remove backend RAG-expansion suffixes from a translated transcript string
 * so that only the customer's actual words (or a clean translation) are shown.
 */
function sanitizeTranscriptText(text: string | null | undefined): string | null {
  if (!text) return text ?? null;
  const lower = text.toLowerCase();
  for (const suffix of RAG_EXPANSION_SUFFIXES) {
    const idx = lower.indexOf(suffix);
    if (idx !== -1) {
      const cleaned = text.slice(0, idx).trim();
      return cleaned || text;
    }
  }
  return text;
}

function normalizeSpeechText(text: string) {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function shouldIgnoreRecognizedText(text: string, assistantText: string, lastSpeechEndedAt: number) {
  const normalized = normalizeSpeechText(text);
  if (!normalized) return true;

  const elapsedSinceAssistant = performance.now() - lastSpeechEndedAt;
  if (elapsedSinceAssistant < 2200) return true;

  const assistant = normalizeSpeechText(assistantText);
  if (assistant && normalized.length > 8 && assistant.includes(normalized)) return true;
  if (assistant && assistant.length > 8 && normalized.includes(assistant.slice(0, Math.min(assistant.length, 40)))) {
    return true;
  }

  const tokens = normalized.split(" ").filter(Boolean);
  if (tokens.length < 10) return false;

  const counts = new Map<string, number>();
  for (const token of tokens) {
    counts.set(token, (counts.get(token) ?? 0) + 1);
  }

  const maxRepeat = Math.max(...counts.values());
  const repeatedDevanagariFillers = (normalized.match(/(?:ते हे|जे आहे|हे जे|आहे ते)/g) ?? []).length;
  const repeatedEnglishFillers = (normalized.match(/(?:this is|that is|so this)/g) ?? []).length;
  return maxRepeat / tokens.length > 0.45 || repeatedDevanagariFillers >= 4 || repeatedEnglishFillers >= 4;
}

async function speakWithBrowser(text: string, langCode: string) {
  if (!text || !window.speechSynthesis) return;

  window.speechSynthesis.cancel();
  await new Promise<void>((resolve) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = langCode || DEFAULT_CUSTOMER_LANGUAGE_CODE;
    utterance.rate = 0.92;
    utterance.pitch = 1;
    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith(utterance.lang.toLowerCase().slice(0, 2)));
    if (matchingVoice) utterance.voice = matchingVoice;
    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();
    window.speechSynthesis.speak(utterance);
  });
}

function getRms(data: Uint8Array): number {
  let sum = 0;
  for (const value of data) {
    const normalized = (value - 128) / 128;
    sum += normalized * normalized;
  }
  return Math.sqrt(sum / data.length);
}

async function blobToWav(blob: Blob): Promise<ArrayBuffer> {
  const arrayBuffer = await blob.arrayBuffer();
  const audioCtx = new AudioContext({ sampleRate: 16000 });

  try {
    const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
    const sampleRate = 16000;
    const channelData = audioBuffer.getChannelData(0);
    const wavBuffer = new ArrayBuffer(44 + channelData.length * 2);
    const view = new DataView(wavBuffer);

    writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + channelData.length * 2, true);
    writeString(view, 8, "WAVE");
    writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, "data");
    view.setUint32(40, channelData.length * 2, true);

    let offset = 44;
    for (let i = 0; i < channelData.length; i++, offset += 2) {
      const sample = Math.max(-1, Math.min(1, channelData[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    }

    audioCtx.close();
    return wavBuffer;
  } catch {
    audioCtx.close();
    return arrayBuffer;
  }
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}
