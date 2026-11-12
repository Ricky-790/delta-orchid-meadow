import json
import os
import random
import time
import urllib.error
import urllib.request

import jsonschema

from .prompts import SYSTEM_PROMPT

# One schema serves two jobs: structured output for the model call, and
# validation of its reply. No additionalProperties key so Gemini accepts it.
DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "source_persona": {
                        "type": "string",
                        "enum": ["dev", "anjali", "bablu", "assumed"],
                    },
                    "status": {
                        "type": "string",
                        "enum": ["confirmed", "conflicting", "assumed"],
                    },
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "source_persona", "status", "evidence"],
            },
        },
        "conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "between": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["dev", "anjali", "bablu", "register"],
                        },
                    },
                    "about": {"type": "string"},
                    "resolution": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["between", "about", "resolution", "evidence"],
            },
        },
        "constraints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "evidence"],
            },
        },
        "budget_inr": {"type": "number", "nullable": True},
        "budget_evidence": {"type": "array", "items": {"type": "string"}},
        "plan": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "requirements",
        "conflicts",
        "constraints",
        "budget_inr",
        "budget_evidence",
        "plan",
        "open_questions",
    ],
}


def build_prompt(quotes, findings):
    lines = [
        SYSTEM_PROMPT,
        "",
        "Register findings (computed by code; the only numbers you may use):",
    ]
    lines.extend(f"- {f}" for f in findings)
    lines.append("")
    lines.append("Interview quotes:")
    for q in quotes:
        lines.append(f"[{q['ref']}] Q: {q['question']} A: {q['text']}")
    return "\n".join(lines)


def _call(base_url, model, key, prompt, timeout_s):
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": DRAFT_SCHEMA,
        },
    }
    request = urllib.request.Request(
        f"{base_url}/models/{model}:generateContent?key={key}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        data = json.loads(response.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def extract(cfg, quotes, findings, root):
    """Use Gemini to turn quotes into a structured draft."""
    llm = cfg["llm"]
    key = os.environ.get(llm["api_key_env"], "")
    if not key:
        raise RuntimeError("No API key in the environment; cannot extract.")

    prompt = build_prompt(quotes, findings)
    models = [
        m
        for m in (llm["model"], llm.get("fallback_model"), llm.get("last_resort_model"))
        if m
    ]
    last_error = None
    for model in models:
        for attempt in range(3):
            try:
                text = _call(llm["base_url"], model, key, prompt, llm.get("timeout_s", 120))
                draft = json.loads(text)
                jsonschema.validate(draft, DRAFT_SCHEMA)
                return draft, f"live {model}"
            except urllib.error.HTTPError as exc:
                last_error = f"{model}: {exc}"
                if exc.code != 503 or attempt == 2:
                    break
                time.sleep(2**attempt + random.uniform(0, 0.5))
            except Exception as exc:
                last_error = f"{model}: {getattr(exc, 'message', None) or exc}"
                break
    raise RuntimeError(f"LLM extraction failed: {last_error}")
