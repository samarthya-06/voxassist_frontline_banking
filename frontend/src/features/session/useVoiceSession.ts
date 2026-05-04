import { useEffect, useRef, useCallback } from "react";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import {
  addTranscript,
  cancelFormInterview,
  mergeEntities,
  setActionChips,
  setComplianceAlert,
  setConnectionStatus,
  setDetectedLanguage,
  setEscalationAlert,
  setFormComplete,
  setFormPdfReady,
  setRecording,
  setSopResult,
  setSummary,
  startFormInterview,
  updateFormField,
  type BankingEntities,
  type ComplianceAlert,
  type FormCurrentField,
  type FormDefinition,
  type SopResult,
  type TranscriptItem
} from "./sessionSlice";

type ServerMessage =
  | {
    type: "transcript";
    item: TranscriptItem;
    entities?: Partial<BankingEntities>;
    actionChips?: string[];
    assistantResponse?: string;
    assistantAudio?: string;
    assistantAudioPending?: boolean;
  }
  | { type: "sop"; result: SopResult }
  | { type: "compliance"; alert: ComplianceAlert | null }
  | { type: "summary"; english: string[]; customerLanguage: string[] }
  | { type: "language_detected"; language: string; code: string }
  | { type: "tts_audio"; audio_b64: string | null; text: string; audience?: "all" | "staff" | "customer"; isFinalChunk?: boolean }
  | { type: "escalation_alert"; message: string }
  // Form interview messages
  | {
    type: "form_started";
    formDefinition: FormDefinition;
    formState: { formType: string; totalFields: number; filledCount: number; progress: number; filledFields: Record<string, string> };
    currentField: FormCurrentField;
    questionText: string;
    questionTranslated: string;
    questionAudio: string | null;
  }
  | {
    type: "form_field_filled";
    formState: { filledCount: number; progress: number; filledFields: Record<string, string>; totalFields: number };
    filledFieldKey: string;
    filledFieldLabel: string;
    filledFieldValue: string;
    nativeAnswer: string;
    englishAnswer: string;
    currentField: FormCurrentField;
    questionText: string;
    questionTranslated: string;
    questionAudio: string | null;
  }
  | {
    type: "form_complete";
    formState: { filledCount: number; progress: number; filledFields: Record<string, string>; totalFields: number };
    filledFieldKey: string;
    filledFieldLabel: string;
    filledFieldValue: string;
    nativeAnswer: string;
    englishAnswer: string;
    completionText: string;
    completionTranslated: string;
    completionAudio: string | null;
  }
  | {
    type: "form_retry";
    formState: { filledCount: number; progress: number; filledFields: Record<string, string>; totalFields: number };
    currentField: FormCurrentField;
    questionText: string;
    questionTranslated: string;
    questionAudio: string | null;
  }
  | { type: "form_pdf_ready"; downloadUrl: string }
  | { type: "form_cancelled" }
  | { type: "form_error"; message: string };

const WS_URL = import.meta.env.VITE_VOXASSIST_WS_URL ?? "ws://localhost:8000/ws/session/demo-session";

function buildWsUrl(authToken?: string, sessionId = "demo-session") {
  const baseWsUrl = WS_URL.includes("demo-session") ? WS_URL.replace("demo-session", sessionId) : WS_URL;
  if (!authToken) return baseWsUrl;
  try {
    const url = new URL(baseWsUrl);
    url.searchParams.set("token", authToken);
    return url.toString();
  } catch {
    const separator = baseWsUrl.includes("?") ? "&" : "?";
    return `${baseWsUrl}${separator}token=${encodeURIComponent(authToken)}`;
  }
}

export function useVoiceSession(authToken?: string, sessionId = "demo-session") {
  const dispatch = useAppDispatch();
  const selectedLanguage = useAppSelector((state) => state.session.language);
  const selectedLanguageCode = useAppSelector((state) => state.session.languageCode);
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const modeRef = useRef<"customer" | "staff">("customer");
  const waveformCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const waveformAudioRef = useRef<AudioContext | null>(null);
  const waveformFrameRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const shouldReconnectRef = useRef(true);
  const selectedLanguageRef = useRef({ language: selectedLanguage, code: selectedLanguageCode });
  const audioPlaybackQueueRef = useRef<Promise<void>>(Promise.resolve());
  const recordingAutoStopTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);

  useEffect(() => {
    selectedLanguageRef.current = { language: selectedLanguage, code: selectedLanguageCode };
  }, [selectedLanguage, selectedLanguageCode]);

  const enqueueAudio = useCallback((audioB64: string) => {
    audioPlaybackQueueRef.current = audioPlaybackQueueRef.current
      .catch(() => { })
      .then(() => playAudioBase64Async(audioB64));
  }, []);

  const handleMessage = useCallback((event: MessageEvent) => {
    const data = JSON.parse(event.data) as ServerMessage;

    switch (data.type) {
      case "transcript":
        dispatch(addTranscript(data.item));
        if (data.entities) dispatch(mergeEntities(data.entities));
        if (data.actionChips) dispatch(setActionChips(data.actionChips));

        // Auto-play assistant response audio if provided
        if (data.assistantResponse) {
          dispatch(addTranscript({
            id: Date.now().toString(),
            speaker: "assistant",
            sourceLanguage: data.item.sourceLanguage,
            originalText: data.assistantResponse,
            translatedText: data.assistantResponse,
            confidence: 1.0,
            timestamp: data.item.timestamp
          }));
        }

        if (data.assistantAudio) {
          enqueueAudio(data.assistantAudio);
        }
        break;

      case "sop":
        dispatch(setSopResult(data.result));
        break;

      case "compliance":
        dispatch(setComplianceAlert(data.alert));
        break;

      case "summary":
        dispatch(setSummary({ english: data.english, customerLanguage: data.customerLanguage }));
        break;

      case "language_detected":
        dispatch(setDetectedLanguage({ language: data.language, code: data.code }));
        break;

      case "tts_audio":
        if (data.audience === "customer") {
          break;
        }
        if (data.audio_b64) {
          enqueueAudio(data.audio_b64);
        }
        break;

      case "escalation_alert":
        dispatch(setEscalationAlert(data.message));
        break;

      // ── Form Interview Messages ─────────────────────────────────────
      case "form_started":
        dispatch(startFormInterview({
          formDefinition: data.formDefinition,
          formState: data.formState,
          currentField: data.currentField,
          questionText: data.questionText,
          questionTranslated: data.questionTranslated,
        }));
        // Auto-play the first question TTS
        if (data.questionAudio) enqueueAudio(data.questionAudio);
        break;

      case "form_field_filled":
        dispatch(updateFormField({
          filledFieldKey: data.filledFieldKey,
          filledFieldValue: data.filledFieldValue,
          formState: data.formState,
          currentField: data.currentField,
          questionText: data.questionText,
          questionTranslated: data.questionTranslated,
        }));
        // Auto-play the next question TTS
        if (data.questionAudio) enqueueAudio(data.questionAudio);
        break;

      case "form_complete":
        dispatch(setFormComplete({
          filledFieldKey: data.filledFieldKey,
          filledFieldValue: data.filledFieldValue,
          formState: data.formState,
        }));
        // Auto-play completion message
        if (data.completionAudio) enqueueAudio(data.completionAudio);
        break;

      case "form_retry":
        // Same question again — just play the TTS
        if (data.questionAudio) enqueueAudio(data.questionAudio);
        break;

      case "form_pdf_ready":
        dispatch(setFormPdfReady(data.downloadUrl));
        break;

      case "form_cancelled":
        dispatch(cancelFormInterview());
        break;

      case "form_error":
        console.error("Form error:", data.message);
        break;
    }
  }, [dispatch, enqueueAudio]);

  const sendSelectedLanguage = useCallback((socket: WebSocket | null = wsRef.current) => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "set_language", code: selectedLanguageRef.current.code }));
    }
  }, []);

  const stopWaveform = useCallback(() => {
    if (waveformFrameRef.current) cancelAnimationFrame(waveformFrameRef.current);
    waveformFrameRef.current = null;
    waveformAudioRef.current?.close().catch(() => { });
    waveformAudioRef.current = null;
    const canvas = waveformCanvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, []);

  const startWaveform = useCallback((stream: MediaStream) => {
    stopWaveform();
    const canvas = waveformCanvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const audioCtx = new AudioContext();
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 128;
    audioCtx.createMediaStreamSource(stream).connect(analyser);
    waveformAudioRef.current = audioCtx;

    const data = new Uint8Array(analyser.frequencyBinCount);
    const draw = () => {
      analyser.getByteTimeDomainData(data);
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);
      ctx.lineWidth = 2;
      ctx.strokeStyle = "rgba(255,255,255,0.9)";
      ctx.beginPath();
      data.forEach((value, index) => {
        const x = (index / (data.length - 1)) * width;
        const y = (value / 255) * height;
        index === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();
      waveformFrameRef.current = requestAnimationFrame(draw);
    };
    draw();
  }, [stopWaveform]);

  useEffect(() => {
    shouldReconnectRef.current = true;

    const reconnect = () => {
      dispatch(setConnectionStatus("connecting"));
      const ws = new WebSocket(buildWsUrl(authToken, sessionId));
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptRef.current = 0;
        dispatch(setConnectionStatus("connected"));
        sendSelectedLanguage(ws);
      };
      ws.onclose = () => {
        dispatch(setConnectionStatus("offline"));
        if (!shouldReconnectRef.current) return;

        const delay = Math.min(30000, 2000 * 2 ** reconnectAttemptRef.current);
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = window.setTimeout(() => reconnect(), delay);
      };
      ws.onerror = () => dispatch(setConnectionStatus("offline"));
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
      stopWaveform();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      if (recordingAutoStopTimerRef.current) window.clearTimeout(recordingAutoStopTimerRef.current);
    };
  }, [authToken, dispatch, handleMessage, sendSelectedLanguage, sessionId, stopWaveform]);

  /**
   * Start recording. Audio is buffered locally and sent as one
   * complete blob when stopRecording() is called.
   */
  async function startRecording(mode: "customer" | "staff") {
    console.log("startRecording called with mode:", mode);
    modeRef.current = mode;
    chunksRef.current = [];

    if (!navigator.mediaDevices?.getUserMedia) {
      console.warn("navigator.mediaDevices.getUserMedia not supported, using demo mode");
      // No mic — send a single demo turn
      wsRef.current?.send(JSON.stringify({ type: "demo_text", mode }));
      dispatch(setRecording(true));
      return;
    }

    try {
      console.log("Requesting microphone access...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log("Microphone access granted.");
      streamRef.current = stream;
      startWaveform(stream);

      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      // When recording stops, combine all chunks and send once
      recorder.onstop = async () => {
        console.log("Recording stopped. Processing audio chunks...");
        if (recordingAutoStopTimerRef.current) window.clearTimeout(recordingAutoStopTimerRef.current);
        recordingAutoStopTimerRef.current = null;
        stopWaveform();
        stream.getTracks().forEach((t) => t.stop());

        if (chunksRef.current.length === 0) {
          console.warn("No audio chunks recorded.");
          return;
        }
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        console.log("Recorded blob size:", blob.size, "mime:", recorder.mimeType);

        // Convert to WAV for Sarvam compatibility
        const wavBytes = await blobToWav(blob);
        console.log("Converted to WAV, size:", wavBytes.byteLength);

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          console.log("Sending audio to server...");
          // Tell backend which mode this audio belongs to
          wsRef.current.send(JSON.stringify({ type: "audio_meta", mode: modeRef.current }));
          wsRef.current.send(wavBytes);
        } else {
          console.error("WebSocket is not open. ReadyState:", wsRef.current?.readyState);
        }
      };

      recorder.start();          // record the full segment, no timeslice
      recordingAutoStopTimerRef.current = window.setTimeout(() => {
        if (recorder.state !== "inactive") {
          recorder.stop();
          dispatch(setRecording(false));
        }
      }, 24000);
      console.log("MediaRecorder started.");
      dispatch(setRecording(true));
      wsRef.current?.send(JSON.stringify({ type: "start", mode }));
    } catch (err) {
      console.error("Mic permission denied or error:", err);
      // Mic permission denied — single demo turn
      wsRef.current?.send(JSON.stringify({ type: "demo_text", mode }));
      dispatch(setRecording(true));
    }
  }

  function stopRecording(_mode: "customer" | "staff") {
    const recorder = recorderRef.current;
    if (recordingAutoStopTimerRef.current) window.clearTimeout(recordingAutoStopTimerRef.current);
    recordingAutoStopTimerRef.current = null;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();           // triggers onstop → sends audio
    } else {
      // Was running in demo mode (no real mic) — no extra send needed
      stopWaveform();
    }
    dispatch(setRecording(false));
  }

  function replayLast() {
    wsRef.current?.send(JSON.stringify({ type: "replay_last" }));
  }

  function requestSummary() {
    wsRef.current?.send(JSON.stringify({ type: "summarize" }));
  }

  function searchSop(query: string) {
    wsRef.current?.send(JSON.stringify({ type: "sop_search", query }));
  }

  function setLanguage(language: string, code: string) {
    selectedLanguageRef.current = { language, code };
    dispatch(setDetectedLanguage({ language, code }));
    sendSelectedLanguage();
  }

  function updateSessionMetadata(metadata: { customerName?: string }) {
    wsRef.current?.send(JSON.stringify({ type: "update_metadata", ...metadata }));
  }

  // ── Form Interview Functions ──────────────────────────────────────────
  function startFormInterviewWs(formType: string) {
    wsRef.current?.send(JSON.stringify({ type: "start_form", formType }));
  }

  function cancelFormInterviewWs() {
    wsRef.current?.send(JSON.stringify({ type: "cancel_form" }));
  }

  function generateFormPdf() {
    wsRef.current?.send(JSON.stringify({ type: "generate_form_pdf" }));
  }

  return {
    startRecording,
    stopRecording,
    replayLast,
    requestSummary,
    searchSop,
    setLanguage,
    updateSessionMetadata,
    waveformCanvasRef,
    startFormInterview: startFormInterviewWs,
    cancelFormInterview: cancelFormInterviewWs,
    generateFormPdf,
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function base64ToBlob(b64: string, mimeType: string): Blob {
  const bytes = atob(b64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  return new Blob([arr], { type: mimeType });
}

async function playAudioBase64Async(b64: string): Promise<void> {
  try {
    const blob = base64ToBlob(b64, "audio/wav");
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    await new Promise<void>((resolve) => {
      audio.onended = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      audio.play().catch(() => {
        URL.revokeObjectURL(url);
        resolve();
      });
    });
  } catch {
    console.warn("Failed to play audio");
  }
}

/**
 * Convert any browser-recorded blob (webm/ogg) to WAV using AudioContext.
 * This is necessary because Sarvam STT only accepts wav/mp3/flac.
 */
async function blobToWav(blob: Blob): Promise<ArrayBuffer> {
  const arrayBuffer = await blob.arrayBuffer();
  const audioCtx = new AudioContext({ sampleRate: 16000 });

  try {
    const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
    const numChannels = 1;
    const sampleRate = 16000;
    const bitsPerSample = 16;
    const length = audioBuffer.length;

    // Downsample / get mono channel
    const channelData = audioBuffer.getChannelData(0);

    // Build WAV file
    const wavBuffer = new ArrayBuffer(44 + length * 2);
    const view = new DataView(wavBuffer);

    // RIFF header
    writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + length * 2, true);
    writeString(view, 8, "WAVE");

    // fmt chunk
    writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true);               // chunk size
    view.setUint16(20, 1, true);                 // PCM format
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * (bitsPerSample / 8), true);
    view.setUint16(32, numChannels * (bitsPerSample / 8), true);
    view.setUint16(34, bitsPerSample, true);

    // data chunk
    writeString(view, 36, "data");
    view.setUint32(40, length * 2, true);

    // Write PCM samples
    let offset = 44;
    for (let i = 0; i < length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, channelData[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    audioCtx.close();
    return wavBuffer;
  } catch {
    // If decoding fails, send the raw blob bytes as fallback
    audioCtx.close();
    return arrayBuffer;
  }
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}
