# Feature Specification: Voice Input (Phase 12)

**Branch**: none — committed to `main` (owner's rule, 2026-10-14) · **Created**: 2026-10-15

**Input**: "implement voice input". Voice had been listed as out of scope; the owner's request
brings it in as FR-27. Proven by AC-30.

## User Scenarios

1. **Given** a browser that can recognise speech, **When** the shopper taps the microphone and
   says "coca cola classic", **Then** the words fill the search box as they are heard, the
   search runs when they stop, and the result is the one typing those words gives (AC-30).
2. **Given** the microphone declined, or the page on plain HTTP, **Then** the page says so in
   one line and typing still works (EC-61).
3. **Given** a browser with no speech recogniser, **Then** no microphone is drawn (EC-62).
4. **Given** silence or only background noise, **Then** "Didn't catch that", and no search
   (EC-63).
5. **Given** a misheard word, **Then** it is in the box to correct by typing (EC-64).

## Requirements

- **P12-R01**: `lib/voice.ts` — find the recogniser, join what was heard, word each failure.
- **P12-R02**: `components/Voice.tsx` — the microphone button; one request per tap, `en-GB`.
- **P12-R03**: The words heard go to `POST /api/search` as typed text. No API, server or model
  change.
- **P12-R04**: No audio is sent to or stored by this system.

## Assumptions

- The browser's own recogniser (Web Speech API) is good enough for product names (A-09). Chrome
  sends the sound to Google; Safari uses Apple's service. Firefox has none, so it gets the typed
  page.
- Server-side transcription (Groq Whisper) was considered and not chosen: it spends the key on
  every utterance and puts shoppers' voices on our side of the line.
