"use client";

// FR-27 — speak the search. A microphone button beside the search box, offered only where the
// browser can recognise speech (EC-62). It listens for one request: the words fill the box as
// they are heard, and when the shopper stops, the search runs on them. The box keeps them, so a
// misheard word is put right by typing (EC-64). The microphone is asked for only on the tap.

import { useEffect, useRef, useState } from "react";

import {
  LANGUAGE,
  NOT_HEARD,
  type Recogniser,
  failure,
  recogniserClass,
  transcript,
} from "@/lib/voice";

export default function Voice({
  busy,
  onListening,
  onHearing,
  onHeard,
  onMessage,
}: {
  busy: boolean;
  onListening: (on: boolean) => void;
  onHearing: (text: string) => void;
  onHeard: (text: string) => void;
  onMessage: (message: string | null) => void;
}) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const active = useRef<Recogniser | null>(null);

  useEffect(() => {
    setSupported(recogniserClass() !== null); // after mount: the page is pre-rendered
    return () => active.current?.abort();
  }, []);

  if (!supported) return null;

  const listen = (on: boolean) => {
    setListening(on);
    onListening(on);
  };

  const start = () => {
    const Maker = recogniserClass();
    if (!Maker) return;
    const r = new Maker();
    r.lang = LANGUAGE;
    r.interimResults = true;
    r.continuous = false;
    r.maxAlternatives = 1;
    let heard = "";
    let failed = false;
    r.onresult = (e) => {
      heard = transcript(e);
      onHearing(heard);
    };
    r.onerror = (e) => {
      failed = true;
      onMessage(failure(e.error));
    };
    r.onend = () => {
      active.current = null;
      listen(false);
      if (failed) return;
      // Some recognisers end without marking the last words final; what was heard still counts.
      if (heard) onHeard(heard);
      else onMessage(NOT_HEARD); // EC-63 — it ended with nothing heard
    };
    onMessage(null);
    active.current = r;
    listen(true);
    try {
      r.start();
    } catch {
      active.current = null;
      listen(false);
      onMessage(failure("start"));
    }
  };

  return (
    <button
      type="button"
      className={listening ? "mic listening" : "mic"}
      aria-label={listening ? "Stop listening" : "Speak your search"}
      aria-pressed={listening}
      disabled={busy && !listening}
      onClick={() => {
        if (!listening) return start();
        listen(false); // back at once; the recogniser's end still delivers what was heard
        active.current?.stop();
      }}
    >
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
        <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
        <path
          d="M6 11a6 6 0 0 0 12 0M12 17v4M8.5 21h7"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    </button>
  );
}
