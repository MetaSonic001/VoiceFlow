"""Summarizer wrapper that uses Hugging Face transformers if available,
otherwise falls back to a fast truncation-based compressor.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline
    _HF_AVAILABLE = True
except Exception:
    _HF_AVAILABLE = False


class Summarizer:
    def __init__(self, model_name: str = 'facebook/bart-large-cnn'):
        self.model_name = model_name
        self._pipe = None
        if _HF_AVAILABLE:
            try:
                # instantiate lazily to avoid long startup when not used
                self._pipe = pipeline('summarization', model=self.model_name)
            except Exception:
                logger.exception('Failed to initialize HF summarization pipeline; falling back to truncation')
                self._pipe = None

    def summarize(self, texts: List[str], max_length: int = 120) -> List[str]:
        """Summarize a list of texts. If HF isn't available, perform safe truncation."""
        out = []
        try:
            if _HF_AVAILABLE and self._pipe:
                for t in texts:
                    if not t or not t.strip():
                        out.append("")
                        continue
                    try:
                        s = self._pipe(t, max_length=max_length, truncation=True)
                        summary = s[0]['summary_text'] if isinstance(s, list) and len(s) > 0 and 'summary_text' in s[0] else str(s)
                        out.append(summary)
                    except Exception:
                        logger.exception('HF summarization failed for a chunk; using truncation')
                        out.append(t[:max_length])
            else:
                # Fast fallback: return a truncated preview
                for t in texts:
                    if not t:
                        out.append("")
                    else:
                        txt = t.replace('\n', ' ').replace('\r', ' ').strip()
                        out.append(txt[:max_length])
        except Exception:
            logger.exception('Summarization process failed; returning raw texts')
            out = [ (t or '')[:max_length] for t in texts ]

        return out
