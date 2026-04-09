"""
Create 3 agents, test conversations, and generate human-like voice audio files.
Uses edge-tts (Microsoft Neural TTS) for natural-sounding voices.
"""
import httpx
import json
import re
import asyncio
import edge_tts
from pathlib import Path

BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "x-tenant-id": "demo-tenant",
    "x-user-id": "demo-user",
}

OUTPUT_DIR = Path(__file__).parent / "demo_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Microsoft Neural Voices — natural, human-like
VOICE_MAP = {
    "sales":     "en-US-GuyNeural",      # confident male — professional sales tone
    "emergency": "en-US-JennyNeural",     # calm female — authoritative dispatcher
    "friend":    "en-US-BrianNeural",     # relaxed male — casual friendly vibe
}

AGENTS = [
    {
        "key": "sales",
        "name": "SalesBot Pro",
        "systemPrompt": (
            "You are an enthusiastic, professional salesperson for a premium smart-home "
            "automation product called 'HomeFlow Hub'. You warmly greet callers, ask about "
            "their home needs, highlight product benefits (energy savings, voice control, "
            "security integration), handle objections, and guide them toward scheduling a "
            "free demo. Keep responses concise (2-3 sentences max). Be persuasive but never pushy."
        ),
        "voiceType": "male",
        "test_messages": [
            "Hi, I saw your ad about some smart home thing. What is it?",
            "Sounds interesting but I already have Alexa. Why would I need this?",
            "How much does it cost?",
        ],
    },
    {
        "key": "emergency",
        "name": "911 Emergency Dispatch",
        "systemPrompt": (
            "You are a calm, authoritative 911 emergency call dispatcher. You quickly assess "
            "the situation by asking the caller's location, the nature of the emergency, and "
            "whether anyone is injured. You provide clear, step-by-step instructions to keep "
            "the caller safe while help is on the way. Stay calm, professional, and reassuring. "
            "Keep responses short and directive (2-3 sentences). Prioritize life safety above all."
        ),
        "voiceType": "female",
        "test_messages": [
            "Help! There's been a car accident on Highway 101!",
            "Yes, there are two people in the other car. One seems unconscious.",
            "The ambulance isn't here yet, what should I do?",
        ],
    },
    {
        "key": "friend",
        "name": "Casual Buddy",
        "systemPrompt": (
            "You are a friendly, laid-back friend who loves chatting about anything — movies, "
            "food, weekend plans, funny stories. You use casual language, light humor, and "
            "occasionally throw in emojis. You're supportive, curious about the caller's day, "
            "and always keep the vibe positive. Keep responses conversational and brief (2-3 sentences)."
        ),
        "voiceType": "male",
        "test_messages": [
            "Hey! What's up? I'm so bored right now.",
            "Yeah, I've been thinking about watching a movie. Any recommendations?",
            "Nice! What are you up to this weekend?",
        ],
    },
]


async def create_agents(client: httpx.AsyncClient):
    """Create the 3 agents (skip if already exist) and return their IDs."""
    resp = await client.get(f"{BASE_URL}/api/agents/", headers=HEADERS)
    existing = {}
    if resp.status_code == 200:
        for a in resp.json().get("agents", []):
            existing[a["name"]] = a["id"]

    agent_ids = []
    for agent_def in AGENTS:
        if agent_def["name"] in existing:
            agent_id = existing[agent_def["name"]]
            agent_ids.append(agent_id)
            print(f"  [=] Reusing agent '{agent_def['name']}' -> {agent_id}")
            continue
        resp = await client.post(
            f"{BASE_URL}/api/agents/",
            headers=HEADERS,
            json={
                "name": agent_def["name"],
                "systemPrompt": agent_def["systemPrompt"],
                "voiceType": agent_def["voiceType"],
                "tokenLimit": 4096,
            },
        )
        if resp.status_code == 201:
            data = resp.json()
            agent_id = data["id"]
            agent_ids.append(agent_id)
            print(f"  [+] Created agent '{agent_def['name']}' -> {agent_id}")
        else:
            print(f"  [!] Failed to create '{agent_def['name']}': {resp.status_code} {resp.text}")
            agent_ids.append(None)
    return agent_ids


async def test_conversations(client: httpx.AsyncClient, agent_ids: list[str]):
    """Chat with each agent. Backend handles 429 retries automatically."""
    all_conversations = []
    for i, (agent_def, agent_id) in enumerate(zip(AGENTS, agent_ids)):
        if not agent_id:
            all_conversations.append([])
            continue
        print(f"\n  --- Talking to: {agent_def['name']} ---")
        conversation = []
        for msg in agent_def["test_messages"]:
            resp = await client.post(
                f"{BASE_URL}/api/runner/chat",
                headers=HEADERS,
                json={"message": msg, "agentId": agent_id, "sessionId": f"test-{i}"},
                timeout=90,
            )
            if resp.status_code == 200:
                reply = resp.json().get("response", "")
                conversation.append({"user": msg, "agent": reply})
                print(f"    User : {msg}")
                print(f"    Agent: {reply[:150]}{'...' if len(reply) > 150 else ''}")
            else:
                print(f"    [!] Chat failed: {resp.status_code} {resp.text}")
                conversation.append({"user": msg, "agent": f"ERROR {resp.status_code}"})
        all_conversations.append(conversation)
    return all_conversations


async def generate_voice_file(agent_def: dict, conversation: list, agent_id: str):
    """Generate one MP3 per agent — full conversation with agent voice responses."""
    safe_name = agent_def["name"].lower().replace(" ", "_")
    voice = VOICE_MAP[agent_def["key"]]
    audio_path = OUTPUT_DIR / f"{safe_name}.mp3"

    # Build text: combine all turns with natural pauses
    parts = []
    # Strip emojis and other non-speech characters
    emoji_re = re.compile(
        "[\U00002600-\U000027BF"
        "\U0001F300-\U0001F9FF"
        "\U0000FE00-\U0000FE0F"
        "\U0000200D"
        "\U00002702-\U000027B0"
        "\U0000231A-\U0000231B"
        "\U00002328"
        "\U000023CF"
        "\U000023E9-\U000023F3"
        "\U000023F8-\U000023FA"
        "]+", flags=re.UNICODE
    )
    for turn_idx, turn in enumerate(conversation, 1):
        agent_text = emoji_re.sub("", turn["agent"]).strip()
        parts.append(f"Turn {turn_idx}. The caller says: {turn['user']}.")
        parts.append(f"Agent responds: {agent_text}")

    full_text = " ... ".join(parts)
    communicate = edge_tts.Communicate(full_text, voice)
    await communicate.save(str(audio_path))

    size_kb = audio_path.stat().st_size // 1024
    print(f"  [+] {audio_path.name} ({size_kb} KB) — voice: {voice}")
    return audio_path


def save_transcript(agent_def: dict, agent_id: str, conversation: list):
    """Save conversation transcript."""
    safe_name = agent_def["name"].lower().replace(" ", "_")
    transcript_path = OUTPUT_DIR / f"{safe_name}_transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(f"Agent: {agent_def['name']}\n")
        f.write(f"Agent ID: {agent_id}\n")
        f.write(f"Voice: {VOICE_MAP[agent_def['key']]}\n")
        f.write(f"System Prompt: {agent_def['systemPrompt']}\n")
        f.write("=" * 70 + "\n\n")
        for turn_idx, turn in enumerate(conversation, 1):
            f.write(f"--- Turn {turn_idx} ---\n")
            f.write(f"User : {turn['user']}\n")
            f.write(f"Agent: {turn['agent']}\n\n")
    print(f"  [+] {transcript_path.name}")


async def main():
    # Clean output directory
    for f in OUTPUT_DIR.iterdir():
        f.unlink()
    print("=" * 60)
    print("VoiceFlow Agent Demo — Final")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Health check
        print("\n[1/4] Health check...")
        resp = await client.get(f"{BASE_URL}/health")
        print(f"  Backend: {resp.json().get('status')}")

        # 2. Create agents
        print("\n[2/4] Creating agents...")
        agent_ids = await create_agents(client)

        # 3. Test conversations (backend retries on 429 automatically)
        print("\n[3/4] Conversations (backend auto-retries rate limits)...")
        conversations = await test_conversations(client, agent_ids)

    # 4. Generate voice + transcripts
    print("\n[4/4] Generating neural voice audio (Microsoft Edge TTS)...")
    for agent_def, agent_id, convo in zip(AGENTS, agent_ids, conversations):
        if convo:
            await generate_voice_file(agent_def, convo, agent_id)
            save_transcript(agent_def, agent_id, convo)

    # Summary
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
    print(f"\nOutput: {OUTPUT_DIR}")
    for f in sorted(OUTPUT_DIR.iterdir()):
        print(f"  {f.name} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    asyncio.run(main())
