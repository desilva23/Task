"use client";

// FR-03 — the barcode scan, in its own sheet. The camera starts only when the shopper opens the
// sheet with "Scan a barcode", so nobody is asked for camera permission unless they want to scan. Frames are decoded on the phone; the
// camera stops at the first single read, so a code is looked up once (EC-54). The typed digits
// beside it are the same lookup when the camera is declined, missing or cannot start (EC-48).

import { useEffect, useRef, useState } from "react";

import { NO_BARCODE_YET, NO_CAMERA, choose, codesIn } from "@/lib/scan";

const FRAME_MS = 250;
const HINT_AFTER_MS = 6000; // EC-49 — say what to try once nothing has been read for a while
const MAX_SIDE = 1280;

export default function Scanner({
  onCode,
  busy,
}: {
  onCode: (code: string) => void;
  busy: boolean;
}) {
  const [looking, setLooking] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [digits, setDigits] = useState("");
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!looking) return;
    let stream: MediaStream | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    const canvas = document.createElement("canvas");
    const started = Date.now();

    const stop = () => {
      stopped = true;
      clearTimeout(timer);
      stream?.getTracks().forEach((t) => t.stop());
    };

    const tick = async () => {
      const v = video.current;
      if (stopped || !v) return;
      if (v.readyState >= 2 && v.videoWidth) {
        const scale = Math.min(1, MAX_SIDE / Math.max(v.videoWidth, v.videoHeight));
        canvas.width = Math.round(v.videoWidth * scale);
        canvas.height = Math.round(v.videoHeight * scale);
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        if (ctx) {
          ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
          const { code, message: why } = choose(
            await codesIn(ctx.getImageData(0, 0, canvas.width, canvas.height)),
          );
          if (stopped) return;
          if (code) {
            stop();
            setLooking(false);
            setMessage(null);
            onCode(code);
            return;
          }
          setMessage(why ?? (Date.now() - started > HINT_AFTER_MS ? NO_BARCODE_YET : null));
        }
      }
      timer = setTimeout(tick, FRAME_MS);
    };

    (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setMessage(NO_CAMERA); // no camera, or not a secure context (C-08)
        setLooking(false);
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
      } catch {
        setMessage(NO_CAMERA); // declined, revoked or absent (EC-48)
        setLooking(false);
        return;
      }
      if (stopped) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      if (video.current) {
        video.current.srcObject = stream;
        await video.current.play().catch(() => undefined);
      }
      tick();
    })();

    return stop;
  }, [looking, onCode]);

  const submitDigits = (e: React.FormEvent) => {
    e.preventDefault();
    if (digits.trim()) onCode(digits.trim());
  };

  return (
    <section className="scan" aria-label="Barcode scan">
      <div className="scan-body">
        {looking ? (
          <div className="viewfinder">
            <video ref={video} playsInline muted aria-label="Camera — point it at the barcode" />
            <span className="guide" aria-hidden="true" />
          </div>
        ) : (
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setMessage(null);
              setLooking(true);
            }}
          >
            Scan another barcode
          </button>
        )}
        {message && (
          <p className="callout warn" role="status">
            {message}
          </p>
        )}
        <form onSubmit={submitDigits} className="row">
          <label className="field grow">
            <span>Or type the numbers under the barcode</span>
            <input
              inputMode="numeric"
              autoComplete="off"
              maxLength={20}
              placeholder="13 digits"
              value={digits}
              onChange={(e) => setDigits(e.target.value)}
            />
          </label>
          <button type="submit" disabled={busy}>
            Look up
          </button>
        </form>
      </div>
    </section>
  );
}
