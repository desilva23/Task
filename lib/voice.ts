// Turning speech into the search text, by the browser's own recogniser (hld.md §3.7). Only the
// words reach our server — they are a typed search from there on. Where the browser has no
// recogniser the microphone is not offered at all (EC-62).

export const MIC_BLOCKED =
  "The microphone isn't available here — type what you're looking for instead.";
export const NOT_HEARD = "Didn't catch that — tap the microphone and try again, or type it.";
export const NO_SERVICE =
  "Voice search isn't working right now — type what you're looking for instead.";

export const LANGUAGE = "en-GB";

// The parts of the Web Speech API the page uses. Declared here because browsers still ship it
// under two names, and the prefixed one is not in TypeScript's DOM library.
type Alternative = { transcript: string };
type Result = { isFinal: boolean; length: number; [i: number]: Alternative };
export type Heard = { results: { length: number; [i: number]: Result } };

export interface Recogniser {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((e: Heard) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

type Maker = new () => Recogniser;

/** The browser's recogniser, or null where it has none (Firefox, older browsers). */
export function recogniserClass(): Maker | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: Maker; webkitSpeechRecognition?: Maker };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Everything heard so far, settled or not — the box shows it as it comes. */
export function transcript(e: Heard): string {
  let text = "";
  for (let i = 0; i < e.results.length; i++) text += e.results[i][0]?.transcript ?? "";
  return text.replace(/\s+/g, " ").trim();
}

/** What to tell the shopper when listening fails; null when they stopped it themselves. */
export function failure(code: string): string | null {
  switch (code) {
    case "aborted":
      return null;
    case "no-speech":
      return NOT_HEARD; // EC-63
    case "not-allowed":
    case "service-not-allowed":
    case "audio-capture":
      return MIC_BLOCKED; // declined, no microphone, or plain HTTP (EC-61, C-08)
    default:
      return NO_SERVICE; // network, language unavailable — the recogniser could not run (EC-61)
  }
}
