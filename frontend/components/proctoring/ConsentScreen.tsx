// frontend/components/proctoring/ConsentScreen.tsx
// -----------------------------------------------------------------------------
// Pre-assessment consent screen.
// -----------------------------------------------------------------------------

"use client";

import { useState } from "react";
import Button from "../ui/Button";

interface Props {
  onAccept: () => Promise<void> | void;
  onDecline: () => Promise<void> | void;
}

export default function ConsentScreen({ onAccept, onDecline }: Props) {
  const [busy, setBusy] = useState(false);

  return (
    <div className="max-w-xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">Camera Monitoring Consent</h1>

      <div className="rounded-lg bg-gray-50 border border-gray-200 p-4 text-sm leading-6 text-gray-700 space-y-3">
        <p>
          During this assessment, your webcam will take periodic snapshots
          (roughly every 20 seconds). These snapshots are analyzed by an AI
          model to verify integrity — for example, that you are the same person
          who started the assessment and that no other people or devices are
          visible.
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Only still images are captured — no video and no audio.</li>
          <li>Images are stored privately and are never shown publicly.</li>
          <li>You can decline. If you decline, you can still take the assessment.</li>
          <li>An always-visible indicator will show while capture is active.</li>
        </ul>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try { await onAccept(); } finally { setBusy(false); }
          }}
          className="flex-1"
        >
          I agree — enable monitoring
        </Button>
        <Button
          variant="secondary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try { await onDecline(); } finally { setBusy(false); }
          }}
          className="flex-1"
        >
          Decline
        </Button>
      </div>

      <p className="text-xs text-gray-500">
        Your choice will be recorded with a timestamp on this session.
      </p>
    </div>
  );
}
