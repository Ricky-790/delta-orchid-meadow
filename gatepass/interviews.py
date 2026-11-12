import json
import os
import urllib.request
from pathlib import Path

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
    lines = [SYSTEM_PROMPT, "", "Register findings (computed by code; the only numbers you may use):"]
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
    """One real LLM call turns quotes into a Draft. Cache when it exists."""
    cache = root / cfg["cache_path"]
    if cache.exists():
        return json.loads(cache.read_text()), "cache"

    llm = cfg["llm"]
    key = os.environ.get(llm["api_key_env"], "")
    if not key:
        raise RuntimeError(
            "No API key in the environment and no LLM cache; cannot extract."
        )

    prompt = build_prompt(quotes, findings)
    models = [m for m in (llm["model"], llm.get("fallback_model")) if m]
    last_error = None
    for model in models:
        for attempt in range(2):
            try:
                text = _call(
                    llm["base_url"], model, key, prompt, llm.get("timeout_s", 120)
                )
            except Exception as exc:
                last_error = f"{model}: {exc}"
                continue
            try:
                draft = json.loads(text)
                jsonschema.validate(draft, DRAFT_SCHEMA)
            except Exception as exc:
                message = getattr(exc, "message", None) or str(exc)
                last_error = f"{model} schema: {message}"
                prompt += (
                    f"\n\nYour previous reply failed validation: {message}. "
                    "Reply again with valid JSON matching the schema exactly."
                )
                continue
            cache.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n")
            return draft, f"live {model}"
    raise RuntimeError(f"LLM extraction failed: {last_error}")
