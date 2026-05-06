"""
Voicemail / Answering-Machine Detection (AMD) service.

Layer 1 — Twilio AMD  : authoritative when `AnsweredBy` is present.
Layer 2 — Audio analysis: 440-480 Hz beep detection + energy-ramp pattern.
Layer 3 — Transcript patterns: common voicemail phrases matched with regex.

Usage:
    from app.services.voicemail_detector import VoicemailDetector
    detector = VoicemailDetector()
    result = await detector.detect(pcm_bytes, transcript="please leave a message")
    # result.is_voicemail, result.confidence, result.method
"""
from __future__ import annotations

import re
import struct
import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("voiceflow.voicemail_detector")

# ── Transcript-pattern layer ─────────────────────────────────────────────────

_VM_PATTERNS = re.compile(
    r"(leave\s+a\s+(message|voicemail)|"
    r"not\s+available\s+(right\s+now|at\s+the\s+moment)|"
    r"please\s+leave\s+(a\s+)?message|"
    r"after\s+the\s+(tone|beep)|"
    r"press\s+\d+\s+to\s+leave|"
    r"your\s+call\s+has\s+been\s+forwarded|"
    r"no\s+one\s+is\s+available|"
    r"cannot\s+(take|answer)\s+(your|the)\s+call|"
    r"at\s+the\s+sound\s+of\s+the\s+(tone|beep))",
    re.IGNORECASE,
)


@dataclass
class VMDetectionResult:
    is_voicemail: bool
    confidence: float        # 0.0 – 1.0
    method: str              # "twilio_amd" | "audio_beep" | "transcript" | "none"
    reasons: list[str] = field(default_factory=list)


class VoicemailDetector:
    """
    Multi-layer voicemail detector.

    Meant to be called:
      1. After Twilio AMD result arrives via `detect_from_twilio(answered_by)`
      2. Optionally as a fallback with raw PCM audio + transcript
    """

    # ── Layer 1 — Twilio AMD ──────────────────────────────────────────────────

    @staticmethod
    def detect_from_twilio(answered_by: str) -> VMDetectionResult:
        """
        Parse Twilio's AnsweredBy field.

        Twilio values: human | machine_start | machine_end_beep |
                       machine_end_silence | machine_end_other | fax | unknown
        """
        answered_by = (answered_by or "").lower().strip()
        if answered_by.startswith("machine") or answered_by == "fax":
            return VMDetectionResult(
                is_voicemail=True,
                confidence=0.97,
                method="twilio_amd",
                reasons=[f"AnsweredBy={answered_by}"],
            )
        if answered_by == "human":
            return VMDetectionResult(
                is_voicemail=False,
                confidence=0.97,
                method="twilio_amd",
                reasons=[f"AnsweredBy=human"],
            )
        # unknown — fall through to audio/transcript analysis
        return VMDetectionResult(
            is_voicemail=False,
            confidence=0.5,
            method="none",
            reasons=[f"AnsweredBy={answered_by} (inconclusive)"],
        )

    # ── Layer 2 — Audio analysis (440-480 Hz beep + energy ramp) ─────────────

    @staticmethod
    def detect_from_audio(pcm_bytes: bytes, sample_rate: int = 16000) -> VMDetectionResult:
        """
        Detect voicemail beep signature in 16-bit mono PCM audio.

        Two signals:
          A. DFT bin energy at 440-480 Hz exceeds threshold → likely beep.
          B. Sustained silence followed by energy spike (leaves-message pattern).
        """
        if not pcm_bytes or len(pcm_bytes) < 2:
            return VMDetectionResult(is_voicemail=False, confidence=0.0, method="none")

        n = len(pcm_bytes) // 2
        samples = struct.unpack(f"<{n}h", pcm_bytes[:n * 2])

        # --- A. Goertzel beep detection (440-480 Hz window) ---
        beep_detected = False
        window_size = min(n, int(sample_rate * 0.1))  # 100ms window
        for target_hz in (440, 460, 480):
            k = int(0.5 + window_size * target_hz / sample_rate)
            omega = 2 * math.pi * k / window_size
            coeff = 2 * math.cos(omega)
            q1 = q2 = 0.0
            for s in samples[:window_size]:
                q0 = coeff * q1 - q2 + s
                q2, q1 = q1, q0
            power = math.sqrt(q1 * q1 + q2 * q2 - coeff * q1 * q2)
            total_rms = math.sqrt(sum(s * s for s in samples[:window_size]) / window_size) or 1
            if power / total_rms > 0.6:
                beep_detected = True
                break

        # --- B. Silence-then-energy ramp (typical voicemail greeting pattern) ---
        frame = sample_rate // 10  # 100ms frames
        rms_frames = []
        for i in range(0, min(n, sample_rate * 10), frame):  # check first 10 seconds
            chunk = samples[i: i + frame]
            if not chunk:
                break
            rms_frames.append(math.sqrt(sum(s * s for s in chunk) / len(chunk)))

        energy_ramp = False
        if len(rms_frames) >= 6:
            first_half = sum(rms_frames[:3]) / 3
            last_half = sum(rms_frames[-3:]) / 3
            # silence up front, speaking at end — typical recorded greeting pattern
            if first_half < 50 and last_half > 200:
                energy_ramp = True

        if beep_detected and energy_ramp:
            return VMDetectionResult(is_voicemail=True, confidence=0.85, method="audio_beep",
                                     reasons=["440-480Hz beep detected", "silence+energy ramp"])
        if beep_detected:
            return VMDetectionResult(is_voicemail=True, confidence=0.70, method="audio_beep",
                                     reasons=["440-480Hz beep detected"])
        if energy_ramp:
            return VMDetectionResult(is_voicemail=False, confidence=0.4, method="none",
                                     reasons=["energy ramp only — not conclusive"])
        return VMDetectionResult(is_voicemail=False, confidence=0.2, method="none")

    # ── Layer 3 — Transcript patterns ────────────────────────────────────────

    @staticmethod
    def detect_from_transcript(transcript: str) -> VMDetectionResult:
        """Match common voicemail phrases in the speech-to-text transcript."""
        if not transcript:
            return VMDetectionResult(is_voicemail=False, confidence=0.0, method="none")
        match = _VM_PATTERNS.search(transcript)
        if match:
            return VMDetectionResult(
                is_voicemail=True,
                confidence=0.88,
                method="transcript",
                reasons=[f"matched phrase: '{match.group(0)}'"],
            )
        return VMDetectionResult(is_voicemail=False, confidence=0.2, method="none")

    # ── Combined detection ────────────────────────────────────────────────────

    async def detect(
        self,
        pcm_bytes: Optional[bytes] = None,
        transcript: Optional[str] = None,
        answered_by: Optional[str] = None,
    ) -> VMDetectionResult:
        """
        Run all applicable layers and return the highest-confidence result.

        Priority: Twilio AMD > audio analysis > transcript patterns.
        """
        results: list[VMDetectionResult] = []

        if answered_by:
            r = self.detect_from_twilio(answered_by)
            if r.confidence >= 0.9:
                return r  # Authoritative — no need for fallbacks
            results.append(r)

        if pcm_bytes:
            results.append(self.detect_from_audio(pcm_bytes))

        if transcript:
            results.append(self.detect_from_transcript(transcript))

        if not results:
            return VMDetectionResult(is_voicemail=False, confidence=0.0, method="none")

        # Return highest confidence
        return max(results, key=lambda r: r.confidence)


# Module-level singleton
voicemail_detector = VoicemailDetector()
