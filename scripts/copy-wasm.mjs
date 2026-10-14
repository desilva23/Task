// The barcode decoder's WebAssembly, served from our own origin rather than a CDN (hld.md §3.5).
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("public", { recursive: true });
copyFileSync("node_modules/zxing-wasm/dist/reader/zxing_reader.wasm", "public/zxing_reader.wasm");
