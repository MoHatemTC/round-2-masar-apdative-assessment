"use client";

import { useState, useEffect, useRef } from "react";
import Button from "@/components/ui/Button";
import { Mic, Square, RotateCcw } from "lucide-react";

export interface VoiceQuestion {
  id: string;
  body: string;
  payload: { time_limit_seconds?: number };
}

type SubmitResult =
  | { pregraded: true }
  | { skipped: true }
  | { no_audio: true; typed_answer: string };
  
export interface VoiceRecorderProps {
  question: VoiceQuestion;
  onSubmit: (result: SubmitResult) => void;
  isSubmitting?: boolean;
  sessionId: string;
  questionNumber: number;
}

type RecordState = "idle" | "recording" | "recorded" | "no_mic";

const MIN_RECORDING_MS = 1000;

export default function VoiceRecorder({ question, onSubmit, isSubmitting = false, sessionId, questionNumber }: VoiceRecorderProps) {
  const [recordState, setRecordState] = useState<RecordState>("idle");
  const [recordError, setRecordError] = useState<string | null>(null);
  const [typedFallback, setTypedFallback] = useState("");
  const [checkingExisting, setCheckingExisting] = useState(true);
  const [alreadyAnswered, setAlreadyAnswered] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recordStartRef = useRef<number>(0);
  const finalBlobRef = useRef<Blob | null>(null);   // held in memory only, until submit
  const finalDurationRef = useRef<number>(0);
  const hasSubmittedRef = useRef(false);

  const timeLimit = question.payload.time_limit_seconds ?? 120;
  const [secondsLeft, setSecondsLeft] = useState(timeLimit);
  const hasAutoSubmitted = useRef(false);

  useEffect(() => {
    if (checkingExisting || alreadyAnswered) return;
    if (secondsLeft <= 0) {
        if (!hasAutoSubmitted.current) {
            hasAutoSubmitted.current = true;
            handleTimeUp();
           }
    return;
  }
  const timer = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
  return () => clearTimeout(timer);
}, [secondsLeft, checkingExisting, alreadyAnswered]);

  useEffect(() => {
  async function checkExisting() {
    try {
      const res = await fetch(`/api/sessions/${sessionId}/questions/${questionNumber}/answer`);
      const data = await res.json();
      if (data.exists) {
        setAlreadyAnswered(true);
      }
    } catch {
      // fail open
    } finally {
      setCheckingExisting(false);
    }
  }
  checkExisting();
}, [sessionId, questionNumber]);
  async function handleTimeUp() {
  if (recordState === "recording") {
    await stopRecordingAndWait();
  }
  await submitWhatWeHave(true);
}
  async function startRecording() {
    setRecordError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/mp4";

      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      recordStartRef.current = Date.now();

      recorder.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      recorder.onstop = () => handleStop(recorder.mimeType);

      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecordState("recording");
    } catch {
      setRecordError("Microphone unavailable — you can type your answer instead.");
      setRecordState("no_mic");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  function stopRecordingAndWait(): Promise<void> {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") return resolve();
      recorder.onstop = () => {
        handleStop(recorder.mimeType);
        resolve();
      };
      recorder.stop();
    });
  }

  // Runs entirely client-side — no network call here anymore.
  function handleStop(mimeType: string) {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    const durationMs = Date.now() - recordStartRef.current;
    const blob = new Blob(chunksRef.current, { type: mimeType });

    if (durationMs < MIN_RECORDING_MS || blob.size === 0) {
      setRecordError("Recording was too short — please try again.");
      setRecordState("idle");
      return;
    }

    finalBlobRef.current = blob;
    finalDurationRef.current = durationMs;
    setRecordError(null);
    setRecordState("recorded");
  }

  function handleReRecord() {
    // Nothing was ever uploaded — just discard the in-memory blob and go again.
    finalBlobRef.current = null;
    finalDurationRef.current = 0;
    setRecordError(null);
    setRecordState("idle");
    chunksRef.current = [];
  }

async function postVoiceAnswer(formData: FormData): Promise<{ ok: boolean; detail: string }> {
  const res = await fetch(
    `/api/sessions/${sessionId}/questions/${questionNumber}/voice-answer`,
    { method: "POST", body: formData }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return { ok: false, detail: err.detail ?? "" };
  }

  await res.json();
  return { ok: true, detail: "" };
}

async function submitWhatWeHave(isAutoSubmit = false) {
  if (hasSubmittedRef.current) return;
  hasSubmittedRef.current = true;

  if (!finalBlobRef.current && !typedFallback.trim()) {
    onSubmit({ skipped: true });
    return;
  }

  const formData = new FormData();
  formData.append("duration_ms", String(finalDurationRef.current));
  formData.append("question_id", question.id);

  if (finalBlobRef.current) {
    formData.append("audio", finalBlobRef.current, "answer.webm");
  } else {
    formData.append("typed_answer", typedFallback);
  }

  const result = await postVoiceAnswer(formData);
  if (!result.ok) {
    if (isAutoSubmit) {
      onSubmit({ skipped: true });
      return;
    }
    hasSubmittedRef.current = false;
    setRecordError(result.detail || "Submission failed — please try again.");
    return;
  }

  onSubmit({ pregraded: true });
}

  async function handleSubmit() {
    if (isSubmitting) return;
    await submitWhatWeHave();
  }
  
  async function handleSkip() {
  if (isSubmitting || hasSubmittedRef.current) return;
  hasSubmittedRef.current = true;

  const formData = new FormData();
  formData.append("duration_ms", "0");
  formData.append("question_id", question.id);
  formData.append("skipped", "true");

  const result = await postVoiceAnswer(formData);
  if (!result.ok) {
    hasSubmittedRef.current = false;
    setRecordError(result.detail || "Skip failed — please try again.");
    return;
  }

  onSubmit({ pregraded: true });
}

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const isUrgent = secondsLeft <= 10;
  const isWarning = secondsLeft <= 30 && secondsLeft > 10;

  if (checkingExisting) {
    return <div className="text-sm text-muted-foreground">Loading…</div>;
  }

  if (alreadyAnswered) {
    return (
      <div className="w-full max-w-xl mx-auto p-5 sm:p-7 rounded-2xl bg-card border border-border shadow-md">
        <p className="text-sm text-muted-foreground">
          This question has already been answered. Moving to the next question…
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-xl mx-auto p-5 sm:p-7 rounded-2xl bg-card border border-border shadow-md">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-5">
        <h2 className="text-lg sm:text-xl font-semibold text-foreground leading-snug">{question.body}</h2>
        <span
          className={[
            "inline-flex items-center shrink-0 px-3 py-1.5 rounded-full text-sm font-mono font-semibold tabular-nums",
            isUrgent ? "bg-destructive/15 text-destructive ring-1 ring-destructive/40 animate-pulse"
              : isWarning ? "bg-warning/15 text-warning ring-1 ring-warning/40"
              : "bg-muted text-muted-foreground ring-1 ring-border",
          ].join(" ")}
          aria-live="polite"
        >
          {minutes}:{seconds.toString().padStart(2, "0")}
        </span>
      </div>

      {recordError && <p className="text-sm text-destructive mb-3">{recordError}</p>}

      {recordState !== "no_mic" ? (
        <div className="mb-5 flex items-center gap-3">
            {recordState === "idle" && (
            <Button
              variant="secondary"
              onClick={startRecording}
              disabled={isSubmitting}
              className="!bg-[#dc2626] !text-white !border-[#dc2626] hover:!bg-[#b91c1c]"
            >
              <Mic className="w-4 h-4 mr-1.5" /> Record answer
            </Button>
          )}
          {recordState === "recording" && (
            <Button
              variant="primary"
              onClick={stopRecording}
              className="!bg-[#dc2626] !text-white hover:!bg-[#b91c1c]"
            >
              <Square className="w-4 h-4 mr-1.5" fill="white" /> Stop
            </Button>
          )}
          {recordState === "recorded" && (
            <>
              <span className="text-sm text-muted-foreground">Recording ready.</span>
              <Button
                variant="secondary"
                onClick={handleReRecord}
                disabled={isSubmitting}
                className="!bg-[#dc2626] !text-white !border-[#dc2626] hover:!bg-[#b91c1c]"
              >
                <RotateCcw className="w-4 h-4 mr-1.5" /> Re-record
              </Button>
            </>
          )}
        </div>
      ) : (
        <textarea
          className="w-full border rounded p-2 text-sm mb-5"
          rows={6}
          value={typedFallback}
          onChange={(e) => setTypedFallback(e.target.value)}
          placeholder="Type your answer here..."
        />
      )}

      <div className="flex flex-col-reverse sm:flex-row gap-3 pt-1">
        <Button variant="secondary" onClick={handleSkip} disabled={isSubmitting} className="w-full sm:w-auto">
         Skip
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting || (recordState !== "recorded" && recordState !== "no_mic") || (recordState === "no_mic" && !typedFallback.trim())}
          className="w-full sm:w-auto sm:ml-auto"
        >
          {isSubmitting ? "Submitting…" : "Submit Answer"}
        </Button>
      </div>
    </div>
  );
}
