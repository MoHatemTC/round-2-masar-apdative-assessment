// frontend/components/proctoring/ReferencePhotoCapture.tsx
// -----------------------------------------------------------------------------
// Reference photo capture flow:
//   live preview  ->  capture  ->  quality check  ->  retake / confirm  ->  upload
//
// Uploading the confirmed photo is the ONLY blocking pre-assessment step.
// -----------------------------------------------------------------------------

"use client";

import { useEffect, useRef, useState } from "react";
import {
  captureJpegFromVideo,
  checkFrameQuality,
  qualityHint,
  uploadReferencePhoto,
  type QualityResult,
} from "../../lib/proctoring";

interface Props {
  sessionId: string;
  onConfirmed: () => void;
}

type Phase = "loading" | "preview" | "review" | "uploading" | "error";

export default function ReferencePhotoCapture({ sessionId, onConfirmed }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [captured, setCaptured] = useState<{
    blob: Blob;
    dataUrl: string;
    quality: QualityResult;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
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
        setPhase("preview");
      } catch {
        setErrorMsg("Cannot access the webcam. Please allow camera permission and reload.");
        setPhase("error");
      }
    })();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, []);

  async function handleCapture() {
    if (!videoRef.current) return;
    const { blob, canvas } = await captureJpegFromVideo(videoRef.current, 640, 0.85);
    const quality = checkFrameQuality(canvas);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    setCaptured({ blob, dataUrl, quality });
    setPhase("review");
  }

  function handleRetake() {
    setCaptured(null);
    setPhase("preview");
  }

  async function handleConfirm() {
    if (!captured) return;
    setPhase("uploading");
    try {
      await uploadReferencePhoto(sessionId, captured.blob);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      onConfirmed();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed. Please try again.";
      setErrorMsg(msg);
      setPhase("error");
    }
  }

  if (phase === "error") {
    return (
      <div className="max-w-xl mx-auto p-6 space-y-4">
        <h2 className="text-xl font-bold">Camera error</h2>
        <p className="text-red-600 text-sm">{errorMsg}</p>
        <button
          onClick={() => window.location.reload()}
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-md px-4 py-2"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto p-6 space-y-4">
      <h2 className="text-xl font-bold">Take your reference photo</h2>
      <p className="text-sm text-gray-600">
        Look at the camera. Make sure your face is clearly visible and well-lit.
      </p>

      <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
        {phase === "review" && captured ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={captured.dataUrl}
            alt="captured reference"
            className="w-full h-full object-cover"
          />
        ) : (
          <video
            ref={videoRef}
            playsInline
            muted
            className="w-full h-full object-cover"
          />
        )}
        {phase === "loading" && (
          <div className="absolute inset-0 grid place-items-center text-white text-sm">
            Loading camera...
          </div>
        )}
      </div>

      {phase === "review" && captured && (
        <div
          className={`text-sm rounded-md p-3 ${
            captured.quality.ok
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-amber-50 text-amber-800 border border-amber-200"
          }`}
        >
          {qualityHint(captured.quality.issues)}
        </div>
      )}

      <div className="flex gap-3">
        {phase === "preview" && (
          <button
            onClick={handleCapture}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white rounded-md py-2.5 font-medium"
          >
            Capture
          </button>
        )}

        {phase === "review" && captured && (
          <>
            <button
              onClick={handleRetake}
              className="flex-1 bg-white border border-gray-300 hover:bg-gray-50 text-gray-800 rounded-md py-2.5 font-medium"
            >
              Retake
            </button>
            <button
              onClick={handleConfirm}
              disabled={!captured.quality.ok}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-md py-2.5 font-medium"
            >
              Confirm & continue
            </button>
          </>
        )}

        {phase === "uploading" && (
          <div className="flex-1 text-center py-2.5 text-sm text-gray-600">
            Uploading...
          </div>
        )}
      </div>
    </div>
  );
}
