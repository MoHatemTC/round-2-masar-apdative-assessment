// frontend/components/proctoring/FrameCaptureRecorder.tsx
// -----------------------------------------------------------------------------
// Background frame capture for the Q&A phase.
//
// Contract (from the Week-3 task):
//   * Snapshot the webcam ~every 20s while a question is active.
//   * Downscale to <=640px JPEG and tag with timestamp + question_number.
//   * Show an always-visible recording indicator while active.
//   * Buffer frames locally and upload in background batches (~every 30s, and
//     on question submit).
//   * Capture must run STRICTLY during the Q&A phase — never on intake, report,
//     or admin pages. Halts instantly when isActive flips to false.
//   * A failed upload must NEVER block or slow down the candidate.
//
// Usage:
//   <FrameCaptureRecorder
//     sessionId={sessionId}
//     questionNumber={currentQuestionNumber}
//     isActive={phase === "qa"}
//     flushSignal={submitTick}         // bump to force an immediate upload
//   />
// -----------------------------------------------------------------------------

"use client";

import { useEffect, useRef, useState } from "react";
import {
  captureJpegFromVideo,
  uploadFrameBatch,
  newBatchId,
  type CapturedFrame,
} from "../../lib/proctoring";

const CAPTURE_INTERVAL_MS = 20_000;
const UPLOAD_INTERVAL_MS = 30_000;

interface Props {
  sessionId: string;
  questionNumber: number | null;
  isActive: boolean;
  /** Bump this number (e.g. increment on submit) to force an immediate flush. */
  flushSignal?: number;
}

export default function FrameCaptureRecorder({
  sessionId,
  questionNumber,
  isActive,
  flushSignal,
}: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const bufferRef = useRef<CapturedFrame[]>([]);
  const captureTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const uploadTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const questionNumberRef = useRef<number | null>(questionNumber);

  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string>("");

  // keep the latest questionNumber in a ref so setInterval callback sees it
  useEffect(() => {
    questionNumberRef.current = questionNumber;
  }, [questionNumber]);

  // ---- start / stop camera + timers based on isActive ----------------------
  useEffect(() => {
    if (!isActive) {
      stopEverything();
      // flush anything still buffered on halt (best-effort)
      void flushBufferedFrames();
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setCameraReady(true);

        // Start capture timer.
        captureTimerRef.current = setInterval(captureOne, CAPTURE_INTERVAL_MS);
        // Also capture one immediately so the first frame lands quickly.
        void captureOne();

        // Start upload timer.
        uploadTimerRef.current = setInterval(
          () => void flushBufferedFrames(),
          UPLOAD_INTERVAL_MS,
        );
      } catch (e) {
        setCameraError(
          "Camera unavailable. The assessment will continue without monitoring.",
        );
        // Do NOT throw — the candidate must not be blocked.
      }
    })();

    return () => {
      cancelled = true;
      stopEverything();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive]);

  // ---- flush on external signal (e.g. answer submit) ----------------------
  useEffect(() => {
    if (flushSignal === undefined) return;
    void flushBufferedFrames();
  }, [flushSignal]);

  function stopEverything() {
    if (captureTimerRef.current) {
      clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }
    if (uploadTimerRef.current) {
      clearInterval(uploadTimerRef.current);
      uploadTimerRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraReady(false);
  }

  async function captureOne() {
    if (!videoRef.current || !streamRef.current) return;
    try {
      const { blob } = await captureJpegFromVideo(videoRef.current, 320, 0.7);
      bufferRef.current.push({
        blob,
        timestamp: Date.now(),
        question_number: questionNumberRef.current ?? undefined,
      });
    } catch {
      // Ignore — a single missed frame is fine.
    }
  }

  async function flushBufferedFrames() {
    if (bufferRef.current.length === 0) return;
    const batch = bufferRef.current;
    bufferRef.current = [];
    await uploadFrameBatch(sessionId, batch, newBatchId());
  }

  // ---- render -------------------------------------------------------------
  // The video element is required for the canvas capture pipeline but doesn't
  // need to be shown; the "recording indicator" is what the candidate sees.
  return (
    <>
      <video
        ref={videoRef}
        playsInline
        muted
        style={{ display: "none" }}
      />

      {isActive && (
        <div
          role="status"
          aria-label="Camera monitoring is active"
          className="fixed top-4 right-4 z-50 flex items-center gap-2 bg-black/80 text-white text-xs px-3 py-1.5 rounded-full shadow-lg"
        >
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              cameraReady ? "bg-red-500 animate-pulse" : "bg-gray-400"
            }`}
          />
          <span>{cameraReady ? "Monitoring" : "Camera…"}</span>
        </div>
      )}

      {isActive && cameraError && (
        <div className="fixed top-14 right-4 z-50 bg-amber-50 border border-amber-200 text-amber-900 text-xs px-3 py-2 rounded-md max-w-xs shadow-lg">
          {cameraError}
        </div>
      )}
    </>
  );
}
