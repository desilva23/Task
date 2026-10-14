"""Search — from what the shopper typed to ranked catalogue products (lld.md §8).

Deterministic throughout: classify the query, score with BM25, retry once with fuzzy matching
when the text match is weak, rank by a named precedence of rules, and mark a term ambiguous
when its best matches are too close to call. Every result can say why it ranked where it did.
"""

import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz, process

from config import (
    AMBIGUITY_MARGIN,
    AMBIGUITY_MIN_HITS,
    BM25_B,
    BM25_K1,
    FUZZY_THRESHOLD,
    FUZZY_TRIGGER_SCORE,
    MAX_BATCH_TERMS,
    MAX_QUERY_CHARS,
    MIN_QUERY_CHARS,
    NL_WORD_THRESHOLD,
    SEARCH_LIMIT,
    SUGGESTION_THRESHOLD,
)
from models.domain import Product, StockPosition, Store

STOPWORDS = frozenset(
    "a an the and of for with to in on my me i some something need want do what make making "
    "please get buy any how recipe is it x".split()
)
SPLIT = re.compile(r"[,;\n]|\s+and\s+|\s*\+\s*", re.I)
HARD_SPLIT = re.compile(r"[,;\n+]")
DIGITS = re.compile(r"^\d{8,13}$")
QTY = re.compile(r"^(\d+)\s*(?:x|×)?\s+(.+)$", re.I)
NL_CUE = re.compile(r"\b(for|with|need|want|make|making|something|what|how|recipe)\b", re.I)
DIETARY = {
    "gluten_free": "diet_gluten_free",
    "vegan": "diet_vegan",
    "vegetarian": "diet_vegetarian",
    "halal": "diet_halal",
}


def normalise(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9%.]+", " ", t)  # keep digits, % and . for "500ml", "1.5l"
    tokens = (tok.strip(".") for tok in t.split())
    return [tok for tok in tokens if tok and tok not in STOPWORDS]


def searchable_text(p: Product) -> str:
    return " ".join([p.name, p.brand, p.size, p.aisle_category, *p.synonyms])


# ── classification — lld.md §8.2 ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SearchTerm:
    text: str
    qty: int = 1


def parse_qty(part: str) -> SearchTerm:
    m = QTY.match(part)
    return SearchTerm(m.group(2).strip(), int(m.group(1))) if m else SearchTerm(part)


def _parts(q: str) -> list[str]:
    return [p.strip() for p in SPLIT.split(q) if p.strip()]


def _tidy(raw: str) -> str:
    """Collapse spaces within each line but keep the newlines — they separate items. Control
    characters (a null byte) are dropped, and the length is capped (NFR-06)."""
    raw = "".join(c for c in raw[:MAX_QUERY_CHARS] if c.isprintable() or c == "\n")
    return "\n".join(" ".join(line.split()) for line in raw.splitlines() if line.strip())


def classify(raw: str) -> tuple[str, list[SearchTerm]]:
    q = _tidy(raw)
    if len(q) < MIN_QUERY_CHARS:
        return "too_short", []
    if DIGITS.match(q):
        return "digits", []  # not a product request — there is no barcode entry (EC-10)
    parts = _parts(q)
    if len(parts) > 1:
        return "batch", [parse_qty(p) for p in parts[:MAX_BATCH_TERMS]]  # EC-06
    if len(q.split()) > NL_WORD_THRESHOLD and NL_CUE.search(q):
        return "nl", []
    return "term", [parse_qty(q)]


# ── the index — lld.md §8.1, §8.2a ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class QueryFilter:
    """What the model may say about a request: categories and dietary needs, never a product."""

    department: tuple[str, ...] = ()
    aisle_category: tuple[str, ...] = ()
    dietary_required: tuple[str, ...] = ()
    exclude_allergens: tuple[str, ...] = ()

    def admits(self, p: Product) -> bool:
        if self.department and p.department not in self.department:
            return False
        if self.aisle_category and p.aisle_category not in self.aisle_category:
            return False
        # unknown never satisfies a requirement (constitution Principle II, NFR-03)
        if any(getattr(p, DIETARY[d]) is not True for d in self.dietary_required):
            return False
        if self.exclude_allergens:
            if p.allergens_contains is None:
                return False  # an unrecorded declaration cannot promise an absence
            if set(self.exclude_allergens) & set(p.allergens_contains):
                return False
        return True


@dataclass(frozen=True)
class Scored:
    product: Product
    text_score: float
    method: str  # bm25 · corrected · name

    @property
    def sku(self) -> str:
        return self.product.sku


class SearchIndex:
    def __init__(self, store: Store):
        self.products = sorted(store.products.values(), key=lambda p: p.sku)
        docs = [normalise(searchable_text(p)) for p in self.products]
        self.bm25 = BM25Okapi(docs, k1=BM25_K1, b=BM25_B)
        self.vocab = sorted({tok for doc in docs for tok in doc})
        self.phrases = {
            p.sku: [p.name, *p.synonyms] for p in self.products
        }  # what a shopper might call it
        self.name_tokens = {tok for p in self.products for tok in normalise(p.name)}
        self.categories: dict[str, tuple[str, str]] = {}
        for p in self.products:
            for field_name in ("department", "aisle_category"):
                value = getattr(p, field_name)
                self.categories.setdefault(" ".join(normalise(value)), (field_name, value))

    def _bm25(self, tokens: list[str], filt: QueryFilter | None, method: str) -> list[Scored]:
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        hits = [
            Scored(p, float(s), method)
            for p, s in zip(self.products, scores, strict=True)
            if s > 0 and (filt is None or filt.admits(p))
        ]
        return sorted(hits, key=lambda c: (-c.text_score, c.sku))

    def _correct(self, tokens: list[str]) -> list[str]:
        fixed = []
        for tok in tokens:
            if tok in self.vocab:
                fixed.append(tok)
                continue
            best = process.extractOne(
                tok, self.vocab, scorer=fuzz.ratio, score_cutoff=FUZZY_THRESHOLD
            )
            fixed.append(best[0] if best else tok)
        return fixed

    def _by_name(self, text: str, filt: QueryFilter | None, cutoff: float) -> list[Scored]:
        hits = []
        for p in self.products:
            if filt is not None and not filt.admits(p):
                continue
            score = max(
                fuzz.WRatio(text, phrase, processor=_plain) for phrase in self.phrases[p.sku]
            )
            if score >= cutoff:
                hits.append(Scored(p, score, "name"))
        return sorted(hits, key=lambda c: (-c.text_score, c.sku))

    def search(
        self, text: str, filt: QueryFilter | None = None, limit: int = SEARCH_LIMIT
    ) -> tuple[list[Scored], str | None]:
        """Ranked-by-text candidates, and the corrected query if the fuzzy retry was used."""
        tokens = normalise(text)
        found = self._bm25(tokens, filt, "bm25")
        corrected = None
        if not found or found[0].text_score < FUZZY_TRIGGER_SCORE:  # one retry only (EC-02)
            fixed = self._correct(tokens)
            retry = self._bm25(fixed, filt, "corrected") if fixed != tokens else []
            if retry and (not found or retry[0].text_score > found[0].text_score):
                found, corrected = retry, " ".join(fixed)
            elif not found:
                found = self._by_name(text, filt, FUZZY_THRESHOLD)
                corrected = text if found else None
        return found[:limit], corrected

    def category_of(self, text: str) -> tuple[str, str] | None:
        """EC-09: a department or category that no product is named after."""
        tokens = normalise(text)
        key = " ".join(tokens)
        if key in self.categories and not set(tokens) & self.name_tokens:
            return self.categories[key]
        return None

    def in_category(self, field_name: str, value: str) -> list[Scored]:
        return [
            Scored(p, 0.0, "category") for p in self.products if getattr(p, field_name) == value
        ]

    def one_product_phrase(self, text: str) -> bool:
        """True if a single product's name or synonym contains every word of ``text``."""
        words = set(normalise(text))
        return bool(words) and any(
            words <= set(normalise(phrase))
            for phrases in self.phrases.values()
            for phrase in phrases
        )

    def suggestions(self, text: str, n: int = 3) -> list[str]:
        return [c.product.name for c in self._by_name(text, None, SUGGESTION_THRESHOLD)[:n]]


def _plain(s: str) -> str:
    return " ".join(normalise(s)) or s.lower()


# ── ranking — lld.md §8.3 ───────────────────────────────────────────────────────────────────


def variant_match(product: Product, term: SearchTerm) -> bool:
    """The shopper asked for this size: every token of the size appears, in order."""
    size, words = normalise(product.size), normalise(term.text)
    n = len(size)
    return bool(size) and any(words[i : i + n] == size for i in range(len(words) - n + 1))


Rule = Callable[[Scored, SearchTerm, Mapping[str, StockPosition]], object]
RULES: tuple[tuple[str, Rule], ...] = (
    ("carried here", lambda c, t, s: not s[c.sku].ranged),
    ("in stock", lambda c, t, s: s[c.sku].shelf_qty == 0),
    ("size asked for", lambda c, t, s: not variant_match(c.product, t)),
    ("text match", lambda c, t, s: -round(c.text_score, 9)),
    ("popularity", lambda c, t, s: -c.product.popularity),
    ("own brand", lambda c, t, s: not c.product.own_brand),
)
TIED = "tied — catalogue order"


def _key(c: Scored, term: SearchTerm, stock: Mapping[str, StockPosition]) -> tuple:
    return (*(rule(c, term, stock) for _, rule in RULES), c.sku)


def rank(cands: list[Scored], term: SearchTerm, stock: Mapping[str, StockPosition]) -> list[Scored]:
    """A precedence list a buyer can read, not a weighted sum (lld.md §8.3)."""
    return sorted(cands, key=lambda c: _key(c, term, stock))


def explain(
    ranked: list[Scored], term: SearchTerm, stock: Mapping[str, StockPosition]
) -> list[str | None]:
    """For each result after the first, the first rule separating it from the one above."""
    reasons: list[str | None] = [None] if ranked else []
    for above, below in zip(ranked, ranked[1:], strict=False):
        a, b = _key(above, term, stock), _key(below, term, stock)
        reasons.append(next((RULES[i][0] for i in range(len(RULES)) if a[i] != b[i]), TIED))
    return reasons


def needs_clarification(ranked: list[Scored]) -> bool:
    """lld.md §8.4 — a relative margin, because BM25 scores are unnormalised."""
    if len(ranked) < AMBIGUITY_MIN_HITS:
        return False
    top, second = ranked[0].text_score, ranked[1].text_score
    if top <= 0:
        return False
    return (top - second) / top < AMBIGUITY_MARGIN


# ── a whole query ───────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TermResult:
    term: SearchTerm
    status: str  # resolved · ambiguous · category · unresolved
    candidates: tuple[Scored, ...] = ()  # ranked by the precedence rules
    reasons: tuple[str | None, ...] = ()
    chosen: str | None = None  # the product the shopper named, when the text makes it clear
    category: str | None = None
    corrected: str | None = None
    suggestions: tuple[str, ...] = ()
    duplicate_of: int | None = None


@dataclass(frozen=True)
class QueryResult:
    shape: str
    terms: tuple[TermResult, ...] = ()
    unprocessed: tuple[str, ...] = ()
    message: str | None = None


def resolve(
    term: SearchTerm,
    index: SearchIndex,
    stock: Mapping[str, StockPosition],
    filt: QueryFilter | None = None,
    sentence: bool = False,
) -> TermResult:
    category = index.category_of(term.text) if filt is None else None
    if category:
        field_name, value = category
        ranked = rank(index.in_category(field_name, value), term, stock)
        return TermResult(
            term, "category", tuple(ranked), tuple(explain(ranked, term, stock)), category=value
        )
    found, corrected = index.search(term.text, filt)
    if not found:
        return TermResult(term, "unresolved", suggestions=tuple(index.suggestions(term.text)))
    ranked = rank(found, term, stock)
    # Which product was asked for is a question of text alone: a sold-out or unranged product
    # the shopper named is still the answer, reported as such (EC-04, EC-13). The precedence
    # ranking orders the options and the alternatives.
    by_text = sorted(found, key=lambda c: (-c.text_score, c.sku))
    ambiguous = sentence or needs_clarification(by_text)  # a keyword guess is never confident
    return TermResult(
        term,
        "ambiguous" if ambiguous else "resolved",
        tuple(ranked),
        tuple(explain(ranked, term, stock)),
        chosen=None if ambiguous else by_text[0].sku,
        corrected=corrected,
    )


@dataclass(frozen=True)
class Prepared:
    shape: str
    terms: tuple[SearchTerm, ...]
    overflow: tuple[str, ...] = ()
    message: str | None = None


def prepare(raw: str, index: SearchIndex) -> Prepared:
    """Classify, apply the "and" guard, cap the batch — everything before resolution."""
    shape, terms = classify(raw)
    q = _tidy(raw)
    if shape == "too_short":
        return Prepared(shape, (), message="Type at least two letters of a product name.")
    if shape == "digits":
        return Prepared(
            shape, (), message="That looks like a number — type the product name instead."
        )
    if shape == "batch" and not HARD_SPLIT.search(q) and index.one_product_phrase(q):
        shape, terms = "term", [parse_qty(q)]  # "salt and vinegar crisps" stays whole
    if shape == "nl":
        terms = [SearchTerm(q)]  # keyword fallback; the model reads sentences (Phase 6)
    overflow = tuple(_parts(q)[MAX_BATCH_TERMS:]) if shape == "batch" else ()
    notes = []
    if len(raw) > MAX_QUERY_CHARS:
        notes.append(f"Your search was cut to its first {MAX_QUERY_CHARS} characters.")
    if overflow:
        notes.append(
            f"Only the first {MAX_BATCH_TERMS} items were searched; {len(overflow)} were not."
        )
    return Prepared(shape, tuple(terms), overflow, " ".join(notes) or None)


def search_query(
    raw: str,
    index: SearchIndex,
    stock: Mapping[str, StockPosition],
    filt: QueryFilter | None = None,
) -> QueryResult:
    p = prepare(raw, index)
    results: list[TermResult] = []
    seen: dict[str, int] = {}
    for term in p.terms:
        r = resolve(term, index, stock, filt, sentence=p.shape == "nl")
        if r.status == "resolved":  # EC-07: merge after resolution
            sku = r.chosen
            if sku in seen:
                r = TermResult(**{**r.__dict__, "duplicate_of": seen[sku]})
            seen.setdefault(sku, len(results))
        results.append(r)
    return QueryResult(p.shape, tuple(results), p.overflow, p.message)
