import { useEffect, useRef, useCallback } from "react";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { buildSessionWsUrl } from "../../config/env";
import {
  addTranscript,
  cancelFormInterview,
  mergeEntities,
  setActionChips,
  setComplianceAlert,
  setConnectionStatus,
  setDetectedLanguage,
  setEscalationAlert,
  setListenMode,
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
  | { type: "asr_status"; mode: "customer" | "staff"; status: string; message: string }
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

function buildWsUrl(authToken?: string, sessionId = "demo-session") {
  return buildSessionWsUrl(sessionId, authToken);
}

export function useVoiceSession(authToken?: string, sessionId = "demo-session") {
  const dispatch = useAppDispatch();
  const selectedLanguage = useAppSelector((state) => state.session.language);
  const selectedLanguageCode = useAppSelector((state) => state.session.languageCode);
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const continuousAudioRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadFrameRef = useRef<number | null>(null);
  const recordingUtteranceRef = useRef(false);
  const speechStartedAtRef = useRef(0);
  const lastSpeechAtRef = useRef(0);
  const sendingUtteranceRef = useRef(false);
  const modeRef = useRef<"customer" | "staff">("customer");
  const waveformCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const waveformAudioRef = useRef<AudioContext | null>(null);
  const waveformFrameRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const shouldReconnectRef = useRef(true);
  const selectedLanguageRef = useRef({ language: selectedLanguage, code: selectedLanguageCode });
  const audioPlaybackQueueRef = useRef<Promise<void>>(Promise.resolve());
  const assistantAudioActiveRef = useRef(false);
  const assistantAudioEndedAtRef = useRef(0);

  useEffect(() => {
    selectedLanguageRef.current = { language: selectedLanguage, code: selectedLanguageCode };
  }, [selectedLanguage, selectedLanguageCode]);

  const enqueueAudio = useCallback((audioB64: string) => {
    audioPlaybackQueueRef.current = audioPlaybackQueueRef.current
      .catch(() => { })
      .then(async () => {
        assistantAudioActiveRef.current = true;
        try {
          await playAudioBase64Async(audioB64);
        } finally {
          assistantAudioEndedAtRef.current = performance.now();
          assistantAudioActiveRef.current = false;
        }
      });
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

      case "asr_status":
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
      stopRecording(modeRef.current);
    };
  }, [authToken, dispatch, handleMessage, sendSelectedLanguage, sessionId, stopWaveform]);

  /**
   * Start click-on listening. Voice activity splits speech into utterances,
   * sends each utterance after silence, and keeps the mic active until stopped.
   */
  async function startRecording(mode: "customer" | "staff") {
    if (streamRef.current) return;
    modeRef.current = mode;
    chunksRef.current = [];

    if (!navigator.mediaDevices?.getUserMedia) {
      dispatch(setRecording(false));
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;
      startWaveform(stream);

      const audioCtx = new AudioContext();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 1024;
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      continuousAudioRef.current = audioCtx;
      analyserRef.current = analyser;

      dispatch(setRecording(true));
      wsRef.current?.send(JSON.stringify({ type: "start", mode }));
      runVadLoop();
    } catch (err) {
      console.error("Mic permission denied or error:", err);
      dispatch(setRecording(false));
    }
  }

  function stopRecording(_mode: "customer" | "staff") {
    if (vadFrameRef.current) cancelAnimationFrame(vadFrameRef.current);
    vadFrameRef.current = null;
    const recorderWasActive = Boolean(recorderRef.current && recorderRef.current.state !== "inactive");
    stopUtteranceRecording(true);
    recorderRef.current = null;
    recordingUtteranceRef.current = false;
    sendingUtteranceRef.current = false;
    if (!recorderWasActive) chunksRef.current = [];
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    analyserRef.current = null;
    continuousAudioRef.current?.close().catch(() => { });
    continuousAudioRef.current = null;
    stopWaveform();
    wsRef.current?.send(JSON.stringify({ type: "stop_listening", mode: modeRef.current }));
    dispatch(setRecording(false));
  }

  function runVadLoop() {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const data = new Uint8Array(analyser.fftSize);
    const silenceMs = 1000;
    const minSpeechMs = 500;
    const maxUtteranceMs = 24000;
    const threshold = 0.04;

    const tick = () => {
      if (!streamRef.current || !analyserRef.current) return;

      analyser.getByteTimeDomainData(data);
      const rms = getRms(data);
      const now = performance.now();
      const coolingDownFromAssistant = assistantAudioActiveRef.current || now - assistantAudioEndedAtRef.current < 900;
      const hasSpeech = !coolingDownFromAssistant && !sendingUtteranceRef.current && rms > threshold;

      if (hasSpeech) {
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

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };

    recorder.onstop = async () => {
      recordingUtteranceRef.current = false;
      if (chunksRef.current.length === 0 || sendingUtteranceRef.current) return;

      sendingUtteranceRef.current = true;
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
      chunksRef.current = [];
      const wavBytes = await blobToWav(blob);

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "audio_meta", mode: modeRef.current }));
        wsRef.current.send(wavBytes);
      }

      window.setTimeout(() => {
        sendingUtteranceRef.current = false;
      }, 900);
    };

    recorder.start(250);
  }

  function stopUtteranceRecording(shouldSend: boolean) {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    if (!shouldSend) chunksRef.current = [];
    recorder.stop();
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

function getRms(data: Uint8Array): number {
  let sum = 0;
  for (const value of data) {
    const normalized = (value - 128) / 128;
    sum += normalized * normalized;
  }
  return Math.sqrt(sum / data.length);
}
