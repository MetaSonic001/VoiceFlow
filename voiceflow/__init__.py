"""
voiceflow — A composable Python framework for building production-grade AI voice agents.

Developers can get a working voice agent in under 20 lines:

    from voiceflow import VoiceAgent
    from voiceflow.plugins.stt import WhisperSTT
    from voiceflow.plugins.tts import KokoroTTS
    from voiceflow.plugins.llm import GroqLLM
    from voiceflow.plugins.telephony import TwilioTelephony

    agent = VoiceAgent(
        name="Support Bot",
        prompt="You are a helpful customer support agent for Acme Corp.",
        stt=WhisperSTT(),
        tts=KokoroTTS(voice_id="af_bella"),
        llm=GroqLLM(model="llama-3.3-70b-versatile"),
        telephony=TwilioTelephony(account_sid="...", auth_token="..."),
    )

    # Attach a knowledge base (auto-chunks, embeds, indexes)
    agent.add_knowledge("./docs/")

    # Start the MCP server (Claude Desktop compatible)
    # or: agent.start(port=8040)   for a standalone FastAPI server
    agent.serve_mcp()

pip install voiceflow                  # core only
pip install voiceflow[sarvam]          # + Sarvam AI (Indian languages)
pip install voiceflow[twilio]          # + Twilio telephony
pip install voiceflow[crm]             # + HubSpot + Salesforce + Slack
pip install voiceflow[all]             # everything
"""
from voiceflow.agent import VoiceAgent
from voiceflow.knowledge_base import KnowledgeBase
from voiceflow.tools import voice_tool

__version__ = "0.1.0"
__all__ = ["VoiceAgent", "KnowledgeBase", "voice_tool"]
