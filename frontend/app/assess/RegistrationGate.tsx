"use client";

import { useState, useRef, useEffect } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

type CameraStatus = "idle" | "checking" | "granted" | "denied";

export interface RegistrationGateProps {
  assessmentTitle: string;
  onComplete: (name: string, email: string) => void;
}

export default function RegistrationGate({ assessmentTitle, onComplete }: RegistrationGateProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus>("idle");
  const [cameraError, setCameraError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Attach the stream to the <video> element once it's actually mounted —
  // the element only renders after cameraStatus flips to "granted", so this
  // can't be done synchronously inside checkCamera() itself.
  useEffect(() => {
    if (cameraStatus === "granted" && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraStatus]);

  useEffect(() => {
    // This is a one-time check, not continuous proctoring capture — release
    // the camera the moment this gate is left, whichever way that happens.
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  async function checkCamera() {
    setCameraError(null);
    setCameraStatus("checking");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      setCameraStatus("granted");
    } catch {
      setCameraStatus("denied");
      setCameraError(
        "Camera access is required for this proctored assessment. Please allow camera access and try again."
      );
    }
  }

  function handleContinue() {
    if (!name.trim()) {
      setFormError("Please enter your full name.");
      return;
    }
    const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    if (!emailOk) {
      setFormError("Please enter a valid email address.");
      return;
    }
    if (cameraStatus !== "granted") {
      setFormError("Please complete the camera check before continuing.");
      return;
    }
    setFormError(null);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    onComplete(name.trim(), email.trim());
  }

  return (
    <main className="max-w-2xl mx-auto p-8">
      <Card className="flex flex-col gap-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Register for: {assessmentTitle}
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Please confirm your details before starting.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Full name
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full border rounded p-2 text-sm"
              placeholder="Jane Doe"
            />
          </label>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full border rounded p-2 text-sm"
              placeholder="jane@example.com"
            />
          </label>
        </div>

        <div className="rounded-md bg-gray-100 dark:bg-neutral-800 p-4">
          <h3 className="font-medium text-gray-900 dark:text-gray-100">Proctoring rules</h3>
          <ul className="mt-2 text-sm text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
            <li>This assessment is proctored — your camera will be used to verify it's you.</li>
            <li>Stay visible in frame and remain alone in the room for the duration of the exam.</li>
            <li>Do not use additional devices, notes, or outside help unless explicitly permitted.</li>
            <li>Leaving the assessment tab or losing camera access may be flagged for review.</li>
          </ul>
        </div>

        <div className="flex flex-col gap-3">
          <h3 className="font-medium text-gray-900 dark:text-gray-100">Camera check</h3>
          {cameraStatus === "granted" ? (
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full max-w-xs rounded-md border border-gray-300 dark:border-neutral-700"
            />
          ) : (
            <div className="w-full max-w-xs h-40 rounded-md border border-dashed border-gray-300 dark:border-neutral-700 flex items-center justify-center text-sm text-gray-500">
              No camera preview yet
            </div>
          )}
          {cameraError && <p className="text-sm text-red-600">{cameraError}</p>}
          <Button
            variant="secondary"
            onClick={checkCamera}
            disabled={cameraStatus === "checking" || cameraStatus === "granted"}
            className="w-fit"
          >
            {cameraStatus === "granted"
              ? "Camera OK"
              : cameraStatus === "checking"
              ? "Requesting access…"
              : "Check camera"}
          </Button>
        </div>

        {formError && <p className="text-sm text-red-600">{formError}</p>}

        <Button onClick={handleContinue} disabled={cameraStatus !== "granted"}>
          Continue
        </Button>
      </Card>
    </main>
  );
}