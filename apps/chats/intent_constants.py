from __future__ import annotations

from typing import Final

# Intents returned by the LLM.
INTENT_TRANSACTION_BATCH: Final[str] = "transaction_batch"
INTENT_FINANCIAL_QUESTION: Final[str] = "financial_question"
INTENT_GREETING: Final[str] = "greeting"
INTENT_UNKNOWN: Final[str] = "unknown"

ALL_INTENTS: Final[tuple[str, ...]] = (
    INTENT_TRANSACTION_BATCH,
    INTENT_FINANCIAL_QUESTION,
    INTENT_GREETING,
    INTENT_UNKNOWN,
)

NON_TRANSACTION_INTENTS: Final[tuple[str, ...]] = (
    INTENT_FINANCIAL_QUESTION,
    INTENT_GREETING,
    INTENT_UNKNOWN,
)

# Rejected action reasons returned by the LLM.
REJECTED_ACTION_REASONS: Final[tuple[str, ...]] = (
    "missing_amount",
    "ambiguous_amount",
    "ambiguous_time",
    "category_not_found",
    "unclear_transaction",
)


# Optional reasons attached when returning intent=unknown.
UNKNOWN_REASON_OTHER_PERSON: Final[str] = "other_person_transaction"

UNKNOWN_REASONS: Final[tuple[str, ...]] = (UNKNOWN_REASON_OTHER_PERSON,)
