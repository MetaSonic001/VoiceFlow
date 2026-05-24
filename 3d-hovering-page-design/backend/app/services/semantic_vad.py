"""
Semantic Turn Detection (Semantic VAD) — knows when the caller is really done speaking.

Standard VAD (Voice Activity Detection) uses silence thresholds: if there's >300ms
of silence, the system assumes the turn is over.  This causes two failure modes:
  1. Mid-sentence pauses (user is thinking) → agent interrupts → rude
  2. Short utterances + silence → correct, but feels sluggish

Semantic VAD uses a lightweight transformer model (or rule-based heuristic fallback)
to detect whether the semantic meaning of an utterance appears grammatically/semantically
complete before committing to the end-of-turn signal.

Architecture:
  - Primary: transformers-based sequence classification (distilbert-base, ~66MB CPU)
    model: "typeform/distilbert-base-uncased-mnli" (zero-shot, no fine-tuning needed)
    label: is the sentence complete? YES/NO classification
  - Fallback: rule-based completeness heuristics (punctuation, open clauses)
    (works without any ML library, always available)

Integration:
  from app.services.semantic_vad import is_turn_complete
  complete = await is_turn_complete("I need to transfer money to my account in")
  # → False — semantically incomplete (dangling prepositional phrase)

  complete = await is_turn_complete("What is the interest rate?")
  # → True — complete question
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

logger = logging.getLogger("voiceflow.semantic_vad")

_CLASSIFIER_AVAILABLE = False
_classifier = None
_classifier_lock = asyncio.Lock()


async def _load_classifier() -> Optional[object]:
    """Lazy-load the zero-shot classifier. Thread-safe."""
    global _classifier, _CLASSIFIER_AVAILABLE
    if _classifier is not None:
        return _classifier
    async with _classifier_lock:
        if _classifier is not None:
            return _classifier
        try:
            import asyncio
            loop = asyncio.get_event_loop()

            def _load():
                from transformers import pipeline  # type: ignore
                return pipeline(
                    "zero-shot-classification",
                    model="typeform/distilbert-base-uncased-mnli",
                    device=-1,  # CPU
                )

            clf = await loop.run_in_executor(None, _load)
            _classifier = clf
            _CLASSIFIER_AVAILABLE = True
            logger.info("[semantic_vad] classifier loaded")
        except Exception as exc:
            logger.info("[semantic_vad] classifier unavailable (%s) — using rule-based fallback", exc)
    return _classifier


# ── Rule-based heuristics (no ML dependency) ─────────────────────────────────

_INCOMPLETE_PATTERNS = re.compile(
    r"\b(and|but|because|so|if|when|where|which|that|who|"
    r"however|although|though|unless|until|while|after|before"
    r"|the|a|an|my|your|our|their|this|these|those|to|in|on|at|for|with|by)\s*$",
    re.IGNORECASE,
)

_COMPLETE_ENDINGS = re.compile(
    r"[.?!]$|"
    r"\b(please|thanks|thank you|okay|ok|yes|no|sure|alright|fine|"
    r"goodbye|bye|hang on)\s*[.!?]?$",
    re.IGNORECASE,
)


def _rule_based_complete(text: str) -> bool:
    """
    Heuristic completeness check.
    Returns True if the utterance appears semantically complete.
    """
    text = text.strip()
    if not text:
        return False
    # Incomplete if ends with a dangling conjunction/preposition/article
    if _INCOMPLETE_PATTERNS.search(text):
        return False
    # Very short utterances (1-2 words) are almost always complete responses
    word_count = len(text.split())
    if word_count <= 2:
        return True
    # Complete sentence indicators
    if _COMPLETE_ENDINGS.search(text):
        return True
    # If >= 4 words and no obvious dangling, consider complete
    return word_count >= 4


async def is_turn_complete(
    text: str,
    confidence_threshold: float = 0.65,
    use_ml: bool = True,
) -> bool:
    """
    Determine if the caller's turn is semantically complete.

    Args:
        text: Transcribed text of the current utterance (possibly partial)
        confidence_threshold: ML model confidence required to override rule-based result
        use_ml: Whether to use the ML classifier (set False to force rule-based only)

    Returns:
        True if the turn appears complete and the agent should respond.
    """
    text = (text or "").strip()
    if not text:
        return False

    # Rule-based result (always available, fast)
    rule_result = _rule_based_complete(text)

    if not use_ml:
        return rule_result

    clf = await _load_classifier()
    if clf is None:
        return rule_result

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: clf(
                text[:256],  # classifier has 512 token limit
                candidate_labels=["complete sentence", "incomplete sentence"],
                multi_label=False,
            ),
        )
        top_label = result["labels"][0]
        top_score = result["scores"][0]
        is_complete_ml = top_label == "complete sentence"

        logger.debug(
            "[semantic_vad] ml=%s(%.2f) rule=%s text=%r",
            top_label, top_score, rule_result, text[:50],
        )

        # Only override rule-based if ML is confident enough
        if top_score >= confidence_threshold:
            return is_complete_ml
        return rule_result

    except Exception as exc:
        logger.debug("[semantic_vad] ML inference failed: %s", exc)
        return rule_result


def get_min_silence_ms(text: str) -> int:
    """
    Adaptive silence threshold based on semantic completeness.
    If the utterance looks complete → shorter silence needed before cutting in.
    If incomplete → wait longer, the caller is mid-thought.
    This replaces a fixed 300ms or 500ms silence threshold.
    """
    # Run quick rule-based check (sync, no await) to tune the silence timer
    looks_complete = _rule_based_complete(text) if text else False
    if not text:
        return 500
    word_count = len(text.split())
    if word_count <= 1:
        return 600  # single word — wait longer to see if they continue
    if looks_complete:
        return 250  # complete sentence — respond quickly
    return 500  # incomplete — keep listening
