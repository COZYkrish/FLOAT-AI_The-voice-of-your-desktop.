# brain.py — FLOAT AI Desktop Assistant
# Groq API client, intent router, and conversation history manager.

import re
import json
import logging
from typing import Optional
from groq import Groq

from config import (
    GROQ_API_KEY, GROQ_MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT, log
)

logger = logging.getLogger("FLOAT.brain")

# ─── Groq Client ──────────────────────────────────────────────────────────────
try:
    _client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except Exception as e:
    logger.error(f"Groq client init failed: {e}")
    _client = None

# ─── Conversation History ─────────────────────────────────────────────────────
_history: list[dict] = []          # list of {"role": ..., "content": ...}
MAX_HISTORY = 20                   # keep last 20 exchanges


def _trim_history() -> None:
    """Keep history within MAX_HISTORY entries (system prompt excluded)."""
    global _history
    if len(_history) > MAX_HISTORY * 2:
        _history = _history[-(MAX_HISTORY * 2):]


def ask_groq(user_text: str) -> str:
    """Send user_text to Groq and return the assistant reply."""
    if not _client:
        return "I can't connect to my AI brain right now. Please check your Groq API key."

    _history.append({"role": "user", "content": user_text})
    _trim_history()

    # Append current language enforcement
    from voice import CURRENT_LANG
    lang_instruction = (
        " You MUST respond entirely in Hindi (Devanagari script)." if CURRENT_LANG == "hi"
        else " You MUST respond entirely in English."
    )
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT + lang_instruction}] + _history

    try:
        response = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        reply = response.choices[0].message.content.strip()
        _history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        _history.pop()  # remove the failed user message
        return "I'm having trouble connecting. Please try again later."


def clear_history() -> None:
    """Reset conversation history."""
    global _history
    _history = []


# ─── Intent Router ────────────────────────────────────────────────────────────
Each entry: (compiled regex, handler key)
# Handler key is resolved in float.py against the module functions.

INTENT_PATTERNS: list[tuple] = [
    # System control
    (re.compile(r"(wifi|वाईफाई|वाइफाइ).*(on|off|enable|disable|चालू|बंद)|(on|off|enable|disable|चालू|बंद).*(wifi|वाईफाई|वाइफाइ)", re.I),   "wifi"),
    (re.compile(r"(bluetooth|ब्लूटूथ).*(on|off|enable|disable|चालू|बंद)|(on|off|enable|disable|चालू|बंद).*(bluetooth|ब्लूटूथ)", re.I), "bluetooth"),
    (re.compile(r"(volume|आवाज़|आवाज).*(up|down|set|to|बढ़ाओ|कम|करो|कितनी)|(up|down|set|to|बढ़ाओ|कम|करो|कितनी).*(volume|आवाज़|आवाज)|\b(\d+)\b", re.I),    "volume"),
    (re.compile(r"(brightness|रोशनी|ब्राइटनेस)", re.I),                      "brightness"),
    (re.compile(r"(open|खोलें|खोलो|खोलना|start|चालू).*(https?://|www\.|\w+\.com|youtube|whatsapp|gmail|google|netflix|github|reddit|twitter|instagram|facebook|linkedin|amazon|wikipedia|spotify|maps|chatgpt|यूट्यूब|व्हाट्सएप|गूगल|फेसबुक|इंस्टाग्राम)|(https?://|www\.|\w+\.com|youtube|whatsapp|gmail|google|netflix|github|reddit|twitter|instagram|facebook|linkedin|amazon|wikipedia|spotify|maps|chatgpt|यूट्यूब|व्हाट्सएप|गूगल|फेसबुक|इंस्टाग्राम).*(open|खोलें|खोलो|खोलना|start|चालू)", re.I),"open_site"),
    (re.compile(r"(open|खोलें|खोलो|खोलना|start|चालू)\s+([a-z\u0900-\u097F][\w\s\u0900-\u097F]*)|([a-z\u0900-\u097F][\w\s\u0900-\u097F]*)\s+(open|खोलें|खोलो|खोलना|चालू करो)", re.I),               "open_app"),
    (re.compile(r"(screenshot|screen shot|स्क्रीनशॉट)", re.I),          "screenshot"),
    (re.compile(r"(lock|लॉक).*(screen|my screen|computer|स्क्रीन)|(स्क्रीन लॉक)", re.I),"lock"),
    (re.compile(r"(shutdown|shut down|शटडाउन|कंप्यूटर बंद)", re.I),              "shutdown"),
    (re.compile(r"(restart|रीस्टार्ट)", re.I),                           "restart"),
    (re.compile(r"(sleep|स्लीप)", re.I),                             "sleep"),
    # Messaging — contacts
    (re.compile(r"(save|सेव|सुरक्षित).*(number|नंबर)|(number|नंबर).*(save|सेव|सुरक्षित)", re.I),             "save_contact"),
    (re.compile(r"(what|show|tell|बताओ|दिखाओ|क्या).*(number|नंबर)|(number|नंबर).*(what|show|tell|बताओ|दिखाओ|क्या)", re.I), "lookup_contact"),
    # Messaging — WhatsApp
    (re.compile(r"(whatsapp|व्हाट्सएप|संदेश|मैसेज|text)", re.I),       "whatsapp"),
    # Messaging — Email
    (re.compile(r"(send|भेजो|ईमेल करो).*(email|ईमेल|मेल)|(email|ईमेल|मेल).*(send|भेजो)", re.I),              "email"),
    (re.compile(r"(read|पढ़ो).*(email|mail|ईमेल|मेल)|(email|mail|ईमेल|मेल).*(read|पढ़ो)", re.I),    "read_email"),
    # Media
    (re.compile(r"(play|बजाओ|लगाओ|चलाओ|प्ले).+", re.I),                        "play_music"),
    (re.compile(r"(.+).*(play|बजाओ|लगाओ|चलाओ|प्ले)", re.I),                        "play_music"),
    (re.compile(r"(pause|stop|रोको|बंद).*(music|song|track|playing|गाना|गाने)|(music|song|track|playing|गाना|गाने).*(pause|stop|रोको|बंद)", re.I), "pause_music"),
    (re.compile(r"(next|skip|अगला).*(song|track|गाना)?", re.I),      "next_track"),
    (re.compile(r"(previous|prev|back|पिछला).*(song|track|गाना)?", re.I),"prev_track"),
    # Web
    (re.compile(r"(weather|वेदर|मौसम)", re.I),                           "weather"),
    (re.compile(r"(news|समाचार|ख़बरें|खबरें)", re.I),                              "news"),
    (re.compile(r"(search|google|सर्च|खोजो).+", re.I),             "search"),
    (re.compile(r"(wikipedia|विकिपीडिया)", re.I),                         "wikipedia"),
    # Files & Productivity
    (re.compile(r"(remind|याद दिलाना|रिमाइंडर)", re.I),       "reminder"),
    (re.compile(r"(todo|to-do|task|टास्क).*(add|जोड़ो|डालो|लिखो)|(add|जोड़ो|डालो|लिखो).*(todo|to-do|task|टास्क)", re.I), "todo"),
    (re.compile(r"(calculate|what is|क्या है|गणना|हिसाब).+", re.I), "calculate"),
    (re.compile(r"(timer|countdown|टाइमर)", re.I),                  "timer"),
    (re.compile(r"(stopwatch|स्टॉपवॉच)", re.I),                          "stopwatch"),
    (re.compile(r"(read|पढ़ो).*(file|फ़ाइल|फाइल|\.txt)|(file|फ़ाइल|फाइल|\.txt).*(read|पढ़ो)", re.I),              "read_file"),
    (re.compile(r"(clipboard|copy|paste|क्लिपबोर्ड|कॉपी|पेस्ट)", re.I),             "clipboard"),
    # Financial
    (re.compile(r"(add|spend|spent|खर्च).*(rs|rupees?|\$|रुपये|रु).*", re.I), "add_expense"),
    (re.compile(r"(how much|spend|खर्च|कितना).*(expense|summary|आज|महीने|month)", re.I), "expense_summary"),
    # Language
    (re.compile(r"(speak|switch|talk|change|टॉक|चेंज|स्विच|स्पीक|बात|turn).*(hindi|english|इंग्लिश|अंग्रेजी|हिंदी|हिन्दी)|(hindi|english|इंग्लिश|अंग्रेजी|हिंदी|हिन्दी).*(speak|switch|talk|change|टॉक|चेंज|स्विच|स्पीक|बात|turn)", re.I), "language"),
]


def route_intent(text: str) -> Optional[str]:
    """
    Fast-path keyword intent detection.
    Returns the intent key string, or None if no match (→ use Groq).
    """
    for pattern, intent_key in INTENT_PATTERNS:
        if pattern.search(text):
            return intent_key
    return None


def extract_entities(text: str, intent: str) -> dict:
    """
    Pull relevant entities from the command text for a given intent.
    Returns a dict of named slots.
    """
    text_lower = text.lower()
    entities: dict = {"raw": text}

    if intent == "volume":
        # Try to find a percentage number
        m = re.search(r"\b(\d{1,3})\b", text)
        if m:
            entities["level"] = int(m.group(1))
        elif any(w in text_lower for w in ["up", "बढ़ाओ", "ज्यादा"]):
            entities["direction"] = "up"
        elif any(w in text_lower for w in ["down", "कम"]):
            entities["direction"] = "down"

    elif intent in ("wifi", "bluetooth"):
        if any(w in text_lower for w in ["on", "enable", "चालू"]):
            entities["state"] = "on"
        else:
            entities["state"] = "off"

    elif intent == "open_app":
        # e.g. "open Chrome" → "chrome" or "Chrome खोलो" → "chrome"
        m = re.search(r"(?:open|खोलें|खोलो|खोलना|start|चालू)\s+([a-z\u0900-\u097F][\w\s\u0900-\u097F]*)", text_lower)
        if m:
            entities["app"] = m.group(1).strip()
        else:
            m2 = re.search(r"([a-z\u0900-\u097F][\w\s\u0900-\u097F]*)\s+(?:open|खोलें|खोलो|खोलना|चालू)", text_lower)
            if m2:
                entities["app"] = m2.group(1).strip()

    elif intent in ("whatsapp",):
        # Check for group message first:
        # "text the family group Happy Diwali"
        m_group = re.search(
            r"\b(?:text|whatsapp|message|send\s+(?:a\s+)?(?:whatsapp|message|text)\s+(?:to\s+)?)"
            r"(?:the\s+)?(.+?)\s+group\s+(.+)", text, re.I
        )
        if m_group:
            entities["group"] = m_group.group(1).strip()
            entities["message"] = m_group.group(2).strip()
            entities["is_group"] = True
        else:
            # "send a whatsapp to Mom saying I love you"
            m = re.search(
                r"\b(?:send\s+(?:a\s+)?(?:whatsapp|message|text)\s+to)\s+(\w+)\s+(?:saying\s+|that\s+)?(.+)",
                text, re.I
            )
            if not m:
                # "text Mom I'll be home late" / "whatsapp Dad meeting at 5"
                m = re.search(
                    r"\b(?:text|whatsapp|message)\s+(?:to\s+)?(\w+)\s+(?:saying\s+|that\s+)?(.+)",
                    text, re.I
                )
            if m:
                entities["contact"] = m.group(1)
                entities["message"] = m.group(2)
            else:
                # Contact only, no message: "text Mom"
                m = re.search(r"\b(?:text|whatsapp|message)\s+(?:to\s+)?(\w+)", text, re.I)
                if m:
                    entities["contact"] = m.group(1)

    elif intent == "save_contact":
        # "save Mom's number as +919876543210"
        m = re.search(
            r"(?:save|add)\s+(\w+)'?s?\s+(?:phone\s+)?number\s+(?:as\s+)?(\+?[\d\s-]+)",
            text, re.I
        )
        if m:
            entities["name"] = m.group(1)
            entities["phone"] = m.group(2).strip()

    elif intent == "lookup_contact":
        # "what's Mom's number"
        m = re.search(
            r"(?:what'?s?|get|show|tell\s+me)\s+(\w+)'?s?\s+(?:phone\s+)?number",
            text, re.I
        )
        if m:
            entities["name"] = m.group(1)

    elif intent == "reminder":
        # "remind me to X in N minutes/hours"
        m = re.search(r"(?:remind me\s+(?:to\s+)?(.+?)\s+in\s+(\d+)\s*(minute|hour|second))", text_lower)
        if m:
            entities["task"] = m.group(1)
            entities["amount"] = int(m.group(2))
            entities["unit"] = m.group(3)

    elif intent == "timer":
        m = re.search(r"(\d+)\s*(second|minute|hour)", text_lower)
        if m:
            entities["amount"] = int(m.group(1))
            entities["unit"] = m.group(2)

    elif intent in ("search", "wikipedia"):
        m = re.search(r"(?:search|google|wikipedia)\s+(?:for\s+)?(.+)", text_lower)
        if m:
            entities["query"] = m.group(1).strip()

    elif intent == "weather":
        m = re.search(r"(?:weather|वेदर|मौसम)\s+(?:in|at|for|में|का)\s+([a-z\s\u0900-\u097F]+)", text_lower)
        city_cand = ""
        if m:
            city_cand = m.group(1).strip()
        else:
            m2 = re.search(r"([a-z\s\u0900-\u097F]+)\s+(?:में|का|की)\s+(?:मौसम|वेदर|weather)", text_lower)
            if m2:
                city_cand = m2.group(1).strip()
        
        if city_cand:
            for w in ["आज", "कल", "today", "tomorrow", "now", "अभी"]:
                city_cand = city_cand.replace(w, "").strip()
            if city_cand:
                entities["city"] = city_cand

    elif intent == "calculate":
        # Extract the math expression
        m = re.search(r"(?:calculate|what\s+is)\s+(.+)", text_lower)
        if m:
            entities["expression"] = m.group(1).strip()

    elif intent == "brightness":
        m = re.search(r"(\d{1,3})", text)
        if m:
            entities["level"] = int(m.group(1))

    elif intent == "play_music":
        m = re.search(r"(?:play|प्ले|चलाओ|बजाओ|लगाओ)\s+(.+?)(?:\s+(?:on|पर)\s+(spotify|youtube|local))?$", text, re.I)
        if m:
            entities["song"] = m.group(1).strip()
            entities["source"] = (m.group(2) or "auto").lower()
        else:
            m2 = re.search(r"(.+?)(?:\s+(?:on|पर)\s+(spotify|youtube|local))?\s+(?:बजाओ|लगाओ|चलाओ|प्ले)", text, re.I)
            if m2:
                entities["song"] = m2.group(1).strip()
                entities["source"] = (m2.group(2) or "auto").lower()

    elif intent == "read_file":
        m = re.search(r"read\s+(?:file\s+)?(.+)", text, re.I)
        if m:
            entities["filename"] = m.group(1).strip()

    elif intent == "add_expense":
        m = re.search(r"\b(add|spend|spent)\s+(rs|rupees?|\$)?\s*(\d+(?:\.\d+)?)\s*(rs|rupees?)?\s*(?:to|on|for)\s+(.+?)(?:\s+expenses?)?\b", text, re.I)
        if m:
            entities["amount"] = float(m.group(3))
            entities["category"] = m.group(5).strip()

    elif intent == "expense_summary":
        if "today" in text_lower:
            entities["period"] = "today"
        else:
            entities["period"] = "month"

    return entities
