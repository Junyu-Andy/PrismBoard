"""DeepSeek client + spec generation (tool use) + patient question classifier.

DeepSeek exposes an OpenAI-compatible chat-completions endpoint at
https://api.deepseek.com. We use deepseek-chat (V3); reasoner (R1) is
intentionally avoided because its tool-use is unreliable.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from openai import OpenAI

import prompts

MODEL = "deepseek-chat"


# --------------------------------------------------------------------- client
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is not None:
        return _client
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not set in environment.")
    _client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    return _client


# --------------------------------------------------------------------- spec generator
class LLMError(Exception):
    pass


def _call_with_tool(messages: list[dict]) -> dict:
    """Single chat completion forced to call generate_dashboard."""
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=[prompts.GENERATE_DASHBOARD_TOOL],
        tool_choice={"type": "function",
                     "function": {"name": "generate_dashboard"}},
        temperature=0,
    )
    msg = resp.choices[0].message
    if not msg.tool_calls:
        raise LLMError("Model returned no tool call.")
    args = msg.tool_calls[0].function.arguments
    try:
        return json.loads(args)
    except json.JSONDecodeError as e:
        raise LLMError(f"Tool arguments not valid JSON: {e}") from e


def generate_spec(role: str, ctx_kwargs: dict, current_time: str,
                  post_op_day: int, ampm: str, user_query: str) -> dict:
    """Produce a dashboard spec for the user's natural-language query.

    Retries once if the first call returns malformed JSON / no tool call.
    """
    system = prompts.build_master_system(
        role=role, ctx_kwargs=ctx_kwargs,
        current_time=current_time, post_op_day=post_op_day, ampm=ampm,
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_query},
    ]
    try:
        return _call_with_tool(messages)
    except LLMError:
        # Re-prompt once, asking for strict tool compliance.
        messages.append({
            "role": "user",
            "content": ("The previous response was malformed. Re-emit a valid "
                        "generate_dashboard tool call following the schema "
                        "exactly."),
        })
        return _call_with_tool(messages)


def deepen_spec(role: str, ctx_kwargs: dict, current_time: str,
                post_op_day: int, ampm: str,
                current_spec: dict, direction: str) -> dict:
    system = prompts.build_master_system(
        role=role, ctx_kwargs=ctx_kwargs,
        current_time=current_time, post_op_day=post_op_day, ampm=ampm,
    )
    user = prompts.DEEPEN_PROMPT.format(
        deepen_direction=direction,
        current_spec_json=json.dumps(current_spec, indent=2, default=str),
    )
    return _call_with_tool([
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ])


def drilldown_spec(role: str, ctx_kwargs: dict, current_time: str,
                   post_op_day: int, ampm: str,
                   current_spec: dict,
                   entity_type: str, entity_id: str, entity_label: str) -> dict:
    system = prompts.build_master_system(
        role=role, ctx_kwargs=ctx_kwargs,
        current_time=current_time, post_op_day=post_op_day, ampm=ampm,
    )
    user = prompts.DRILLDOWN_PROMPT.format(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        current_spec_json=json.dumps(current_spec, indent=2, default=str),
    )
    return _call_with_tool([
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ])


# --------------------------------------------------------------------- classifier
VALID_CLASSES = {"procedural", "symptom", "emotional", "chitchat"}


def classify_patient_question(question: str) -> str:
    """Lightweight classifier for the patient-side safety router."""
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user",
             "content": prompts.PATIENT_QUESTION_CLASSIFIER_PROMPT.format(
                 question=question)},
        ],
        temperature=0,
        max_tokens=8,
    )
    raw = (resp.choices[0].message.content or "").strip().lower()
    # First word, stripped of punctuation
    token = raw.split()[0] if raw else ""
    token = "".join(ch for ch in token if ch.isalpha())
    return token if token in VALID_CLASSES else "symptom"
