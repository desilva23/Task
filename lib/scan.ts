// Reading a barcode from camera frames, on the phone (hld.md §3.5). Only the digits leave the
// device; the server checks them again. Retail symbologies only — a QR code is not a product.
import { prepareZXingModule, readBarcodes } from "zxing-wasm/reader";

export const NO_BARCODE_YET =
  "No barcode read yet. Hold the barcode flat and close enough to fill the frame, in good light — or type the numbers under it.";
export const SEVERAL =
  "There's more than one barcode in view — scan one product at a time.";
export const NO_CAMERA =
  "The camera isn't available here — type the numbers under the barcode instead.";

let prepared = false;

function prepare() {
  if (prepared) return;
  prepareZXingModule({
    overrides: {
      locateFile: (path: string, prefix: string) =>
        path.endsWith(".wasm") ? `/${path}` : prefix + path, // our copy, not a CDN
    },
  });
  prepared = true;
}

/** The distinct product codes in one frame. */
export async function codesIn(frame: ImageData): Promise<string[]> {
  prepare();
  const found = await readBarcodes(frame, {
    formats: ["EAN13", "EAN8", "UPCA"],
    tryHarder: true,
    maxNumberOfSymbols: 4,
  });
  return [...new Set(found.filter((r) => r.isValid).map((r) => r.text.trim()))];
}

/** One code is looked up; none, or several, is never guessed between (EC-49, EC-53). */
export function choose(codes: string[]): { code: string | null; message: string | null } {
  if (codes.length === 1) return { code: codes[0], message: null };
  return { code: null, message: codes.length ? SEVERAL : null };
}
