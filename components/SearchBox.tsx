"use client";

// FR-28 — the search box suggests products as the shopper types. A combobox: the list opens
// under the box from two characters, arrow keys move through it, Enter or a tap chooses, Escape
// closes. Choosing puts the product's label in place of the item being typed and runs the
// search. Typing on and pressing Search still searches exactly what was typed.

import { useMemo, useState } from "react";

import type { Suggestion } from "@/lib/api";
import { choose, suggest } from "@/lib/suggest";

export default function SearchBox({
  value,
  products,
  placeholder,
  quiet,
  maxLength,
  onChange,
  onPick,
}: {
  value: string;
  products: Suggestion[];
  placeholder: string;
  quiet: boolean; // while listening, the words come from the microphone — suggest nothing
  maxLength: number;
  onChange: (text: string) => void;
  onPick: (text: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const shown = useMemo(
    () => (open && !quiet ? suggest(products, value) : []),
    [open, quiet, products, value],
  );

  const pick = (p: Suggestion) => {
    setOpen(false);
    setActive(-1);
    (document.activeElement as HTMLElement | null)?.blur(); // show the answer, not the keyboard
    onPick(choose(value, p.label).slice(0, maxLength));
  };

  return (
    <div className="combo">
      <input
        id="q"
        type="search"
        enterKeyHint="search"
        autoComplete="off"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={shown.length > 0}
        aria-controls="suggestions"
        aria-activedescendant={active >= 0 && shown[active] ? `suggestion-${active}` : undefined}
        maxLength={maxLength}
        placeholder={placeholder}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && active < 0) setOpen(false); // searching what was typed
          if (!shown.length) return;
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            const n = shown.length;
            setActive((i) => (e.key === "ArrowDown" ? (i + 1) % n : i <= 0 ? n - 1 : i - 1));
          } else if (e.key === "Enter" && active >= 0 && shown[active]) {
            e.preventDefault(); // the suggestion, not the half-typed word
            pick(shown[active]);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {shown.length > 0 && (
        <ul id="suggestions" role="listbox" aria-label="Suggestions" className="suggestions">
          {shown.map((p, i) => (
            <li
              key={p.sku}
              id={`suggestion-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "on" : undefined}
              // mousedown, not click: the box would blur first and close the list
              onMouseDown={(e) => {
                e.preventDefault();
                pick(p);
              }}
            >
              <span>{p.label}</span>
              {!p.in_stock && <span className="badge out">Sold out</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
