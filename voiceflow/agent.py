"""
VoiceAgent — the core abstraction.

Instantiate with a prompt or config, attach a knowledge base, attach tools,
and call .start() or .serve_mcp(). The framework handles the entire pipeline.

Example:
    agent = VoiceAgent(
        name="Dental Receptionist",
        prompt="You are a dental clinic receptionist that books appointments in Hindi.",
        stt=SarvamSTT(api_key="...", language="hi-IN"),
        tts=SarvamTTS(api_key="...", language="hi-IN"),
        llm=GroqLLM(model="llama-3.3-70b-versatile", api_key="..."),
        telephony=TwilioTelephony(account_sid="...", auth_token="..."),
    )
    agent.add_knowledge("./clinic_info/")
    agent.add_tool(book_appointment)   # decorated with @voice_tool
    agent.start(port=8040)
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("voiceflow.agent")


class VoiceAgent:
    """
    High-level composable voice agent.

    All components are pluggable via the plugin base classes.
    You never need to touch FastAPI, ChromaDB, Redis, or Twilio directly.
    """

    def __init__(
        self,
        name: str,
        prompt: str,
        stt=None,
        tts=None,
        llm=None,
        telephony=None,
        knowledge_base=None,
        noise_reduction: bool = True,
        semantic_vad: bool = True,
        recording: bool = False,
        crm_enrichment: bool = False,
    ):
        self.name = name
        self.prompt = prompt
        self.stt = stt
        self.tts = tts
        self.llm = llm
        self.telephony = telephony
        self.knowledge_base = knowledge_base
        self.noise_reduction = noise_reduction
        self.semantic_vad = semantic_vad
        self.recording = recording
        self.crm_enrichment = crm_enrichment
        self._tools: list[Callable] = []
        self._app = None

    def add_knowledge(self, source: str | Path, **kwargs) -> "VoiceAgent":
        """
        Attach a knowledge base. source can be:
          - A directory path (all .txt/.pdf/.md files are ingested)
          - A file path (single document)
          - A URL (scraped and ingested)
          - A KnowledgeBase instance (pre-configured)
        """
        from voiceflow.knowledge_base import KnowledgeBase
        if not isinstance(source, KnowledgeBase):
            kb = KnowledgeBase()
            kb.add(source, **kwargs)
            self.knowledge_base = kb
        else:
            self.knowledge_base = source
        return self

    def add_tool(self, fn: Callable) -> "VoiceAgent":
        """Register a @voice_tool decorated function the agent can call during conversations."""
        if not hasattr(fn, "_voice_tool_meta"):
            raise ValueError(
                f"{fn.__name__} must be decorated with @voice_tool before registration."
            )
        self._tools.append(fn)
        return self

    def _build_fastapi_app(self):
        """Build and return the FastAPI application for this agent."""
        from fastapi import FastAPI, Request
        from fastapi.responses import Response

        app = FastAPI(title=f"VoiceFlow — {self.name}")
        agent_ref = self

        @app.post("/voice/inbound")
        async def inbound(request: Request):
            """Twilio webhook — handles inbound calls."""
            return await agent_ref._handle_twilio_gather(request)

        @app.get("/health")
        def health():
            return {"status": "ok", "agent": agent_ref.name}

        return app

    def start(self, port: int = 8040, host: str = "127.0.0.1") -> None:
        """
        Start the agent as a standalone FastAPI server.
        The server listens for Twilio webhooks at /voice/inbound.
        """
        import uvicorn
        app = self._build_fastapi_app()
        self._app = app
        logger.info("Starting VoiceFlow agent '%s' on %s:%d", self.name, host, port)
        uvicorn.run(app, host=host, port=port)

    def serve_mcp(self) -> None:
        """
        Export this agent as a FastMCP server (stdio MCP protocol).
        Works with Claude Desktop, Cursor, and any MCP-compatible client.

        Configure in Claude Desktop:
          {
            "mcpServers": {
              "my_agent": {
                "command": "python",
                "args": ["my_agent.py"],
                "env": {"VOICEFLOW_API_URL": "http://localhost:8040"}
              }
            }
          }
        """
        from voiceflow.mcp import build_mcp_server
        mcp = build_mcp_server(self)
        mcp.run()

    async def _handle_twilio_gather(self, request) -> Any:
        """Internal: handle a Twilio Gather webhook turn."""
        form = await request.form()
        speech_result = form.get("SpeechResult", "").strip()
        caller = form.get("From", "")
        call_sid = form.get("CallSid", "")

        if not speech_result:
            return self._twiml_greeting()

        # STT already done by Twilio Gather, but apply semantic VAD
        if self.semantic_vad:
            from voiceflow.services.semantic_vad_shim import is_turn_complete_sync
            if not is_turn_complete_sync(speech_result):
                return self._twiml_listen_more()

        # RAG retrieval
        context = ""
        if self.knowledge_base:
            context = await self.knowledge_base.search(speech_result, top_k=5)

        # LLM response
        if self.llm:
            response_text = await self.llm.chat(
                system_prompt=self.prompt,
                user_message=speech_result,
                context=context,
            )
        else:
            response_text = "I don't have a language model configured."

        # TTS
        if self.tts:
            audio = await self.tts.synthesize(response_text)
        else:
            audio = None

        return self._twiml_say(response_text)

    def _twiml_greeting(self) -> Any:
        from fastapi.responses import Response
        name = self.name
        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Gather input="speech" timeout="5" action="/voice/inbound">'
            f'<Say>Hello! I\'m {name}. How can I help you today?</Say>'
            f'</Gather></Response>'
        )
        return Response(content=twiml, media_type="application/xml")

    def _twiml_listen_more(self) -> Any:
        from fastapi.responses import Response
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response><Gather input="speech" timeout="8" action="/voice/inbound">'
            '<Say>Go ahead, I\'m listening.</Say>'
            '</Gather></Response>'
        )
        return Response(content=twiml, media_type="application/xml")

    def _twiml_say(self, text: str) -> Any:
        from fastapi.responses import Response
        import html
        safe_text = html.escape(text)
        twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Gather input="speech" timeout="5" action="/voice/inbound">'
            f'<Say>{safe_text}</Say>'
            f'</Gather></Response>'
        )
        return Response(content=twiml, media_type="application/xml")
