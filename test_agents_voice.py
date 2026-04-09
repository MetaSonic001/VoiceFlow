"""
Create 3 agents through the FULL onboarding flow (exactly as the frontend would),
test conversations, and generate human-like voice audio files.
"""
import httpx
import json
import asyncio
import re
import edge_tts
from pathlib import Path

BASE = "http://localhost:8000"
H = {"Content-Type": "application/json", "x-tenant-id": "demo-tenant", "x-user-id": "demo-user"}
OUT = Path(__file__).parent / "demo_outputs"
OUT.mkdir(exist_ok=True)

VOICE_MAP = {
    "sales":     "en-US-GuyNeural",
    "emergency": "en-US-JennyNeural",
    "friend":    "en-US-BrianNeural",
}

SCENARIOS = [
    {
        "key": "sales",
        "company": {
            "company_name": "HomeFlow Technologies",
            "industry": "Smart Home / IoT",
            "use_case": "Sales & Lead Generation",
            "website_url": "https://homeflow.example.com",
            "description": "Premium smart-home automation company offering energy-saving, voice-controlled home systems.",
        },
        "brand": {
            "name": "HomeFlow Technologies",
            "brandVoice": "Professional, enthusiastic, solution-oriented. Highlights innovation and energy savings.",
            "allowedTopics": ["smart home", "energy savings", "home security", "voice control", "pricing", "demos"],
            "restrictedTopics": ["competitor bashing", "politics", "religion"],
        },
        "agent": {
            "name": "SalesBot Pro",
            "role": "Sales Representative",
            "description": "An enthusiastic sales agent for HomeFlow Hub smart home products. Handles inquiries, demos, and pricing.",
            "channels": ["phone", "web_chat"],
        },
        "voice": {
            "voice": "en-US-GuyNeural",
            "tone": "professional",
            "personality": "enthusiastic",
        },
        "agent_config": {
            "agent_name": "SalesBot Pro",
            "agent_role": "Sales Representative",
            "agent_description": "Handles product inquiries, pricing questions, and demo scheduling for HomeFlow Hub.",
            "personality_traits": ["enthusiastic", "professional", "persuasive", "empathetic"],
            "communication_channels": ["phone", "web_chat"],
            "preferred_response_style": "conversational",
            "response_tone": "professional",
            "voice_id": "en-US-GuyNeural",
            "company_name": "HomeFlow Technologies",
            "industry": "Smart Home / IoT",
            "primary_use_case": "Sales & Lead Generation",
        },
        "system_prompt": (
            "You are SalesBot Pro, a professional sales representative for HomeFlow Technologies. "
            "You sell the HomeFlow Hub - a premium smart-home automation system ($499 starter, $999 pro). "
            "Key benefits: energy savings up to 30%, voice control, security camera integration, "
            "works with 200+ smart devices. You warmly greet callers, ask about their home needs, "
            "highlight product benefits, handle objections, and guide toward scheduling a free demo. "
            "Keep responses concise (2-3 sentences). Be persuasive but never pushy. "
            "Company: HomeFlow Technologies | Industry: Smart Home / IoT"
        ),
        "test_messages": [
            "Hi, I saw your ad about some smart home thing. What is it?",
            "Sounds interesting but I already have Alexa. Why would I need this?",
            "How much does it cost? And can I get a demo?",
        ],
    },
    {
        "key": "emergency",
        "company": {
            "company_name": "Metro Emergency Services",
            "industry": "Emergency Services / Public Safety",
            "use_case": "Emergency Call Dispatch",
            "website_url": None,
            "description": "Municipal emergency call center handling 911 dispatch for fire, medical, and police services.",
        },
        "brand": {
            "name": "Metro Emergency Services",
            "brandVoice": "Calm, authoritative, clear, reassuring. Every word counts - life safety first.",
            "allowedTopics": ["emergency response", "first aid", "location", "medical", "fire", "police"],
            "restrictedTopics": ["small talk", "product sales", "opinions"],
        },
        "agent": {
            "name": "911 Emergency Dispatch",
            "role": "Emergency Dispatcher",
            "description": "A calm, authoritative 911 dispatcher that quickly assesses emergencies and provides life-saving instructions.",
            "channels": ["phone"],
        },
        "voice": {
            "voice": "en-US-JennyNeural",
            "tone": "calm",
            "personality": "authoritative",
        },
        "agent_config": {
            "agent_name": "911 Emergency Dispatch",
            "agent_role": "Emergency Dispatcher",
            "agent_description": "Handles 911 calls - assesses location, emergency type, injuries, and provides step-by-step instructions.",
            "personality_traits": ["calm", "authoritative", "reassuring", "decisive"],
            "communication_channels": ["phone"],
            "preferred_response_style": "directive",
            "response_tone": "calm",
            "voice_id": "en-US-JennyNeural",
            "company_name": "Metro Emergency Services",
            "industry": "Emergency Services / Public Safety",
            "primary_use_case": "Emergency Call Dispatch",
        },
        "system_prompt": (
            "You are a 911 emergency call dispatcher for Metro Emergency Services. "
            "You are calm, authoritative, and reassuring. Your top priority is life safety. "
            "Step 1: Get the caller's exact location (street address, intersection, or mile marker). "
            "Step 2: Determine the nature of the emergency (medical, fire, accident, crime). "
            "Step 3: Ask if anyone is injured and how many people are involved. "
            "Step 4: Provide clear, step-by-step instructions while help is on the way. "
            "Keep responses short and directive (2-3 sentences). Never ask unnecessary questions. "
            "If someone is unconscious, instruct on checking airways and recovery position."
        ),
        "test_messages": [
            "Help! There's been a car accident on Highway 101 near exit 24!",
            "Yes, there are two people in the other car. One seems unconscious.",
            "The ambulance isn't here yet, what should I do? The person isn't breathing well.",
        ],
    },
    {
        "key": "friend",
        "company": {
            "company_name": "ChillChat AI",
            "industry": "Entertainment / Social",
            "use_case": "Casual Companion Chat",
            "website_url": "https://chillchat.example.com",
            "description": "AI companion service for casual conversations, entertainment, and emotional support.",
        },
        "brand": {
            "name": "ChillChat AI",
            "brandVoice": "Casual, warm, fun, supportive. Uses humor, pop culture references, and light slang.",
            "allowedTopics": ["movies", "music", "food", "weekend plans", "hobbies", "sports", "travel", "life advice"],
            "restrictedTopics": ["medical advice", "legal advice", "financial advice", "harmful content"],
        },
        "agent": {
            "name": "Casual Buddy",
            "role": "Casual Friend",
            "description": "A friendly, laid-back AI companion that chats about movies, food, weekend plans, and life.",
            "channels": ["web_chat", "phone"],
        },
        "voice": {
            "voice": "en-US-BrianNeural",
            "tone": "casual",
            "personality": "friendly",
        },
        "agent_config": {
            "agent_name": "Casual Buddy",
            "agent_role": "Casual Friend",
            "agent_description": "Hangout buddy for casual conversations about movies, food, plans, and life.",
            "personality_traits": ["friendly", "laid-back", "humorous", "supportive", "curious"],
            "communication_channels": ["web_chat", "phone"],
            "preferred_response_style": "conversational",
            "response_tone": "casual",
            "voice_id": "en-US-BrianNeural",
            "company_name": "ChillChat AI",
            "industry": "Entertainment / Social",
            "primary_use_case": "Casual Companion Chat",
        },
        "system_prompt": (
            "You are Casual Buddy, a friendly laid-back AI friend from ChillChat AI. "
            "You love chatting about movies, food, weekend plans, funny stories, and life. "
            "You use casual language, light humor, and you're always positive and supportive. "
            "You're curious about the caller's day and share your own (fictional) plans too. "
            "Keep responses conversational and brief (2-3 sentences). "
            "You are NOT a customer service bot - you're a friend. Talk like one."
        ),
        "test_messages": [
            "Hey! What's up? I'm so bored right now.",
            "Yeah, I've been thinking about watching a movie. Any recommendations?",
            "Nice! What are you up to this weekend?",
        ],
    },
]


async def run_full_onboarding(client: httpx.AsyncClient, scenario: dict) -> dict:
    """Execute the full onboarding flow for one agent, exactly as the frontend would."""
    print(f"\n  -- Onboarding: {scenario['agent']['name']} --")

    # Step 1: Company profile
    print(f"    [1] Company profile...")
    r = await client.post(f"{BASE}/onboarding/company", headers=H, json=scenario["company"])
    assert r.status_code == 200, f"Company profile failed: {r.text}"

    # Step 2: Brand
    print(f"    [2] Brand...")
    r = await client.post(f"{BASE}/api/brands/", headers=H, json=scenario["brand"])
    assert r.status_code == 201, f"Brand creation failed: {r.text}"
    brand_id = r.json()["id"]
    print(f"        Brand ID: {brand_id}")

    # Step 3: Agent (via onboarding -> creates Agent + AgentConfiguration)
    print(f"    [3] Agent + AgentConfiguration...")
    r = await client.post(f"{BASE}/onboarding/agent", headers=H,
                          json={**scenario["agent"], "brandId": brand_id})
    assert r.status_code == 200, f"Agent creation failed: {r.text}"
    agent_id = r.json()["agent_id"]
    print(f"        Agent ID: {agent_id}")

    # Step 4: Set system prompt on agent (so runner can use it)
    print(f"    [4] System prompt...")
    r = await client.put(f"{BASE}/api/agents/{agent_id}", headers=H,
                         json={"systemPrompt": scenario["system_prompt"]})
    assert r.status_code == 200, f"System prompt failed: {r.text}"

    # Step 5: Voice config
    print(f"    [5] Voice config...")
    r = await client.post(f"{BASE}/onboarding/voice", headers=H, json=scenario["voice"])
    assert r.status_code == 200, f"Voice config failed: {r.text}"

    # Step 6: Channels
    print(f"    [6] Channels...")
    r = await client.post(f"{BASE}/onboarding/channels", headers=H, json={})
    assert r.status_code == 200

    # Step 7: Agent config (detailed)
    print(f"    [7] Agent config (detailed)...")
    r = await client.post(f"{BASE}/onboarding/agent-config", headers=H, json=scenario["agent_config"])
    assert r.status_code == 200, f"Agent config failed: {r.text}"

    # Step 8: Progress tracking
    print(f"    [8] Progress...")
    r = await client.post(f"{BASE}/onboarding/progress", headers=H, json={
        "agent_id": agent_id, "current_step": 8,
        "data": {"company": scenario["company"], "brand_id": brand_id,
                 "agent_id": agent_id, "voice": scenario["voice"],
                 "channels": scenario["agent"]["channels"]},
    })
    assert r.status_code == 200

    # Step 9: Deploy
    print(f"    [9] Deploy...")
    r = await client.post(f"{BASE}/onboarding/deploy", headers=H, json={"agent_id": agent_id})
    if r.status_code == 200:
        print(f"        Phone: {r.json().get('phone_number', 'N/A')}")
    else:
        print(f"        Deploy skipped (Twilio not configured - expected)")

    print(f"    [OK] {scenario['agent']['name']} fully onboarded!")
    return {"agent_id": agent_id, "brand_id": brand_id}


async def cleanup(client: httpx.AsyncClient):
    """Delete existing agents and brands via API."""
    r = await client.get(f"{BASE}/api/agents/", headers=H)
    if r.status_code == 200:
        agents = r.json().get("agents", [])
        for a in agents:
            await client.delete(f"{BASE}/api/agents/{a['id']}", headers=H)
        if agents:
            print(f"  Cleaned {len(agents)} agents")
    r = await client.get(f"{BASE}/api/brands/", headers=H)
    if r.status_code == 200:
        brands = r.json() if isinstance(r.json(), list) else r.json().get("brands", [])
        for b in brands:
            await client.delete(f"{BASE}/api/brands/{b['id']}", headers=H)
        if brands:
            print(f"  Cleaned {len(brands)} brands")
    await client.delete(f"{BASE}/onboarding/progress", headers=H)


async def test_conversations(client: httpx.AsyncClient, scenarios: list, results: list):
    """Chat with each agent. Backend handles 429 retries automatically."""
    all_convos = []
    for scenario, result in zip(scenarios, results):
        agent_id = result["agent_id"]
        print(f"\n  --- {scenario['agent']['name']} ---")
        convo = []
        for msg in scenario["test_messages"]:
            r = await client.post(
                f"{BASE}/api/runner/chat", headers=H,
                json={"message": msg, "agentId": agent_id, "sessionId": f"test-{scenario['key']}"},
                timeout=90,
            )
            if r.status_code == 200:
                reply = r.json().get("response", "")
                convo.append({"user": msg, "agent": reply})
                print(f"    User : {msg}")
                print(f"    Agent: {reply[:150]}{'...' if len(reply) > 150 else ''}")
            else:
                print(f"    [!] Failed: {r.status_code}")
                convo.append({"user": msg, "agent": f"ERROR {r.status_code}"})
        all_convos.append(convo)
    return all_convos


async def generate_voice(scenario: dict, convo: list):
    safe = scenario["agent"]["name"].lower().replace(" ", "_")
    voice = VOICE_MAP[scenario["key"]]
    path = OUT / f"{safe}.mp3"

    emoji_re = re.compile(
        "[\U00002600-\U000027BF\U0001F300-\U0001F9FF\U0000FE00-\U0000FE0F"
        "\U0000200D\U00002702-\U000027B0]+", flags=re.UNICODE
    )
    parts = []
    for i, t in enumerate(convo, 1):
        text = emoji_re.sub("", t["agent"]).strip()
        parts.append(f"Turn {i}. The caller says: {t['user']}.")
        parts.append(f"Agent responds: {text}")

    comm = edge_tts.Communicate(" ... ".join(parts), voice)
    await comm.save(str(path))
    print(f"  [+] {path.name} ({path.stat().st_size // 1024} KB) - {voice}")


def save_transcript(scenario: dict, result: dict, convo: list):
    safe = scenario["agent"]["name"].lower().replace(" ", "_")
    path = OUT / f"{safe}_transcript.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Agent: {scenario['agent']['name']}\n")
        f.write(f"Agent ID: {result['agent_id']}\n")
        f.write(f"Brand ID: {result['brand_id']}\n")
        f.write(f"Role: {scenario['agent']['role']}\n")
        f.write(f"Company: {scenario['company']['company_name']}\n")
        f.write(f"Industry: {scenario['company']['industry']}\n")
        f.write(f"Voice: {VOICE_MAP[scenario['key']]}\n")
        f.write(f"Channels: {', '.join(scenario['agent']['channels'])}\n")
        f.write(f"System Prompt: {scenario['system_prompt']}\n")
        f.write("=" * 70 + "\n\n")
        for i, t in enumerate(convo, 1):
            f.write(f"--- Turn {i} ---\n")
            f.write(f"User : {t['user']}\n")
            f.write(f"Agent: {t['agent']}\n\n")
    print(f"  [+] {path.name}")


async def verify_db(client: httpx.AsyncClient, results: list):
    """Verify all records exist."""
    print("\n  DB Verification:")
    for scenario, result in zip(SCENARIOS, results):
        r = await client.get(f"{BASE}/api/agents/{result['agent_id']}", headers=H)
        a = r.json()
        checks = {
            "agent": r.status_code == 200,
            "brand": a.get("brandId") == result["brand_id"],
            "prompt": bool(a.get("systemPrompt")),
            "status": a.get("status") == "active",
            "channels": a.get("channels") is not None,
        }
        ok = "PASS" if all(checks.values()) else "FAIL"
        print(f"    [{ok}] {scenario['agent']['name']}: {checks}")


async def main():
    for f in OUT.iterdir():
        f.unlink()

    print("=" * 60)
    print("VoiceFlow - Full Onboarding Demo")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/health")
        print(f"\n[1/6] Backend: {r.json().get('status')}")

        print("\n[2/6] Cleaning old data...")
        await cleanup(client)

        print("\n[3/6] Full onboarding flow (9 steps each)...")
        results = []
        for scenario in SCENARIOS:
            result = await run_full_onboarding(client, scenario)
            results.append(result)

        print("\n[4/6] Verifying DB records...")
        await verify_db(client, results)

        print("\n[5/6] Testing conversations...")
        convos = await test_conversations(client, SCENARIOS, results)

    print("\n[6/6] Generating voice audio...")
    for scenario, result, convo in zip(SCENARIOS, results, convos):
        if convo:
            await generate_voice(scenario, convo)
            save_transcript(scenario, result, convo)

    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
    print(f"\nOutput: {OUT}")
    for f in sorted(OUT.iterdir()):
        print(f"  {f.name} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    asyncio.run(main())
