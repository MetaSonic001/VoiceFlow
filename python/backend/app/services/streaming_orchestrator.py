"""
Streaming Orchestrator — Patent Claims 8, 12.

Coordinates the real-time voice pipeline:
  Listening (VAD) → STT → Thinking (RAG) → Speaking (TTS) → Listening …

Yields typed event dicts to the caller (e.g., Twilio Media Streams WS handler):

  {"type": "state",  "state": "listening"}
  {"type": "text",   "content": "<transcript>"}
  {"type": "state",  "state": "thinking"}
  {"type": "state",  "state": "speaking"}
  {"type": "audio",  "bytes": b"..."}   # 160-byte μ-law chunks
  {"type": "interrupt"}
  {"type": "done"}                       # sent when audio_input is exhausted
"""
from __future__ import annotations

import asyncio
import logging
import struct
from collections.abc import AsyncGenerator
from typing import Any

from app.services.call_state import CallState, CallStateManager

logger = logging.getLogger("voiceflow.orchestrator")

# ── VAD / interruption constants ─────────────────────────────────────────────

# PCM energy below this = silence (16-bit RMS)
_SILENCE_RMS_THRESHOLD: float = 50.0
# PCM energy above this while SPEAKING = barge-in
_INTERRUPT_RMS_THRESHOLD: float = 300.0
# Consecutive silence frames before end-of-utterance (~480 ms at 20 ms/frame)
_SILENCE_FRAMES_THRESHOLD: int = 24
# 20ms of 8kHz μ-law = 160 bytes per chunk
_FRAME_BYTES: int = 160
# Max buffered PCM frames in internal queue
_AUDIO_QUEUE_MAXSIZE: int = 512


def _pcm_rms(pcm_bytes: bytes) -> float:
    """Compute root-mean-square energy of 16-bit little-endian PCM."""
    n = len(pcm_bytes) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm_bytes)
    return (sum(s * s for s in samples) / n) ** 0.5


class StreamingOrchestrator:
    """
    Coordinates STT → LLM/RAG → TTS pipeline with real-time interruption support.

    Usage::

        orch = StreamingOrchestrator(stt_service, tts_router, rag_service, call_state_manager)
        async for event in orch.run_pipeline(audio_gen, agent, tenant, call_sid, session_id):
            if event["type"] == "audio":
                ...  # send to Twilio
    """

    def __init__(
        self,
        stt_service: Any,
        tts_router: Any,
        rag_service: Any,
        call_state_manager: CallStateManager,
    ) -> None:
        self.stt = stt_service
        self.tts = tts_router
        self.rag = rag_service
        self.state = call_state_manager

    # ── Public pipeline entry-point ──────────────────────────────────────────

    async def run_pipeline(
        self,
        audio_input: AsyncGenerator[bytes, None],
        agent: Any,     # app.models.Agent
        tenant: Any,    # app.models.Tenant
        call_sid: str,
        session_id: str,
    ) -> AsyncGenerator[dict, None]:
        """
        Main async generator.

        *audio_input* must yield raw PCM 16-bit 16kHz mono bytes (any chunk size).
        The generator runs until audio_input is exhausted or a fatal error occurs.
        """
        # Resolve engine preferences from agent.llmPreferences JSON
        prefs: dict = agent.llmPreferences or {}
        stt_engine: str = prefs.get("sttEngine", "faster-whisper")
        tts_engine: str = prefs.get("ttsEngine", "kokoro")
        tts_voice_id: str = "af_sky"
        cfg = getattr(agent, "configuration", None)
        if cfg and cfg.voiceId:
            tts_voice_id = cfg.voiceId

        # Initialise call state in Redis
        await self.state.create(call_sid, agent.id, tenant.id)

        # Feed audio_input into an internal queue so we can peek during SPEAKING
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=_AUDIO_QUEUE_MAXSIZE)
        feeder_task = asyncio.create_task(self._feed_audio(audio_input, audio_queue))

        try:
            async for event in self._pipeline_loop(
                audio_queue=audio_queue,
                agent_id=agent.id,
                tenant_id=tenant.id,
                call_sid=call_sid,
                session_id=session_id,
                stt_engine=stt_engine,
                tts_engine=tts_engine,
                tts_voice_id=tts_voice_id,
            ):
                yield event
        finally:
            feeder_task.cancel()
            await asyncio.gather(feeder_task, return_exceptions=True)
            await self.state.delete(call_sid)

    # ── Internal audio feeder ─────────────────────────────────────────────────

    @staticmethod
    async def _feed_audio(
        source: AsyncGenerator[bytes, None],
        queue: asyncio.Queue,
    ) -> None:
        """Background task: drain *source* into *queue*, put None sentinel at end."""
        try:
            async for chunk in source:
                await queue.put(chunk)
        except Exception:
            logger.exception("[orchestrator] audio feeder error")
        finally:
            await queue.put(None)  # sentinel — signals end of stream

    # ── Core pipeline loop ────────────────────────────────────────────────────

    async def _pipeline_loop(
        self,
        *,
        audio_queue: asyncio.Queue,
        agent_id: str,
        tenant_id: str,
        call_sid: str,
        session_id: str,
        stt_engine: str,
        tts_engine: str,
        tts_voice_id: str,
    ) -> AsyncGenerator[dict, None]:
        """
        Runs the listen → transcribe → think → speak loop indefinitely
        until audio_queue is closed (sentinel received) or a timeout fires.
        """
        # A chunk that was dequeued during barge-in handling and needs to start
        # the next listening phase.
        pending_chunk: bytes | None = None

        while True:
            # ── Phase 1: LISTENING ────────────────────────────────────────────
            await self.state.transition(call_sid, CallState.LISTENING)
            yield {"type": "state", "state": "listening"}

            pcm_buffer = bytearray()
            silence_frames = 0

            # Seed the buffer with any leftover chunk from a previous barge-in
            if pending_chunk is not None:
                rms = _pcm_rms(pending_chunk)
                if rms >= _SILENCE_RMS_THRESHOLD:
                    pcm_buffer.extend(pending_chunk)
                    silence_frames = 0
                pending_chunk = None

            # Accumulate PCM until end-of-utterance
            call_ended = False
            while True:
                try:
                    chunk = await asyncio.wait_for(audio_queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    logger.info("[orchestrator] 30s silence — ending call=%s", call_sid)
                    yield {"type": "done"}
                    return

                if chunk is None:
                    # Sentinel: audio_input exhausted
                    call_ended = True
                    break

                rms = _pcm_rms(chunk)
                pcm_buffer.extend(chunk)

                if rms < _SILENCE_RMS_THRESHOLD:
                    silence_frames += 1
                else:
                    silence_frames = 0

                if silence_frames >= _SILENCE_FRAMES_THRESHOLD and len(pcm_buffer) > 0:
                    break  # end-of-utterance detected

            utterance = bytes(pcm_buffer)

            if call_ended:
                if utterance:
                    # Process final utterance before ending
                    async for event in self._process_utterance(
                        utterance=utterance,
                        audio_queue=audio_queue,
                        agent_id=agent_id,
                        tenant_id=tenant_id,
                        call_sid=call_sid,
                        session_id=session_id,
                        stt_engine=stt_engine,
                        tts_engine=tts_engine,
                        tts_voice_id=tts_voice_id,
                    ):
                        yield event
                yield {"type": "done"}
                return

            if not utterance:
                continue  # no audio captured, listen again

            # ── Phases 2–4: STT → RAG → TTS ──────────────────────────────────
            interrupted = False
            pending_chunk_out: bytes | None = None

            async for event in self._process_utterance(
                utterance=utterance,
                audio_queue=audio_queue,
                agent_id=agent_id,
                tenant_id=tenant_id,
                call_sid=call_sid,
                session_id=session_id,
                stt_engine=stt_engine,
                tts_engine=tts_engine,
                tts_voice_id=tts_voice_id,
            ):
                yield event
                if event.get("type") == "interrupt":
                    interrupted = True
                    pending_chunk_out = event.get("_chunk")

            if interrupted:
                pending_chunk = pending_chunk_out

    async def _process_utterance(
        self,
        *,
        utterance: bytes,
        audio_queue: asyncio.Queue,
        agent_id: str,
        tenant_id: str,
        call_sid: str,
        session_id: str,
        stt_engine: str,
        tts_engine: str,
        tts_voice_id: str,
    ) -> AsyncGenerator[dict, None]:
        """
        STT → RAG (thinking) → TTS (speaking) for a single utterance.
        Monitors audio_queue for barge-in during the SPEAKING phase.
        Yields all events including a special {"type":"interrupt","_chunk":...} on barge-in.
        """
        # ── STT ───────────────────────────────────────────────────────────────
        transcript = await self.stt.transcribe_bytes(
            utterance,
            sample_rate=16000,
            engine=stt_engine,
        )
        if not transcript:
            logger.debug("[orchestrator] empty transcript call=%s", call_sid)
            return

        yield {"type": "text", "content": transcript}

        # ── Thinking / RAG ────────────────────────────────────────────────────
        await self.state.transition(call_sid, CallState.THINKING)
        yield {"type": "state", "state": "thinking"}

        response_text = await self._run_rag(
            tenant_id=tenant_id,
            agent_id=agent_id,
            query=transcript,
            session_id=session_id,
        )

        # ── TTS → μ-law ───────────────────────────────────────────────────────
        try:
            mulaw_bytes = await self.tts.synthesize_mulaw(
                text=response_text,
                engine=tts_engine,
                voice_id=tts_voice_id,
            )
        except Exception:
            logger.exception("[orchestrator] TTS failed call=%s", call_sid)
            return

        await self.state.transition(call_sid, CallState.SPEAKING)
        yield {"type": "state", "state": "speaking"}

        # ── Stream audio chunks, monitoring for barge-in ──────────────────────
        for i in range(0, len(mulaw_bytes), _FRAME_BYTES):
            chunk = mulaw_bytes[i : i + _FRAME_BYTES]
            yield {"type": "audio", "bytes": chunk}

            # Non-blocking check for incoming audio
            inbound: bytes | None = None
            try:
                inbound = audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                inbound = ...  # type: ignore[assignment]  # sentinel for "no data"

            if inbound is None:
                # None sentinel → audio_input exhausted; stop streaming
                yield {"type": "done"}
                return

            if inbound is not ...:  # actual audio arrived
                rms = _pcm_rms(inbound)  # type: ignore[arg-type]
                if rms > _INTERRUPT_RMS_THRESHOLD:
                    logger.info(
                        "[orchestrator] barge-in call=%s rms=%.1f", call_sid, rms
                    )
                    await self.state.transition(call_sid, CallState.LISTENING)
                    # Pass the barge-in chunk back so the caller can seed next listen
                    yield {"type": "interrupt", "_chunk": inbound}
                    return
                # Chunk not loud enough to interrupt — discard (already dequeued)

            await asyncio.sleep(0.02)  # 20ms pacing to match real-time audio

    # ── RAG helper ────────────────────────────────────────────────────────────

    async def _run_rag(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        query: str,
        session_id: str,
    ) -> str:
        from app.services.rag_service import process_query
        from app.database import AsyncSessionLocal

        try:
            async with AsyncSessionLocal() as db:
                result = await process_query(db, tenant_id, agent_id, query, session_id)
            return result.get("response", "I'm not sure how to help with that.")
        except Exception:
            logger.exception("[orchestrator] RAG failed session=%s", session_id)
            return "I encountered an error. Please try again."
