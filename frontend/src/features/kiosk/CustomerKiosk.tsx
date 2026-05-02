import { useEffect, useState } from "react";
import { useKioskSession } from "./useKioskSession";

export function CustomerKiosk() {
  // Extract session and token from URL params
  const [params, setParams] = useState({ session: "", token: "" });

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    setParams({
      session: searchParams.get("session") || "demo-session",
      token: searchParams.get("token") || "demo"
    });
  }, []);

  const kioskState = useKioskSession(params.session, params.token);

  if (kioskState.connectionStatus !== "connected" && kioskState.connectionStatus !== "idle") {
    return (
      <div className="bg-surface font-sans text-on-surface min-h-screen flex flex-col items-center justify-center">
        <div className="text-secondary text-h2 animate-pulse">
          Connecting to session...
        </div>
      </div>
    );
  }

  // Display default text if no active question
  const isComplete = kioskState.isComplete;
  const showForm = kioskState.formActive;
  const apiBase = import.meta.env.VITE_VOXASSIST_API_URL ?? "http://localhost:8000";
  const isMarathi = kioskState.languageCode.startsWith("mr");
  const mainPrompt = kioskState.assistantText || (isMarathi ? "VoxAssist मध्ये आपले स्वागत आहे" : "Welcome to VoxAssist");
  const isLongPrompt = mainPrompt.length > 180;
  const subPrompt = kioskState.isSessionActive
    ? kioskState.isSpeaking
      ? isMarathi ? "कृपया ऐका" : "Please listen"
      : kioskState.isListening
        ? isMarathi ? "मी ऐकत आहे" : "I am listening"
        : isMarathi ? "आता बोला" : "You can speak now"
    : isMarathi ? "सुरू करण्यासाठी microphone दाबा" : "Tap the microphone once to begin";

  return (
    <div className="bg-white font-sans text-on-surface min-h-screen flex flex-col relative overflow-hidden">
      {/* Background Subtle Circles */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden opacity-5">
        <div className="absolute top-[-10%] right-[-5%] w-[600px] h-[600px] rounded-full border-[1px] border-primary-container" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[800px] h-[800px] rounded-full border-[1px] border-primary-container" />
      </div>

      {/* Top Banner */}
      <header className="flex justify-between items-center w-full px-12 py-8 fixed top-0 z-50">
        <div className="flex items-center gap-4">
          <span className="text-2xl font-black text-[#002D62]">VoxAssist Frontline</span>
        </div>
        
        {kioskState.language !== "English" && (
          <div className="absolute left-1/2 -translate-x-1/2">
            <div className="bg-secondary-container px-6 py-3 rounded-full flex items-center gap-3 border border-outline-variant/30">
              <span className="material-symbols-outlined text-primary-container">language</span>
              <div className="flex flex-col leading-tight">
                <span className="text-[11px] font-bold tracking-widest text-on-secondary-fixed-variant">
                  We're speaking {kioskState.language} today.
                </span>
              </div>
            </div>
          </div>
        )}
        
        <div className="text-slate-500 font-bold">
          EN / {kioskState.languageCode.split("-")[0].toUpperCase()}
        </div>
      </header>

      {/* Main Content Stage */}
      <main className="flex-grow flex flex-col items-center justify-center px-6 max-w-6xl mx-auto w-full text-center mt-20 mb-40 relative z-10">
        
        {/* Fading Transcript Context */}
        <div className={`mb-12 transition-opacity duration-1000 ${kioskState.lastCustomerTranscriptNative ? 'opacity-40' : 'opacity-0'}`}>
          <div className="flex flex-col items-center">
            <span className="text-h2 text-secondary mb-1">
              {kioskState.lastCustomerTranscriptNative || "..."}
            </span>
            <span className="text-[13px] italic text-secondary">
              ({kioskState.lastCustomerTranscriptEnglish || "..."})
            </span>
          </div>
        </div>

        {/* Center Stage Text Block */}
        <section className="space-y-6">
          {isComplete ? (
            <>
              <h1 className="text-[64px] leading-[1.1] font-extrabold text-primary-container tracking-tight">
                Thank you!
              </h1>
              <p className="text-[32px] font-medium text-outline">
                Your form is complete.
              </p>
            </>
          ) : showForm ? (
            <>
              <h1 className="text-[64px] leading-[1.1] font-extrabold text-primary-container tracking-tight transition-opacity duration-500">
                {kioskState.questionTranslated || "Please wait..."}
              </h1>
              <p className="text-[32px] font-medium text-outline transition-opacity duration-500">
                {kioskState.questionText || "Preparing next question..."}
              </p>
            </>
          ) : kioskState.assistantText ? (
            <>
              <h1 className={`${isLongPrompt ? "max-h-72 overflow-y-auto text-[30px] leading-[1.25]" : "text-[56px] leading-[1.1]"} font-extrabold text-primary-container tracking-tight`}>
                {mainPrompt}
              </h1>
              <p className="text-[28px] font-medium text-outline">
                {subPrompt}
              </p>
            </>
          ) : (
            <>
              <h1 className="text-[48px] leading-[1.1] font-extrabold text-primary-container tracking-tight opacity-50">
                Welcome to VoxAssist
              </h1>
              <p className="text-[24px] font-medium text-outline opacity-50">
                {isMarathi ? "सुरू करण्यासाठी microphone दाबा" : "Tap the microphone once to begin"}
              </p>
            </>
          )}

          {/* AI Thinking Indicator */}
          {kioskState.isSessionActive && !kioskState.isSpeaking && !kioskState.isListening && !kioskState.assistantText && (
            <div className="flex items-center gap-3 mt-4">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-primary-container animate-bounce" style={{animationDelay: '0ms'}} />
                <div className="w-2 h-2 rounded-full bg-primary-container animate-bounce" style={{animationDelay: '150ms'}} />
                <div className="w-2 h-2 rounded-full bg-primary-container animate-bounce" style={{animationDelay: '300ms'}} />
              </div>
              <span className="text-[18px] text-secondary font-medium animate-pulse">
                {isMarathi ? 'AI विचार करत आहे...' : 'AI is thinking...'}
              </span>
            </div>
          )}
        </section>

        {kioskState.lastError && (
          <div className="mt-10 rounded border border-red-200 bg-red-50 px-5 py-3 text-[16px] font-semibold text-red-800">
            {kioskState.lastError}
          </div>
        )}

        {kioskState.sopResult && !isComplete && (
          <section className="mt-8 w-full max-w-4xl rounded-lg border border-secondary-container bg-white/95 p-5 text-left shadow-md">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-secondary flex items-center gap-2">
                  <span className="material-symbols-outlined text-[14px]">verified</span>
                  Trusted Policy
                </div>
                <h2 className="mt-1 text-[20px] font-extrabold leading-6 text-primary-container">
                  {kioskState.sopResult.title}
                </h2>
              </div>
              <div className="flex items-center gap-2">
                {kioskState.sopResult.citations && kioskState.sopResult.citations.length > 0 && (
                  <div className="rounded border border-outline-variant px-2 py-1 text-[11px] font-bold text-outline">
                    {kioskState.sopResult.citations.length} source{kioskState.sopResult.citations.length > 1 ? 's' : ''}
                  </div>
                )}
                {typeof kioskState.sopResult.confidence === "number" && (
                  <div className={`rounded border px-2 py-1 text-[12px] font-bold ${
                    kioskState.sopResult.confidence >= 0.6 ? 'border-green-300 text-green-700 bg-green-50' :
                    kioskState.sopResult.confidence >= 0.3 ? 'border-amber-300 text-amber-700 bg-amber-50' :
                    'border-outline-variant text-secondary'
                  }`}>
                    {Math.round(kioskState.sopResult.confidence * 100)}% match
                  </div>
                )}
              </div>
            </div>
            <p className="mt-3 max-h-64 overflow-y-auto text-[15px] leading-7 text-on-surface-variant">
              {kioskState.sopResult.answer}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] font-bold uppercase tracking-[0.12em] text-outline border-t border-surface-container-high pt-3">
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px]">description</span>
                {kioskState.sopResult.source}
              </span>
              {kioskState.sopResult.effectiveFrom && (
                <span className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-[12px]">calendar_today</span>
                  Effective {kioskState.sopResult.effectiveFrom}
                </span>
              )}
              {kioskState.sopResult.requiresStaffVerification && (
                <span className="flex items-center gap-1 text-amber-600">
                  <span className="material-symbols-outlined text-[12px]">warning</span>
                  Staff verification needed
                </span>
              )}
            </div>
          </section>
        )}

        {isComplete && kioskState.pdfUrl && (
          <a
            href={`${apiBase}${kioskState.pdfUrl}`}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-10 rounded-md bg-primary-container px-8 py-4 text-[18px] font-bold text-white shadow-lg transition-transform active:scale-95"
          >
            View completed form
          </a>
        )}

        {/* Progress Tracking */}
        {showForm && !isComplete && (
          <div className="mt-16 w-full max-w-2xl space-y-4">
            <div className="flex justify-between items-end mb-2">
              <span className="text-[11px] font-bold tracking-widest text-secondary uppercase">
                FORM PROGRESS: FIELD {Math.min(kioskState.filledCount + 1, kioskState.totalFields)} OF {kioskState.totalFields || 1}
              </span>
              <span className="text-[14px] font-medium text-primary-container">
                {Math.round(kioskState.progress)}%
              </span>
            </div>
            {/* Native Tailwind Progress Bar */}
            <div className="h-3 w-full bg-surface-container-high rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary-container rounded-full transition-all duration-500 ease-out"
                style={{ width: `${kioskState.progress}%` }}
              />
            </div>
          </div>
        )}
      </main>

      {/* Footer sticky bar */}
      <footer className={`fixed bottom-0 left-0 w-full z-50 flex flex-col items-center justify-center py-10 px-12 bg-white border-t border-surface-container-high transition-opacity duration-700 ${kioskState.isSessionActive ? 'opacity-100' : 'opacity-70'}`}>
        <div className="flex flex-col items-center gap-6">
          
          <div className="flex items-center gap-8">
            {/* Visualizer Left */}
            <div className="flex items-end gap-1 h-8">
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.0s'}}></div>
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.2s'}}></div>
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.4s'}}></div>
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.1s'}}></div>
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.3s'}}></div>
            </div>
            
            {/* Mic Icon */}
            <button
              type="button"
              aria-label={kioskState.isSessionActive ? "End voice session" : "Start voice session"}
              onClick={() => {
                if (kioskState.isSessionActive) kioskState.stopConversation();
                else kioskState.startConversation();
              }}
              className="relative rounded-full transition-transform active:scale-95"
            >
              {(kioskState.isListening || kioskState.isSpeaking) && (
                <div className="absolute inset-0 bg-primary-container/20 rounded-full animate-ping scale-150"></div>
              )}
              <div className={`w-16 h-16 rounded-full flex items-center justify-center relative z-10 transition-all ${
                kioskState.isSessionActive ? 'bg-primary-container shadow-[0_0_20px_2px_rgba(0,45,98,0.2)]' : 'bg-slate-500 opacity-80'
              }`}>
                <span className="material-symbols-outlined text-white text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  mic
                </span>
              </div>
            </button>
            
            {/* Visualizer Right */}
            <div className="flex items-end gap-1 h-8">
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.3s'}}></div>
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.1s'}}></div>
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.4s'}}></div>
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.2s'}}></div>
              <div className={`w-1 rounded-sm bg-primary-container ${kioskState.isListening ? 'animate-[wave_1s_ease-in-out_infinite]' : 'h-1'} transition-all`} style={{animationDelay: '0.0s'}}></div>
            </div>
          </div>
          
          <div className="text-center">
            <span className={`font-sans font-bold uppercase tracking-widest text-lg text-[#002D62] block ${kioskState.isListening ? 'animate-pulse' : ''}`}>
              {kioskState.isSpeaking ? (isMarathi ? 'AI बोलत आहे' : 'AI Speaking') : kioskState.isListening ? (isMarathi ? 'ऐकत आहे...' : 'Listening...') : kioskState.isSessionActive ? 'Active Session' : 'Tap to Start'}
            </span>
            <span className="text-[13px] text-secondary uppercase tracking-[0.2em] mt-1 block">
              {kioskState.isSpeaking ? (isMarathi ? 'कृपया ऐका' : 'Please listen') : kioskState.isListening ? (isMarathi ? 'कृपया बोला' : 'Please speak') : kioskState.isSessionActive ? (isMarathi ? 'Voice ची वाट पाहत आहे' : 'Waiting for voice') : 'One tap continuous voice'}
            </span>
          </div>
        </div>
        
        <div className="absolute bottom-4 left-12 right-12 flex justify-between opacity-30 text-[10px] font-bold uppercase tracking-widest">
          <div className="flex gap-4">
            <span>Voice Support</span>
            <span>Accessibility</span>
          </div>
          <div>Institutional Bank &copy; 2024</div>
        </div>
      </footer>
    </div>
  );
}
