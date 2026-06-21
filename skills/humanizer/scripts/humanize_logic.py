import os
import re
import sys
import json
import urllib.request
import urllib.error

AI_JARGON_REPLACEMENTS = {
    r"\bdelve\b": "explore",
    r"\bdelves\b": "explores",
    r"\bdelving\b": "exploring",
    r"\btapestry\b": "complexity",
    r"\btestament\b": "proof",
    r"\bfurthermore\b": "also",
    r"\bmoreover\b": "in addition",
    r"\butilize\b": "use",
    r"\butilizes\b": "uses",
    r"\butilizing\b": "using",
    r"\bfacilitate\b": "help",
    r"\bfacilitates\b": "helps",
    r"\bfacilitating\b": "helping",
    r"\bunderscores\b": "highlights",
    r"\bunderscore\b": "highlight",
    r"\bpivotal\b": "key",
    r"\bexhibit\b": "show",
    r"\bexhibits\b": "shows",
    r"\bexhibiting\b": "showing",
}

AI_CONVERSATIONAL_FILLERS = [
    r"^(?:certainly|absolutely|of course|sure|here is|here's)[!,\s]*",
    r"(?:in conclusion|to summarize|to sum up|in summary)[,\s]*",
    r"it is important to (?:note|remember|keep in mind) that\s*",
    r"please note that\s*",
]

def humanize_text_local(text, tone="conversational", intensity="medium"):
    refined = text
    for pattern in AI_CONVERSATIONAL_FILLERS:
        refined = re.sub(pattern, "", refined, flags=re.IGNORECASE)
    for pattern, replacement in AI_JARGON_REPLACEMENTS.items():
        refined = re.sub(pattern, replacement, refined, flags=re.IGNORECASE)
    refined = re.sub(r"\s+", " ", refined).strip()
    if tone == "casual":
        refined = refined.replace("do not", "don't").replace("cannot", "can't").replace("is not", "isn't")
    return refined

def humanize_text_llm(text, tone="conversational", intensity="medium"):
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                data=json.dumps({
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"Humanize the following text to sound natural, conversational, and authentic. "
                                f"Remove AI boilerplate. Target tone: {tone}, intensity: {intensity}.\n\n"
                                f"Text: {text}"
                            ),
                        }
                    ],
                }).encode("utf-8")
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["content"][0]["text"].strip(), "llm (anthropic)"
        except Exception:
            pass

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"You are a professional editor. Humanize input text. Target tone: {tone}, intensity: {intensity}."
                            ),
                        },
                        {"role": "user", "content": text},
                    ],
                }).encode("utf-8")
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"].strip(), "llm (openai)"
        except Exception:
            pass

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            req = urllib.request.Request(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": (
                                        f"Humanize the following text to sound natural and conversational. "
                                        f"Target tone: {tone}, intensity: {intensity}.\n\n"
                                        f"Text: {text}"
                                    )
                                }
                            ]
                        }
                    ]
                }).encode("utf-8")
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"].strip(), "llm (gemini)"
        except Exception:
            pass

    return None

def humanize(text, tone="conversational", intensity="medium"):
    llm_result = humanize_text_llm(text, tone, intensity)
    if llm_result:
        refined_text, engine = llm_result
    else:
        refined_text = humanize_text_local(text, tone, intensity)
        engine = "local rule-based engine"

    return {
        "original_text": text,
        "humanized_text": refined_text,
        "tone": tone,
        "intensity": intensity,
        "engine": engine,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python humanize_logic.py <text>")
        sys.exit(1)
    
    input_text = sys.argv[1]
    res = humanize(input_text)
    print(json.dumps(res, indent=2))
