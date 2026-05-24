"""
Background Ambient Sound Service.

Mixes a configurable ambient audio track into TTS responses to make AI agents
sound more natural by adding subtle environmental background noise.

Per-agent configuration is stored in Agent.integrations['backgroundSound']:
  {
    "type": "callcenter" | "office" | "cafe" | "street" | "none",
    "volume": 0.0–1.0   (default: 0.15)
  }

Audio is generated synthetically at module load — no external assets required.
All audio is 16-bit PCM, mono, 16 kHz (same as the VoiceFlow pipeline default).
"""
from __future__ import annotations

import logging
import math
import random
import struct
from typing import Optional

logger = logging.getLogger("voiceflow.background_sound")

_SAMPLE_RATE = 16_000
_CACHE: dict[str, bytes] = {}

# ── Synthetic noise generators ──────────────────────────────────────────────

def _white_noise(samples: int, amplitude: int) -> list[int]:
    return [int(random.gauss(0, amplitude)) for _ in range(samples)]


def _generate_callcenter_pcm(duration_s: float, sr: int) -> bytes:
    """Low-level broadband noise + periodic speech-like bursts at ~1.5 Hz."""
    n = int(sr * duration_s)
    pcm = []
    for i in range(n):
        base = random.gauss(0, 200)
        if math.sin(2 * math.pi * 1.5 * i / sr) > 0.70:
            base += random.gauss(0, 900)
        pcm.append(max(-32_767, min(32_767, int(base))))
    return struct.pack(f"<{n}h", *pcm)


def _generate_office_pcm(duration_s: float, sr: int) -> bytes:
    """Very quiet broadband + occasional keyboard tap bursts."""
    n = int(sr * duration_s)
    pcm = []
    for i in range(n):
        base = random.gauss(0, 90)
        if random.random() < 0.0008:    # ~1 tap per 1250 samples ≈ 12 taps/s
            base += random.gauss(0, 2_500)
        if random.random() < 0.000015:  # rare chair creak
            base += random.gauss(0, 4_000)
        pcm.append(max(-32_767, min(32_767, int(base))))
    return struct.pack(f"<{n}h", *pcm)


def _generate_cafe_pcm(duration_s: float, sr: int) -> bytes:
    """
    Medium broadband + low-frequency music hum (110 Hz) + irregular clatter.
    """
    n = int(sr * duration_s)
    hum_freq = 110.0
    pcm = []
    for i in range(n):
        base = random.gauss(0, 350)
        hum = int(150 * math.sin(2 * math.pi * hum_freq * i / sr))
        if random.random() < 0.0003:   # cup clink
            base += random.gauss(0, 3_000)
        pcm.append(max(-32_767, min(32_767, int(base + hum))))
    return struct.pack(f"<{n}h", *pcm)


def _generate_street_pcm(duration_s: float, sr: int) -> bytes:
    """
    Heavy broadband noise + occasional horn / engine rumble at 80 Hz.
    Suitable for delivery driver / outdoor call scenarios.
    """
    n = int(sr * duration_s)
    pcm = []
    for i in range(n):
        base = random.gauss(0, 600)
        rumble = int(250 * math.sin(2 * math.pi * 80 * i / sr))
        if random.random() < 0.00005:  # rare horn burst
            base += random.gauss(0, 8_000)
        pcm.append(max(-32_767, min(32_767, int(base + rumble))))
    return struct.pack(f"<{n}h", *pcm)


# ── Cache helper ─────────────────────────────────────────────────────────────

def _get_loop(ambient_type: str) -> bytes:
    """Return (cached) 2-second synthetic ambient PCM loop."""
    if ambient_type not in _CACHE:
        generators = {
            "callcenter": _generate_callcenter_pcm,
            "office":     _generate_office_pcm,
            "cafe":       _generate_cafe_pcm,
            "street":     _generate_street_pcm,
        }
        fn = generators.get(ambient_type)
        if fn:
            _CACHE[ambient_type] = fn(2.0, _SAMPLE_RATE)
        else:
            _CACHE[ambient_type] = b"\x00\x00" * (2 * _SAMPLE_RATE)  # silence
    return _CACHE[ambient_type]


# ── Public API ───────────────────────────────────────────────────────────────

def mix_background_into_pcm(
    speech_pcm: bytes,
    ambient_type: str = "office",
    volume: float = 0.15,
    sample_rate: int = 16_000,
) -> bytes:
    """
    Mix background ambient noise into speech PCM.

    Both `speech_pcm` and the ambient track are 16-bit LE mono PCM.
    Returns mixed 16-bit LE PCM of the same length as `speech_pcm`.

    Args:
        speech_pcm:   Raw 16-bit LE PCM bytes from TTS.
        ambient_type: One of "callcenter", "office", "cafe", "street", "none".
        volume:       Ambient volume relative to speech (0.0 = silent, 1.0 = equal).
        sample_rate:  Sample rate — must match the TTS output.
    """
    if ambient_type == "none" or volume <= 0 or not speech_pcm:
        return speech_pcm

    ambient_loop = _get_loop(ambient_type)
    loop_samples = len(ambient_loop) // 2
    speech_samples = len(speech_pcm) // 2

    mixed: list[int] = []
    for i in range(speech_samples):
        s = struct.unpack_from("<h", speech_pcm, i * 2)[0]
        a = struct.unpack_from("<h", ambient_loop, (i % loop_samples) * 2)[0]
        blended = s + int(a * volume)
        mixed.append(max(-32_767, min(32_767, blended)))

    return struct.pack(f"<{speech_samples}h", *mixed)


def get_agent_ambient_config(agent_integrations: dict) -> tuple[str, float]:
    """
    Extract ambient sound config from agent.integrations dict.

    Returns (ambient_type, volume) — defaults to ("none", 0.0).
    """
    cfg = agent_integrations.get("backgroundSound", {}) if agent_integrations else {}
    if not isinstance(cfg, dict):
        return "none", 0.0
    ambient_type = str(cfg.get("type", "none")).lower()
    volume = float(cfg.get("volume", 0.15))
    volume = max(0.0, min(1.0, volume))
    return ambient_type, volume


AMBIENT_TYPES = ["none", "office", "callcenter", "cafe", "street"]
