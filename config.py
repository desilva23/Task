"""Every threshold and cap in one place (lld.md §14). Each number names the case it serves."""

# search — lld.md §8
MIN_QUERY_CHARS = 2  # EC-01
MAX_BATCH_TERMS = 30  # EC-06
NL_WORD_THRESHOLD = 3  # measured live: 'something for a headache' (4 words) must reach the model
BM25_K1, BM25_B = 1.2, 0.5
SEARCH_LIMIT = 10
FUZZY_THRESHOLD = 75  # rapidfuzz ratio — 75 measured on the query set: every typo, no new noise
FUZZY_TRIGGER_SCORE = 2.0  # BM25 below this triggers the fuzzy retry (EC-02)
SUGGESTION_THRESHOLD = 60  # nearest names offered when nothing matches (EC-03)
AMBIGUITY_MIN_HITS = 3
AMBIGUITY_MARGIN = 0.15  # §8.4

# graph — lld.md §5, §6
MAX_CLARIFY_ROUNDS = 2  # EC-35
THREAD_TTL_MINUTES = 30  # EC-34 — abandoned interrupts
ROUND_TOLERANCE_M = 0.5  # §9 verify — rounding slack on a distance claim

# models — GroqCloud (C-06). Strict structured output only on the gpt-oss models;
# re-verify these IDs before Phase 6.
MODEL_TIMEOUT_S = 6
MODEL_UNDERSTAND = "openai/gpt-oss-20b"
MODEL_SUBSTITUTE = "openai/gpt-oss-120b"
MODEL_DESCRIBE = "openai/gpt-oss-20b"
MODEL_MAX_TOKENS = 1024  # per call; reasoning tokens count against it
MODEL_REASONING_EFFORT = "low"  # short tasks; reasoning still counts against the cap
MODEL_CALLS_PER_SESSION = 60  # public-deployment guard — then fallbacks only
