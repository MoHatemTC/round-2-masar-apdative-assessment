// frontend/lib/proctoring.ts
// -----------------------------------------------------------------------------
// Utilities + API wrappers for the AI-Proctoring flow.
// - Quality gate on the client (resolution + brightness)
// - JPEG compression / downscale
// - API wrappers (consent, reference upload, frame batch upload)
// -----------------------------------------------------------------------------

// API base — falls back to localhost:8000 for dev.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ---------- Types -----------------------------------------------------------

export type QualityIssue =
  | "resolution_too_low"
  | "too_dark"
  | "too_bright"
  | "ok";

export interface QualityResult {
  ok: boolean;
  issues: QualityIssue[];
  brightness: number; // 0..255
  width: number;
  height: number;
}

export interface CapturedFrame {
  blob: Blob;                // JPEG blob to upload
  timestamp: number;         // ms since epoch
  question_number?: number;  // undefined for the reference photo
}

// ---------- Quality gate ----------------------------------------------------

const MIN_WIDTH = 480;
const MIN_HEIGHT = 360;
const MIN_BRIGHTNESS = 40;   // out of 255
const MAX_BRIGHTNESS = 235;  // out of 255 (avoid blown-out)

/**
 * Runs a lightweight client-side quality check on a captured frame.
 * Samples pixels for speed (we don't need pixel-perfect analysis).
 */
export function checkFrameQuality(canvas: HTMLCanvasElement): QualityResult {
  const width = canvas.width;
  const height = canvas.height;
  const issues: QualityIssue[] = [];

  if (width < MIN_WIDTH || height < MIN_HEIGHT) {
    issues.push("resolution_too_low");
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return {
      ok: false,
      issues: ["resolution_too_low"],
      brightness: 0,
      width,
      height,
    };
  }

  const step = 16;
  const data = ctx.getImageData(0, 0, width, height).data;
  let total = 0;
  let count = 0;
  for (let i = 0; i < data.length; i += 4 * step) {
    total += 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
    count += 1;
  }
  const brightness = count > 0 ? total / count : 0;

  if (brightness < MIN_BRIGHTNESS) issues.push("too_dark");
  if (brightness > MAX_BRIGHTNESS) issues.push("too_bright");

  return {
    ok: issues.length === 0,
    issues: issues.length === 0 ? ["ok"] : issues,
    brightness,
    width,
    height,
  };
}

export function qualityHint(issues: QualityIssue[]): string {
  if (issues.includes("resolution_too_low"))
    return "The image resolution is too low, please move closer to the camera.";
  if (issues.includes("too_dark"))
    return "The lighting is too low, please move to a brighter place.";
  if (issues.includes("too_bright"))
    return "There is strong lighting behind you, try moving away from the window.";
  return "The image looks good.";
}

// ---------- Compression -----------------------------------------------------

/**
 * Draws a video frame onto a canvas, downscaling so the longest side is
 * <= maxSide, and returns a JPEG blob at the given quality (0..1).
 */
export async function captureJpegFromVideo(
  video: HTMLVideoElement,
  maxSide = 640,
  quality = 0.82,
): Promise<{ blob: Blob; canvas: HTMLCanvasElement }> {
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  const scale = Math.min(1, maxSide / Math.max(vw, vh));
  const width = Math.round(vw * scale);
  const height = Math.round(vh * scale);

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D context unavailable");
  ctx.drawImage(video, 0, 0, width, height);

  const blob: Blob = await new Promise((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("toBlob failed"))),
      "image/jpeg",
      quality,
    );
  });

  return { blob, canvas };
}

// ---------- API wrappers ----------------------------------------------------

export async function recordConsent(
  sessionId: string,
  accepted: boolean,
): Promise<void> {
  const res = await fetch(`${API_BASE}/proctoring/consent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      accepted,
      timestamp: new Date().toISOString(),
    }),
  });
  if (!res.ok) throw new Error(`Consent save failed: ${res.status}`);
}

export async function uploadReferencePhoto(
  sessionId: string,
  blob: Blob,
): Promise<void> {
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("kind", "reference");
  fd.append("file", blob, "reference.jpg");

  const res = await fetch(`${API_BASE}/proctoring/reference`, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Reference upload failed (${res.status}): ${text}`);
  }
}

/**
 * Uploads a batch of frames. NEVER throws — a failed upload must not block or
 * degrade the candidate's assessment (proctoring "hard rule").
 */
export async function uploadFrameBatch(
  sessionId: string,
  frames: CapturedFrame[],
  batchId: string,
): Promise<void> {
  if (frames.length === 0) return;

  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("batch_id", batchId);
  frames.forEach((f, idx) => {
    fd.append(`file_${idx}`, f.blob, `frame_${f.timestamp}.jpg`);
    fd.append(
      `meta_${idx}`,
      JSON.stringify({
        timestamp: f.timestamp,
        question_number: f.question_number ?? null,
      }),
    );
  });

  try {
    const res = await fetch(`${API_BASE}/proctoring/frames`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) {
      // eslint-disable-next-line no-console
      console.warn("Frame batch upload non-OK", res.status, await res.text());
    }
  } catch (e) {
    // Network dropped, backend down, etc. — the candidate must not notice.
    // eslint-disable-next-line no-console
    console.warn("Frame batch upload threw", e);
  }
}

// ---------- Batch-id helper -------------------------------------------------

export function newBatchId(): string {
  // simple client-side unique id; the backend enforces idempotency on this.
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
