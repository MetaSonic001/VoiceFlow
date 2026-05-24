"""
Voice catalog — aggregates voices from Edge TTS, Sarvam AI, Kokoro, and Piper.

Providers
---------
* Edge TTS  — 120+ curated voices, free, requires internet (Microsoft Azure).
* Sarvam AI — 10 Indian languages × 5 speakers, requires SARVAM_API_KEY.
* Kokoro     — local sidecar at :8880, CPU-only.
* Piper      — local sidecar at :8890, CPU-only.

Voice ID scheme
---------------
  edge-{ShortName}     e.g.  edge-en-US-AriaNeural
  sarvam-{lang}-{spk}  e.g.  sarvam-hi-IN-meera
  kokoro-{voice}       e.g.  kokoro-af_sky
  piper-{voice}        e.g.  piper-en_US-lessac-medium
  clone-{uuid}         e.g.  clone-xxxxxxxx (user clones)
"""

from __future__ import annotations

import os
from typing import Any

# ── Voice Categories ──────────────────────────────────────────────────────────
VOICE_CATEGORIES: dict[str, str] = {
    "customer_support": "Customer Support",
    "sales":            "Sales & Outreach",
    "news_narration":   "News & Narration",
    "educational":      "Educational",
    "asmr_calm":        "ASMR & Calm",
    "indian_regional":  "Indian Regional",
}

# ── Edge TTS voices ───────────────────────────────────────────────────────────
# (ShortName, DisplayName, Gender, Locale, LanguageName, Accent, [categories], Style)
_EDGE_DATA: list[tuple] = [
    # en-US -------------------------------------------------------------
    ("en-US-AriaNeural",        "Aria",        "Female", "en-US", "English (US)", "American",  ["customer_support"],              "Friendly & warm"),
    ("en-US-AvaNeural",         "Ava",         "Female", "en-US", "English (US)", "American",  ["customer_support"],              "Expressive & natural"),
    ("en-US-JennyNeural",       "Jenny",       "Female", "en-US", "English (US)", "American",  ["customer_support"],              "Conversational"),
    ("en-US-EmmaNeural",        "Emma",        "Female", "en-US", "English (US)", "American",  ["educational", "customer_support"],"Cheerful & clear"),
    ("en-US-AnaNeural",         "Ana",         "Female", "en-US", "English (US)", "American",  ["asmr_calm"],                     "Soft & gentle"),
    ("en-US-MichelleNeural",    "Michelle",    "Female", "en-US", "English (US)", "American",  ["customer_support"],              "Clear & confident"),
    ("en-US-NancyNeural",       "Nancy",       "Female", "en-US", "English (US)", "American",  ["news_narration"],                "Mature & authoritative"),
    ("en-US-SerenaNeural",      "Serena",      "Female", "en-US", "English (US)", "American",  ["asmr_calm"],                     "Pleasant & calm"),
    ("en-US-AmberNeural",       "Amber",       "Female", "en-US", "English (US)", "American",  ["sales"],                         "Warm & persuasive"),
    ("en-US-MonicaNeural",      "Monica",      "Female", "en-US", "English (US)", "American",  ["customer_support"],              "Warm & empathetic"),
    ("en-US-ElizabethNeural",   "Elizabeth",   "Female", "en-US", "English (US)", "American",  ["news_narration", "educational"], "Storytelling"),
    ("en-US-GuyNeural",         "Guy",         "Male",   "en-US", "English (US)", "American",  ["news_narration"],                "News anchor"),
    ("en-US-BrianNeural",       "Brian",       "Male",   "en-US", "English (US)", "American",  ["sales", "news_narration"],       "Confident narrator"),
    ("en-US-AndrewNeural",      "Andrew",      "Male",   "en-US", "English (US)", "American",  ["customer_support"],              "Casual & friendly"),
    ("en-US-ChristopherNeural", "Christopher", "Male",   "en-US", "English (US)", "American",  ["asmr_calm"],                     "Relaxed & calm"),
    ("en-US-DavisNeural",       "Davis",       "Male",   "en-US", "English (US)", "American",  ["news_narration", "educational"], "Informative"),
    ("en-US-EricNeural",        "Eric",        "Male",   "en-US", "English (US)", "American",  ["educational"],                   "Rational & clear"),
    ("en-US-RogerNeural",       "Roger",       "Male",   "en-US", "English (US)", "American",  ["news_narration"],                "Animated & expressive"),
    ("en-US-SteffanNeural",     "Steffan",     "Male",   "en-US", "English (US)", "American",  ["news_narration"],                "Crisp & authoritative"),
    ("en-US-TonyNeural",        "Tony",        "Male",   "en-US", "English (US)", "American",  ["sales"],                         "Enthusiastic"),
    # en-GB -------------------------------------------------------------
    ("en-GB-LibbyNeural",       "Libby",       "Female", "en-GB", "English (UK)", "British",   ["customer_support"],              "Friendly & professional"),
    ("en-GB-MaisieNeural",      "Maisie",      "Female", "en-GB", "English (UK)", "British",   ["educational"],                   "Lively & warm"),
    ("en-GB-SoniaNeural",       "Sonia",       "Female", "en-GB", "English (UK)", "British",   ["news_narration", "asmr_calm"],   "Mature & composed"),
    ("en-GB-HollieNeural",      "Hollie",      "Female", "en-GB", "English (UK)", "British",   ["customer_support"],              "Warm & natural"),
    ("en-GB-OliviaNeural",      "Olivia",      "Female", "en-GB", "English (UK)", "British",   ["educational", "asmr_calm"],      "Gentle & articulate"),
    ("en-GB-RyanNeural",        "Ryan",        "Male",   "en-GB", "English (UK)", "British",   ["sales", "news_narration"],       "Confident & polished"),
    ("en-GB-ThomasNeural",      "Thomas",      "Male",   "en-GB", "English (UK)", "British",   ["asmr_calm", "educational"],      "Relaxed & refined"),
    ("en-GB-NoahNeural",        "Noah",        "Male",   "en-GB", "English (UK)", "British",   ["customer_support"],              "Easygoing & approachable"),
    ("en-GB-OliverNeural",      "Oliver",      "Male",   "en-GB", "English (UK)", "British",   ["customer_support"],              "Friendly & clear"),
    # en-AU -------------------------------------------------------------
    ("en-AU-NatashaNeural",     "Natasha",     "Female", "en-AU", "English (AU)", "Australian",["customer_support"],              "Natural & warm"),
    ("en-AU-FreyaNeural",       "Freya",       "Female", "en-AU", "English (AU)", "Australian",["asmr_calm", "customer_support"], "Warm & gentle"),
    ("en-AU-TimNeural",         "Tim",         "Male",   "en-AU", "English (AU)", "Australian",["asmr_calm"],                     "Relaxed & easy"),
    ("en-AU-WilliamNeural",     "William",     "Male",   "en-AU", "English (AU)", "Australian",["sales", "news_narration"],       "Casual & confident"),
    # en-IN -------------------------------------------------------------
    ("en-IN-NeerjaNeural",      "Neerja",      "Female", "en-IN", "English (IN)", "Indian",    ["customer_support", "indian_regional"], "Friendly & professional"),
    ("en-IN-KavyaNeural",       "Kavya",       "Female", "en-IN", "English (IN)", "Indian",    ["customer_support", "indian_regional"], "Natural & warm"),
    ("en-IN-AaravNeural",       "Aarav",       "Male",   "en-IN", "English (IN)", "Indian",    ["sales", "indian_regional"],      "Confident & clear"),
    ("en-IN-PrabhatNeural",     "Prabhat",     "Male",   "en-IN", "English (IN)", "Indian",    ["customer_support", "indian_regional"], "Conversational"),
    # hi-IN (Hindi) -----------------------------------------------------
    ("hi-IN-SwaraNeural",       "Swara",       "Female", "hi-IN", "Hindi (India)", "Hindi",    ["customer_support", "indian_regional"], "Expressive & warm"),
    ("hi-IN-MadhurNeural",      "Madhur",       "Male",   "hi-IN", "Hindi (India)", "Hindi",   ["news_narration", "indian_regional"],  "Eloquent & authoritative"),
    # ta-IN (Tamil) -----------------------------------------------------
    ("ta-IN-PallaviNeural",     "Pallavi",     "Female", "ta-IN", "Tamil (India)", "Tamil",    ["customer_support", "indian_regional"], "Expressive & clear"),
    ("ta-IN-ValluvarNeural",    "Valluvar",    "Male",   "ta-IN", "Tamil (India)", "Tamil",    ["news_narration", "indian_regional"],  "Dignified & clear"),
    # te-IN (Telugu) ----------------------------------------------------
    ("te-IN-ShrutiNeural",      "Shruti",      "Female", "te-IN", "Telugu (India)","Telugu",   ["customer_support", "indian_regional"], "Expressive"),
    ("te-IN-MohanNeural",       "Mohan",       "Male",   "te-IN", "Telugu (India)","Telugu",   ["news_narration", "indian_regional"],  "Steady & clear"),
    # bn-IN (Bengali) ---------------------------------------------------
    ("bn-IN-TanishaaNeural",    "Tanishaa",    "Female", "bn-IN", "Bengali (India)","Bengali",  ["customer_support", "indian_regional"], "Warm & expressive"),
    ("bn-IN-BashkarNeural",     "Bashkar",     "Male",   "bn-IN", "Bengali (India)","Bengali",  ["news_narration", "indian_regional"],  "Deep & warm"),
    # mr-IN (Marathi) ---------------------------------------------------
    ("mr-IN-AarohiNeural",      "Aarohi",      "Female", "mr-IN", "Marathi (India)","Marathi",  ["customer_support", "indian_regional"], "Natural & warm"),
    ("mr-IN-ManojNeural",       "Manoj",       "Male",   "mr-IN", "Marathi (India)","Marathi",  ["news_narration", "indian_regional"],  "Enthusiastic"),
    # kn-IN (Kannada) ---------------------------------------------------
    ("kn-IN-SapnaNeural",       "Sapna",       "Female", "kn-IN", "Kannada (India)","Kannada",  ["customer_support", "indian_regional"], "Expressive & friendly"),
    ("kn-IN-GaganNeural",       "Gagan",       "Male",   "kn-IN", "Kannada (India)","Kannada",  ["indian_regional"],                    "Steady & clear"),
    # gu-IN (Gujarati) --------------------------------------------------
    ("gu-IN-DhwaniNeural",      "Dhwani",      "Female", "gu-IN", "Gujarati (India)","Gujarati", ["customer_support", "indian_regional"], "Expressive"),
    ("gu-IN-NiranjanNeural",    "Niranjan",     "Male",   "gu-IN", "Gujarati (India)","Gujarati", ["indian_regional"],                    "Clear & dignified"),
    # ml-IN (Malayalam) -------------------------------------------------
    ("ml-IN-SobhanaNeural",     "Sobhana",     "Female", "ml-IN", "Malayalam (India)","Malayalam",["customer_support", "indian_regional"],"Friendly & warm"),
    ("ml-IN-MidhunNeural",      "Midhun",      "Male",   "ml-IN", "Malayalam (India)","Malayalam",["indian_regional"],                    "Relaxed & warm"),
    # pa-IN (Punjabi) ---------------------------------------------------
    ("pa-IN-VaaniNeural",       "Vaani",       "Female", "pa-IN", "Punjabi (India)","Punjabi",  ["customer_support", "indian_regional"], "Warm & expressive"),
    ("pa-IN-OjasNeural",        "Ojas",        "Male",   "pa-IN", "Punjabi (India)","Punjabi",  ["indian_regional"],                    "Confident & clear"),
    # de-DE (German) ----------------------------------------------------
    ("de-DE-KatjaNeural",       "Katja",       "Female", "de-DE", "German",       "German",    ["customer_support"],              "Professional & crisp"),
    ("de-DE-AmalaNeural",       "Amala",       "Female", "de-DE", "German",       "German",    ["educational"],                   "Clear & warm"),
    ("de-DE-LeniNeural",        "Leni",        "Female", "de-DE", "German",       "German",    ["asmr_calm"],                     "Soft & pleasant"),
    ("de-DE-ConradNeural",      "Conrad",      "Male",   "de-DE", "German",       "German",    ["news_narration"],                "Authoritative"),
    ("de-DE-FlorianMultilingualNeural", "Florian", "Male", "de-DE", "German",    "German",    ["sales"],                         "Energetic & confident"),
    # fr-FR (French) ----------------------------------------------------
    ("fr-FR-DeniseNeural",      "Denise",      "Female", "fr-FR", "French",       "French",    ["customer_support"],              "Elegant & warm"),
    ("fr-FR-EloiseNeural",      "Eloise",      "Female", "fr-FR", "French",       "French",    ["asmr_calm", "educational"],      "Gentle & refined"),
    ("fr-FR-VivienneNeural",    "Vivienne",    "Female", "fr-FR", "French",       "French",    ["news_narration"],                "Clear & composed"),
    ("fr-FR-HenriNeural",       "Henri",       "Male",   "fr-FR", "French",       "French",    ["news_narration"],                "Authoritative"),
    ("fr-FR-RemyMultilingualNeural", "Remy",   "Male",   "fr-FR", "French",       "French",    ["sales"],                         "Expressive & confident"),
    # es-ES / es-MX -----------------------------------------------------
    ("es-ES-ElviraNeural",      "Elvira",      "Female", "es-ES", "Spanish (ES)", "Castilian", ["customer_support"],              "Clear & professional"),
    ("es-ES-AlvaroNeural",      "Alvaro",      "Male",   "es-ES", "Spanish (ES)", "Castilian", ["news_narration", "sales"],       "Confident & clear"),
    ("es-MX-DaliaNeural",       "Dalia",       "Female", "es-MX", "Spanish (MX)", "Mexican",   ["customer_support"],              "Warm & natural"),
    ("es-MX-JorgeNeural",       "Jorge",       "Male",   "es-MX", "Spanish (MX)", "Mexican",   ["sales"],                         "Confident & energetic"),
    # it-IT (Italian) ---------------------------------------------------
    ("it-IT-IsabellaNeural",    "Isabella",    "Female", "it-IT", "Italian",      "Italian",   ["customer_support"],              "Warm & expressive"),
    ("it-IT-ElsaNeural",        "Elsa",        "Female", "it-IT", "Italian",      "Italian",   ["asmr_calm", "educational"],      "Composed & refined"),
    ("it-IT-DiegoNeural",       "Diego",       "Male",   "it-IT", "Italian",      "Italian",   ["sales", "news_narration"],       "Confident & dynamic"),
    ("it-IT-GiuseppeNeural",    "Giuseppe",    "Male",   "it-IT", "Italian",      "Italian",   ["news_narration"],                "Authoritative"),
    # pt-BR (Portuguese Brazil) -----------------------------------------
    ("pt-BR-FranciscaNeural",   "Francisca",   "Female", "pt-BR", "Portuguese (BR)","Brazilian",["customer_support"],             "Warm & natural"),
    ("pt-BR-ManuelaNeural",     "Manuela",     "Female", "pt-BR", "Portuguese (BR)","Brazilian",["educational"],                  "Clear & expressive"),
    ("pt-BR-AntonioNeural",     "Antonio",     "Male",   "pt-BR", "Portuguese (BR)","Brazilian",["news_narration", "sales"],      "Deep & confident"),
    ("pt-BR-NicolauNeural",     "Nicolau",     "Male",   "pt-BR", "Portuguese (BR)","Brazilian",["customer_support"],             "Friendly & warm"),
    # zh-CN (Mandarin Chinese) ------------------------------------------
    ("zh-CN-XiaoxiaoNeural",    "Xiaoxiao",    "Female", "zh-CN", "Chinese (Mandarin)", "Mandarin", ["customer_support"],         "Warm & lively"),
    ("zh-CN-XiaoyiNeural",      "Xiaoyi",      "Female", "zh-CN", "Chinese (Mandarin)", "Mandarin", ["asmr_calm"],                "Gentle & calm"),
    ("zh-CN-YunxiNeural",       "Yunxi",       "Male",   "zh-CN", "Chinese (Mandarin)", "Mandarin", ["news_narration"],           "Clear & authoritative"),
    ("zh-CN-YunjianNeural",     "Yunjian",     "Male",   "zh-CN", "Chinese (Mandarin)", "Mandarin", ["news_narration", "sales"],  "Passionate & energetic"),
    # ja-JP -------------------------------------------------------------
    ("ja-JP-NanamiNeural",      "Nanami",      "Female", "ja-JP", "Japanese",     "Japanese",  ["customer_support"],              "Polite & warm"),
    ("ja-JP-KeitaNeural",       "Keita",       "Male",   "ja-JP", "Japanese",     "Japanese",  ["news_narration"],                "Composed & clear"),
    ("ja-JP-AoiNeural",         "Aoi",         "Female", "ja-JP", "Japanese",     "Japanese",  ["asmr_calm", "educational"],     "Soft & natural"),
    ("ja-JP-DaichiNeural",      "Daichi",      "Male",   "ja-JP", "Japanese",     "Japanese",  ["sales"],                         "Confident & energetic"),
    # ko-KR -------------------------------------------------------------
    ("ko-KR-SunHiNeural",       "SunHi",       "Female", "ko-KR", "Korean",       "Korean",    ["customer_support"],              "Friendly & clear"),
    ("ko-KR-InJoonNeural",      "InJoon",      "Male",   "ko-KR", "Korean",       "Korean",    ["news_narration"],                "Composed & authoritative"),
    # nl-NL (Dutch) -----------------------------------------------------
    ("nl-NL-FennaNeural",       "Fenna",       "Female", "nl-NL", "Dutch",        "Dutch",     ["customer_support"],              "Friendly & natural"),
    ("nl-NL-MaartenNeural",     "Maarten",     "Male",   "nl-NL", "Dutch",        "Dutch",     ["news_narration"],                "Clear & authoritative"),
    # pl-PL (Polish) ----------------------------------------------------
    ("pl-PL-AgnieszkaNeural",   "Agnieszka",   "Female", "pl-PL", "Polish",       "Polish",    ["customer_support"],              "Warm & expressive"),
    ("pl-PL-MarekNeural",       "Marek",       "Male",   "pl-PL", "Polish",       "Polish",    ["news_narration"],                "Authoritative"),
    # ru-RU (Russian) ---------------------------------------------------
    ("ru-RU-SvetlanaNeural",    "Svetlana",    "Female", "ru-RU", "Russian",       "Russian",  ["customer_support"],              "Warm & professional"),
    ("ru-RU-DmitryNeural",      "Dmitry",      "Male",   "ru-RU", "Russian",       "Russian",  ["news_narration"],                "Deep & authoritative"),
    # ar-SA (Arabic) ----------------------------------------------------
    ("ar-SA-ZariyahNeural",     "Zariyah",     "Female", "ar-SA", "Arabic",        "Arabic",   ["customer_support"],              "Warm & clear"),
    ("ar-SA-HamedNeural",       "Hamed",       "Male",   "ar-SA", "Arabic",        "Arabic",   ["news_narration"],                "Deep & authoritative"),
]

EDGE_VOICES: list[dict[str, Any]] = [
    {
        "id":               f"edge-{d[0]}",
        "name":             d[1],
        "gender":           d[2],
        "language":         d[3],
        "language_name":    d[4],
        "accent":           d[5],
        "categories":       d[6],
        "style":            d[7],
        "provider":         "edge",
        "neural_name":      d[0],
        "requires_api_key": None,
        "available":        True,
    }
    for d in _EDGE_DATA
]

# ── Sarvam AI voices (auto-generated matrix) ──────────────────────────────────
# bulbul:v1 — 10 Indian languages, 5 speakers each
_SARVAM_LANGS: list[tuple[str, str]] = [
    ("hi-IN",  "Hindi (India)"),
    ("ta-IN",  "Tamil (India)"),
    ("te-IN",  "Telugu (India)"),
    ("bn-IN",  "Bengali (India)"),
    ("mr-IN",  "Marathi (India)"),
    ("kn-IN",  "Kannada (India)"),
    ("gu-IN",  "Gujarati (India)"),
    ("ml-IN",  "Malayalam (India)"),
    ("pa-IN",  "Punjabi (India)"),
    ("en-IN",  "English (India)"),
]

# (speaker_id, display_name, gender, style)
_SARVAM_SPEAKERS: list[tuple[str, str, str, str]] = [
    ("meera",   "Meera",   "Female", "Warm & conversational"),
    ("kalpana", "Kalpana", "Female", "Professional & clear"),
    ("diya",    "Diya",    "Female", "Youthful & expressive"),
    ("arvind",  "Arvind",  "Male",   "Confident & authoritative"),
    ("amol",    "Amol",    "Male",   "Friendly & approachable"),
]

def _lang_short(lang_name: str) -> str:
    return lang_name.split(" ")[0]

SARVAM_VOICES: list[dict[str, Any]] = [
    {
        "id":               f"sarvam-{lang}-{spk}",
        "name":             f"{spk_name} · {_lang_short(lang_name)}",
        "gender":           gender,
        "language":         lang,
        "language_name":    lang_name,
        "accent":           _lang_short(lang_name),
        "categories":       ["customer_support", "indian_regional"],
        "style":            style,
        "provider":         "sarvam",
        "neural_name":      spk,
        "requires_api_key": "SARVAM_API_KEY",
        "available":        bool(os.getenv("SARVAM_API_KEY")),
    }
    for lang, lang_name in _SARVAM_LANGS
    for spk, spk_name, gender, style in _SARVAM_SPEAKERS
]

# ── Local CPU voices (Kokoro / Piper) ─────────────────────────────────────────
LOCAL_VOICES: list[dict[str, Any]] = [
    {
        "id": "kokoro-af_sky", "name": "Sky (Kokoro)", "gender": "Female",
        "language": "en-US", "language_name": "English (US)", "accent": "American",
        "categories": ["customer_support", "sales"],
        "style": "Natural CPU voice", "provider": "kokoro",
        "neural_name": "af_sky", "requires_api_key": None, "available": True,
    },
    {
        "id": "kokoro-af_bella", "name": "Bella (Kokoro)", "gender": "Female",
        "language": "en-US", "language_name": "English (US)", "accent": "American",
        "categories": ["customer_support", "asmr_calm"],
        "style": "Warm & smooth CPU voice", "provider": "kokoro",
        "neural_name": "af_bella", "requires_api_key": None, "available": True,
    },
    {
        "id": "kokoro-am_adam", "name": "Adam (Kokoro)", "gender": "Male",
        "language": "en-US", "language_name": "English (US)", "accent": "American",
        "categories": ["sales", "news_narration"],
        "style": "Confident CPU voice", "provider": "kokoro",
        "neural_name": "am_adam", "requires_api_key": None, "available": True,
    },
    {
        "id": "kokoro-bf_emma", "name": "Emma-UK (Kokoro)", "gender": "Female",
        "language": "en-GB", "language_name": "English (UK)", "accent": "British",
        "categories": ["customer_support", "educational"],
        "style": "British English CPU voice", "provider": "kokoro",
        "neural_name": "bf_emma", "requires_api_key": None, "available": True,
    },
    {
        "id": "orpheus-af_sky", "name": "Orpheus Expressive", "gender": "Female",
        "language": "en-US", "language_name": "English (US)", "accent": "American",
        "categories": ["sales", "customer_support"],
        "style": "Emotion-tagged expressive", "provider": "kokoro",
        "neural_name": "af_sky", "requires_api_key": None, "available": True,
    },
    {
        "id": "piper-en_US-lessac-medium", "name": "Lessac (Piper)", "gender": "Male",
        "language": "en-US", "language_name": "English (US)", "accent": "American",
        "categories": ["educational", "news_narration"],
        "style": "Fast ONNX CPU synthesis", "provider": "piper",
        "neural_name": "en_US-lessac-medium", "requires_api_key": None, "available": True,
    },
    {
        "id": "piper-en_US-ryan-high", "name": "Ryan-High (Piper)", "gender": "Male",
        "language": "en-US", "language_name": "English (US)", "accent": "American",
        "categories": ["customer_support"],
        "style": "High-quality ONNX CPU", "provider": "piper",
        "neural_name": "en_US-ryan-high", "requires_api_key": None, "available": True,
    },
]


def get_full_catalog() -> list[dict[str, Any]]:
    """Return all voices ordered: Edge → Sarvam → Local."""
    return EDGE_VOICES + SARVAM_VOICES + LOCAL_VOICES


def get_voice_by_id(voice_id: str) -> dict[str, Any] | None:
    for v in get_full_catalog():
        if v["id"] == voice_id:
            return v
    return None


def filter_catalog(
    voices: list[dict[str, Any]],
    language: str | None = None,
    gender: str | None = None,
    provider: str | None = None,
    category: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    result = voices
    if language:
        result = [v for v in result if v["language"] == language]
    if gender:
        result = [v for v in result if v["gender"].lower() == gender.lower()]
    if provider:
        result = [v for v in result if v["provider"] == provider]
    if category:
        result = [v for v in result if category in v["categories"]]
    if search:
        q = search.lower()
        result = [
            v for v in result
            if q in v["name"].lower()
            or q in v["language_name"].lower()
            or q in v["accent"].lower()
            or q in v.get("style", "").lower()
        ]
    return result


def unique_languages(voices: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    for v in voices:
        seen[v["language"]] = v["language_name"]
    return sorted(
        [{"code": k, "name": v} for k, v in seen.items()],
        key=lambda x: x["name"],
    )
