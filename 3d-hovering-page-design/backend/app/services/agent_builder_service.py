"""
agent_builder_service.py — Core intelligence for the Prompt-to-Agent system.

Orchestrates the full pipeline:
  1. extract_intent()        — Structured intent extraction from free-form prompt
  2. generate_full_config()  — context_breakdown sections + welcome msg + personas
  3. score_section_quality() — 1-5 star AI quality score per section
  4. detect_compliance()     — Auto-adds compliance sections by industry
  5. generate_sim_suite()    — 10-scenario simulation suite
  6. compute_revision_diff() — Structured diff for revision prompts
  7. score_deployment_readiness() — 0-100 readiness score with gap analysis
"""

from __future__ import annotations
import asyncio
import json
import uuid
import httpx
from typing import Any

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_FAST_MODEL = "llama-3.1-8b-instant"
_SMART_MODEL = "llama-3.3-70b-versatile"


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _groq_json(
    prompt: str,
    groq_key: str,
    *,
    model: str = _SMART_MODEL,
    temperature: float = 0.4,
    max_tokens: int = 2048,
    system: str = "You are an expert AI agent designer. Return valid JSON only — no markdown fences.",
) -> dict | list:
    """Single Groq call → parsed JSON. Raises ValueError on failure."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _GROQ_URL,
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
    if resp.status_code != 200:
        raise ValueError(f"Groq HTTP {resp.status_code}: {resp.text[:200]}")
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    # Find first [ or { to tolerate leading text
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = raw.find(start_char)
        end = raw.rfind(end_char) + 1
        if start != -1 and end > start:
            candidate = raw[start:end]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No JSON found in LLM response: {raw[:300]}")


def _slug() -> str:
    return str(uuid.uuid4())[:8]


# ── COMPLIANCE LIBRARY ────────────────────────────────────────────────────────

_COMPLIANCE_LIBRARY: dict[str, list[dict]] = {
    "healthcare": [
        {
            "title": "Consent & Privacy",
            "body": (
                "Before collecting any personal or medical information, clearly inform the caller that this "
                "call may be recorded for quality and training purposes, and that their information will be "
                "handled in accordance with applicable privacy laws. Obtain verbal consent before proceeding. "
                "Never store, process, or share identifiable health information beyond what is strictly necessary."
            ),
            "auto_compliance": True,
        }
    ],
    "finance": [
        {
            "title": "Regulatory Disclaimer",
            "body": (
                "This agent provides general information only and does not constitute financial, investment, "
                "or legal advice. All information shared is for informational purposes. Callers should consult "
                "a qualified financial advisor before making any decisions. The agent must not make any "
                "promises about returns, guarantees, or outcomes."
            ),
            "auto_compliance": True,
        }
    ],
    "real_estate": [
        {
            "title": "Fair Housing Compliance",
            "body": (
                "This agent must not discriminate based on race, color, religion, sex, national origin, "
                "disability, or familial status. The agent should not make any statements that could be "
                "construed as discriminatory. Any property recommendations must be based solely on the "
                "caller's stated preferences and budget."
            ),
            "auto_compliance": True,
        }
    ],
    "insurance": [
        {
            "title": "Terms & Disclosure",
            "body": (
                "Policy information provided by this agent is for general guidance only. Actual coverage, "
                "premiums, and terms depend on individual underwriting review. The agent must advise callers "
                "to review their policy documents carefully and clarify that quotes are estimates only."
            ),
            "auto_compliance": True,
        }
    ],
    "debt_collection": [
        {
            "title": "FDCPA / Collection Compliance",
            "body": (
                "This agent must comply with all applicable debt collection laws. The agent must identify "
                "itself as a debt collector at the start of each call. The agent must not use abusive, "
                "threatening, or misleading language. Callers have the right to request written verification "
                "of any debt. The agent must stop if the caller requests to cease contact."
            ),
            "auto_compliance": True,
        }
    ],
}

_INDUSTRY_ALIASES: dict[str, str] = {
    "medical": "healthcare", "hospital": "healthcare", "clinic": "healthcare",
    "dental": "healthcare", "pharmacy": "healthcare", "wellness": "healthcare",
    "bank": "finance", "banking": "finance", "fintech": "finance",
    "loan": "finance", "investment": "finance", "credit": "finance",
    "property": "real_estate", "realty": "real_estate",
    "mortgage": "real_estate",
    "insur": "insurance",
    "collection": "debt_collection", "debt": "debt_collection",
}


def detect_compliance_sections(industry: str, description: str = "") -> list[dict]:
    """Return auto-compliance section dicts that apply to a given industry."""
    normalized = industry.lower()
    # Alias lookup
    for alias, canonical in _INDUSTRY_ALIASES.items():
        if alias in normalized or alias in description.lower():
            normalized = canonical
            break
    return _COMPLIANCE_LIBRARY.get(normalized, [])


# ── 1. INTENT EXTRACTION ─────────────────────────────────────────────────────

async def extract_intent(prompt: str, groq_key: str) -> dict:
    """
    Parse a free-form agent description into a structured intent object.

    Returns:
    {
      "business_type": "dental clinic",
      "primary_language": "hi-IN",
      "secondary_languages": ["en-IN"],
      "use_cases": ["appointment_booking", "pricing_faq"],
      "call_type": "inbound",
      "industry": "healthcare",
      "geography": "Mumbai, India",
      "formality_level": "conversational",
      "tone": "warm",
      "company_name": "XYZ Dental",
      "detected_features": ["multilingual", "appointment_booking", "knowledge_base"]
    }
    """
    llm_prompt = f"""Analyse this AI voice/chat agent description and extract structured intent.

DESCRIPTION: "{prompt}"

Return a JSON object with EXACTLY these fields (use null for unknowns):
{{
  "business_type": "e.g. dental clinic / SaaS startup / e-commerce store",
  "company_name": "extracted company name or null",
  "primary_language": "BCP-47 language code e.g. en-IN / hi-IN / en-US",
  "secondary_languages": ["list of secondary BCP-47 codes or empty array"],
  "use_cases": ["list of 2-5 detected use cases e.g. appointment_booking / lead_qualification / pricing_faq / complaint_handling / order_tracking"],
  "call_type": "inbound or outbound or both",
  "industry": "one of: healthcare / finance / real_estate / insurance / e-commerce / education / hospitality / logistics / hr / customer_support / sales / other",
  "geography": "city/country if detectable, else null",
  "formality_level": "formal / conversational / casual",
  "tone": "warm / professional / enthusiastic / empathetic / direct",
  "detected_features": ["relevant capabilities: multilingual / 24x7_availability / escalation / appointment_booking / knowledge_base / crm_integration / order_lookup / payment_support"]
}}"""

    try:
        result = await _groq_json(llm_prompt, groq_key, model=_FAST_MODEL, temperature=0.2, max_tokens=512)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    # Fallback with sensible defaults
    return {
        "business_type": "business",
        "company_name": None,
        "primary_language": "en-IN",
        "secondary_languages": [],
        "use_cases": ["customer_support"],
        "call_type": "inbound",
        "industry": "other",
        "geography": None,
        "formality_level": "conversational",
        "tone": "professional",
        "detected_features": [],
    }


# ── 2. FULL CONFIG GENERATION ─────────────────────────────────────────────────

async def generate_full_config(intent: dict, prompt: str, groq_key: str) -> dict:
    """
    Generate a complete structured agent configuration from intent + original prompt.

    Returns:
    {
      "name": "...",
      "description": "...",
      "system_prompt": "...",       # flat systemPrompt compiled from sections
      "voice_type": "female",
      "suggested_voice_id": "...",
      "context_breakdown": [...],   # 5-7 sections
      "welcome_message": "...",
      "post_call_actions": [...],
      "caller_personas": [...],
      "language_config": {...},
      "template_id": "...",
      "llm_preferences": {...},
      "stt_engine": "...",
      "tts_engine": "...",
    }
    """
    use_cases_str = ", ".join(intent.get("use_cases") or ["customer_support"])
    industry = intent.get("industry") or "other"
    language = intent.get("primary_language") or "en-IN"
    tone = intent.get("tone") or "professional"
    formality = intent.get("formality_level") or "conversational"
    company = intent.get("company_name") or "the company"
    geography = intent.get("geography") or ""
    geo_hint = f" (based in {geography})" if geography else ""

    sections_prompt = f"""You are designing a production-grade AI voice agent.

ORIGINAL DESCRIPTION: "{prompt}"

EXTRACTED INTENT:
- Business: {intent.get("business_type","")}{geo_hint}
- Industry: {industry}
- Use cases: {use_cases_str}
- Primary language: {language}
- Tone: {tone} / {formality}
- Company: {company}

Generate a complete agent configuration as a JSON object with EXACTLY these fields:

{{
  "name": "2-4 word agent name",
  "description": "one crisp sentence describing what this agent does",
  "welcome_message": "the first thing the agent says — 1-2 sentences, natural, in-character, mentions company name",
  "context_breakdown": [
    {{
      "id": "sect_XXXXX",
      "title": "Section title (2-4 words)",
      "body": "Detailed instruction paragraph (4-6 sentences) telling the agent how to handle this topic. Be specific, actionable, and realistic.",
      "is_enabled": true
    }}
    // 5 to 7 sections total. MUST include: Agent Identity, at least 2 use-case sections,
    // Objection Handling or FAQ, Escalation Rules, Call Closure.
    // Add more sections as required by the use cases.
  ],
  "post_call_actions": [
    {{
      "variable": "snake_case_name",
      "extraction_prompt": "What was the [thing]?",
      "data_type": "string|date|phone|boolean|number"
    }}
    // 3-6 extraction variables most relevant to the use cases
  ],
  "caller_personas": [
    {{
      "name": "Persona name",
      "intent": "their primary goal",
      "frustration_level": "low|medium|high",
      "vocabulary_level": "basic|intermediate|technical",
      "typical_utterance": "example of what they might say"
    }}
    // 2-3 personas representing typical callers
  ],
  "voice_type": "male or female",
  "template_id": "one of: customer-support|cold-calling|appointment-setter|healthcare|real-estate|e-commerce|lead-qualification|faq-bot|hr-recruiter|debt-collection",
  "stt_engine": "faster-whisper or sarvam (use sarvam for Indian languages)",
  "tts_engine": "kokoro or sarvam (use sarvam for Indian languages)"
}}"""

    try:
        result = await _groq_json(
            sections_prompt, groq_key,
            model=_SMART_MODEL, temperature=0.5, max_tokens=3000
        )
    except Exception as exc:
        raise ValueError(f"Config generation failed: {exc}") from exc

    if not isinstance(result, dict):
        raise ValueError("LLM returned array instead of object")

    # Add stable IDs to sections that may be missing them
    for section in result.get("context_breakdown") or []:
        if not section.get("id"):
            section["id"] = f"sect_{_slug()}"
        section.setdefault("is_enabled", True)

    # Attach compliance sections
    compliance_sections = detect_compliance_sections(industry, prompt)
    for comp in compliance_sections:
        comp["id"] = f"sect_{_slug()}"
        comp.setdefault("is_enabled", True)
        result.setdefault("context_breakdown", []).append(comp)

    # Language config
    result["language_config"] = {
        "primary_language": language,
        "secondary_languages": intent.get("secondary_languages") or [],
        "geography": geography,
        "formality_level": formality,
    }
    result["llm_preferences"] = {"model": "llama-3.3-70b-versatile"}

    return result


# ── 3. SECTION QUALITY SCORING ────────────────────────────────────────────────

async def score_section_quality(section_title: str, section_body: str, groq_key: str) -> int:
    """
    Return a quality score 1-5 for a context_breakdown section.
    Uses fast model for speed; scores based on specificity, actionability, completeness.
    """
    prompt = f"""Score this AI agent instruction section on a scale of 1 to 5.

SECTION TITLE: {section_title}
SECTION CONTENT: {section_body[:600]}

Scoring criteria:
5 = Highly specific, actionable, covers edge cases, production-ready
4 = Good specificity, mostly actionable, minor gaps
3 = Adequate but generic; some specific details missing
2 = Vague or incomplete; missing key instructions
1 = Too short, placeholder-like, or generic

Return ONLY a JSON object: {{"score": 3, "reason": "brief reason"}}"""

    try:
        result = await _groq_json(prompt, groq_key, model=_FAST_MODEL, temperature=0.1, max_tokens=100)
        if isinstance(result, dict):
            score = int(result.get("score", 3))
            return max(1, min(5, score))
    except Exception:
        pass
    return 3  # default mid score


async def score_all_sections(sections: list[dict], groq_key: str) -> list[dict]:
    """Score all sections in parallel and attach quality_score to each."""
    tasks = [
        score_section_quality(s.get("title", ""), s.get("body", ""), groq_key)
        for s in sections
    ]
    scores = await asyncio.gather(*tasks)
    for section, score in zip(sections, scores):
        section["quality_score"] = score
    return sections


# ── 4. SIMULATION SUITE GENERATION ───────────────────────────────────────────

async def generate_simulation_suite(
    agent_config: dict,
    groq_key: str,
    count: int = 10,
) -> list[dict]:
    """
    Generate a comprehensive simulation test suite for an agent.

    Returns list of:
    {
      "id": "sim_XXXXX",
      "utterance": "caller says this",
      "expected_intent": "...",
      "expected_keywords": ["word1", "word2"],
      "must_not_contain": ["apolog", "i don't know"],
      "persona": "Regular Customer",
      "scenario_type": "normal|edge_case|adversarial|short_utterance|complaint",
      "difficulty": "easy|medium|hard"
    }
    """
    personas = agent_config.get("caller_personas") or []
    persona_descriptions = "\n".join(
        f"- {p.get('name')}: {p.get('intent')} (frustration={p.get('frustration_level')})"
        for p in personas
    ) or "- Standard user"

    use_cases = agent_config.get("use_cases") or ["customer_support"]
    if isinstance(use_cases, str):
        use_cases = [use_cases]
    use_cases_str = ", ".join(use_cases)

    prompt = f"""Generate {count} diverse simulation test scenarios for this AI voice agent.

AGENT: {agent_config.get("name", "AI Agent")}
DESCRIPTION: {agent_config.get("description", "")[:300]}
USE CASES: {use_cases_str}
CALLER PERSONAS:
{persona_descriptions}

Include a balanced mix of:
- 3 normal/routine requests (easy)
- 2 edge cases or unusual requests (medium)
- 2 adversarial or frustrated callers (hard)
- 1 very short/terse utterance (easy)
- 1 multi-part complex request (hard)
- 1 out-of-scope request (medium)

Return a JSON array of {count} objects:
[
  {{
    "utterance": "exact words the caller says",
    "expected_intent": "what they want",
    "expected_keywords": ["words that should appear in agent response"],
    "must_not_contain": ["words/phrases the agent must NOT say"],
    "persona": "persona name this caller represents",
    "scenario_type": "normal|edge_case|adversarial|short_utterance|complaint|out_of_scope",
    "difficulty": "easy|medium|hard"
  }}
]"""

    try:
        result = await _groq_json(
            prompt, groq_key,
            model=_FAST_MODEL, temperature=0.7, max_tokens=3000
        )
        if isinstance(result, list):
            for item in result:
                item["id"] = f"sim_{_slug()}"
            return result
    except Exception:
        pass
    return []


# ── 5. REVISION DIFF ──────────────────────────────────────────────────────────

async def compute_revision_diff(
    current_config: dict,
    revision_prompt: str,
    groq_key: str,
) -> dict:
    """
    Given the current agent config and a revision instruction, compute a structured diff.

    Returns:
    {
      "changes": [
        {
          "field": "welcome_message",
          "section_id": null,
          "change_type": "modified",
          "old_value": "...",
          "new_value": "...",
          "reason": "why this changed"
        },
        {
          "field": "context_breakdown",
          "section_id": "sect_ABC",
          "section_title": "Appointment Booking",
          "change_type": "modified|added|removed",
          "old_value": "...",
          "new_value": "...",
          "reason": "..."
        }
      ],
      "summary": "one-line summary of all changes",
      "sections_to_regenerate": ["sect_ABC"]
    }
    """
    sections_summary = []
    for s in current_config.get("context_breakdown") or []:
        sections_summary.append({
            "id": s.get("id"), "title": s.get("title"),
            "body_preview": (s.get("body") or "")[:200],
        })

    prompt = f"""You are applying a revision to an AI voice agent configuration.

CURRENT CONFIG SUMMARY:
- Name: {current_config.get("name")}
- Description: {current_config.get("description")}
- Welcome message: {current_config.get("welcome_message")}
- Sections: {json.dumps(sections_summary, indent=2)}

REVISION INSTRUCTION: "{revision_prompt}"

Determine what needs to change and return a structured diff as JSON:
{{
  "summary": "one-line summary of all changes being made",
  "changes": [
    {{
      "field": "name|description|welcome_message|voice_type|context_breakdown",
      "section_id": "sect_ID or null if not a section change",
      "section_title": "section title or null",
      "change_type": "modified|added|removed",
      "old_value": "current value (string, abbreviated if long)",
      "new_value": "new proposed value (full text)",
      "reason": "why this changes based on the revision instruction"
    }}
  ],
  "sections_to_regenerate": ["list of section IDs that need full regeneration"]
}}

Only include fields that actually need to change. Be precise about what changes."""

    try:
        result = await _groq_json(
            prompt, groq_key,
            model=_SMART_MODEL, temperature=0.3, max_tokens=2000
        )
        if isinstance(result, dict):
            return result
    except Exception as exc:
        pass
    return {"summary": "Could not compute diff", "changes": [], "sections_to_regenerate": []}


# ── 6. DEPLOYMENT READINESS SCORING ──────────────────────────────────────────

async def score_deployment_readiness(
    agent_config: dict,
    sim_results: list[dict] | None = None,
    groq_key: str | None = None,
) -> dict:
    """
    Score 0-100 deployment readiness and return gap analysis.

    Scoring breakdown (total 100):
    - context_breakdown quality (30): avg section quality score × 6
    - welcome_message (10): present and non-trivial
    - post_call_actions (10): has extraction variables
    - simulation_suite size (15): ≥10 scenarios
    - sim_results pass rate (20): fraction passing
    - language_config (5): configured
    - caller_personas (10): has personas
    """
    score = 0
    gaps = []

    # Section quality (max 30)
    sections = agent_config.get("context_breakdown") or []
    if sections:
        avg_quality = sum(s.get("quality_score", 3) for s in sections) / len(sections)
        section_score = int(avg_quality / 5 * 30)
        score += section_score
        if avg_quality < 3.5:
            gaps.append({"area": "Context Sections", "issue": "Some sections have low quality scores — add more specific instructions.", "priority": "high"})
        if len(sections) < 5:
            gaps.append({"area": "Context Sections", "issue": "Fewer than 5 sections defined — add more use-case coverage.", "priority": "medium"})
    else:
        gaps.append({"area": "Context Sections", "issue": "No context_breakdown sections defined.", "priority": "critical"})

    # Welcome message (max 10)
    welcome = agent_config.get("welcome_message") or ""
    if len(welcome) > 20:
        score += 10
    elif welcome:
        score += 5
        gaps.append({"area": "Welcome Message", "issue": "Welcome message is very short — expand it.", "priority": "low"})
    else:
        gaps.append({"area": "Welcome Message", "issue": "No welcome message configured.", "priority": "medium"})

    # Post-call actions (max 10)
    actions = agent_config.get("post_call_actions") or []
    if len(actions) >= 3:
        score += 10
    elif actions:
        score += 5
        gaps.append({"area": "Data Extraction", "issue": "Fewer than 3 extraction variables — add more post-call variables.", "priority": "low"})
    else:
        gaps.append({"area": "Data Extraction", "issue": "No post-call extraction variables configured.", "priority": "medium"})

    # Simulation suite (max 15)
    sim_suite = agent_config.get("simulation_suite") or []
    sim_count = len(sim_suite)
    if sim_count >= 10:
        score += 15
    elif sim_count >= 5:
        score += 8
        gaps.append({"area": "Simulation Suite", "issue": f"Only {sim_count} scenarios — aim for at least 10.", "priority": "medium"})
    else:
        score += 3
        gaps.append({"area": "Simulation Suite", "issue": "Not enough simulation scenarios to validate the agent.", "priority": "high"})

    # Sim results (max 20)
    if sim_results:
        passed = sum(1 for r in sim_results if r.get("passed", False))
        pass_rate = passed / len(sim_results)
        sim_result_score = int(pass_rate * 20)
        score += sim_result_score
        if pass_rate < 0.8:
            gaps.append({"area": "Simulation Results", "issue": f"Pass rate is {pass_rate*100:.0f}% — review failed scenarios.", "priority": "high"})
    else:
        score += 10  # neutral if no results yet

    # Language config (max 5)
    if agent_config.get("language_config"):
        score += 5

    # Caller personas (max 10)
    personas = agent_config.get("caller_personas") or []
    if len(personas) >= 2:
        score += 10
    elif personas:
        score += 5
        gaps.append({"area": "Caller Personas", "issue": "Only 1 persona defined — add more diversity.", "priority": "low"})
    else:
        gaps.append({"area": "Caller Personas", "issue": "No caller personas defined.", "priority": "low"})

    score = min(100, max(0, score))
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"

    return {
        "score": score,
        "grade": grade,
        "gaps": gaps,
        "ready_to_deploy": score >= 70,
        "summary": f"Deployment readiness: {score}/100 ({grade}) — {'Ready to deploy.' if score >= 70 else 'Address gaps before deploying.'}",
    }


# ── 7. SNAPSHOT HELPERS ───────────────────────────────────────────────────────

def build_snapshot(agent) -> dict:
    """Build a full config snapshot from an Agent ORM object."""
    return {
        "name": agent.name,
        "description": agent.description,
        "systemPrompt": agent.systemPrompt,
        "voiceType": agent.voiceType,
        "channels": agent.channels,
        "llmPreferences": agent.llmPreferences,
        "tokenLimit": agent.tokenLimit,
        "contextWindowStrategy": agent.contextWindowStrategy,
        "context_breakdown": agent.context_breakdown,
        "welcome_message": agent.welcome_message,
        "post_call_actions": agent.post_call_actions,
        "language_config": agent.language_config,
        "caller_personas": agent.caller_personas,
        "simulation_suite": agent.simulation_suite,
        "telephony_provider": agent.telephony_provider,
        "version_number": agent.version_number,
    }
