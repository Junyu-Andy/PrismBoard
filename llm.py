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

MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# Placeholder strings the LLM sometimes emits when it gets lazy. If any
# of these appear in the spec we re-prompt once before giving up.
_LAZY_SINGLE_TOKENS = {
    "?", "-", "--", "...", "tbd", "n/a", "na",
    "unknown", "todo", "placeholder", "pending",
}
_LAZY_PHRASES = (
    "query result",
    "your text here",
    "lorem ipsum",
    "summary will appear",
    "summary here",
    "fill in",
    "to be determined",
)


def _looks_lazy(spec: dict) -> bool:
    """Return True if any layout component has placeholder content.

    We only check fields the renderer actually displays
    (config.value / config.content / config.label) and data_query,
    so the user's intent / reasoning text is not affected.
    """
    layout = spec.get("layout") or []
    for comp in layout:
        cfg = comp.get("config") or {}
        for key in ("value", "content", "label"):
            v = cfg.get(key)
            if isinstance(v, str):
                s = v.strip().lower()
                if s in _LAZY_SINGLE_TOKENS:
                    return True
                if any(p in s for p in _LAZY_PHRASES):
                    return True
        dq = comp.get("data_query")
        if isinstance(dq, str) and dq.lower().lstrip().startswith("select '"):
            # Catches SELECT 'query result' AS msg style placeholder SQL
            head = dq.lower()
            if any(p in head for p in (
                    "'query result'", "'placeholder'", "'tbd'",
                    "'summary'", "'foo'", "'n/a'")):
                return True
    return False


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


def generate_spec(role: str, ctx_kwargs: dict, current_time: str, current_date: str,
                  post_op_day: int, ampm: str, user_query: str) -> dict:
    """Produce a dashboard spec for the user's natural-language query.

    Retries once if the first call returns malformed JSON / no tool call.
    """
    system = prompts.build_master_system(
        role=role, ctx_kwargs=ctx_kwargs,
        current_time=current_time, current_date=current_date, post_op_day=post_op_day, ampm=ampm,
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_query},
    ]
    try:
        spec = _call_with_tool(messages)
    except LLMError:
        # Re-prompt once, asking for strict tool compliance.
        messages.append({
            "role": "user",
            "content": ("The previous response was malformed. Re-emit a valid "
                        "generate_dashboard tool call following the schema "
                        "exactly."),
        })
        spec = _call_with_tool(messages)

    # Lazy-content guard: if the model dumped 'query result' / 'placeholder'
    # / 'TBD' style strings into the spec, re-prompt once more for concrete
    # content. This is the most common cause of empty-looking dashboards.
    if _looks_lazy(spec):
        messages.append({
            "role": "assistant",
            "content": json.dumps(spec),
        })
        messages.append({
            "role": "user",
            "content": (
                "The previous spec contained placeholder strings such as "
                "'query result', 'TBD', or 'placeholder'. Regenerate the "
                "spec with concrete content drawn from real database "
                "tables. For text_summary panels, set config.content to "
                "actual prose that references concrete numbers (e.g. "
                "'18 of 21 scheduled doses administered on time'). For "
                "metric_card components, value must come from a real "
                "data_query, not a literal SELECT 'foo' AS bar. If you "
                "cannot fill a panel with real data, drop that panel."
            ),
        })
        try:
            spec = _call_with_tool(messages)
        except LLMError:
            pass  # Keep the previous (lazy) spec rather than crashing.
    return spec


def deepen_spec(role: str, ctx_kwargs: dict, current_time: str, current_date: str,
                post_op_day: int, ampm: str,
                current_spec: dict, direction: str) -> dict:
    system = prompts.build_master_system(
        role=role, ctx_kwargs=ctx_kwargs,
        current_time=current_time, current_date=current_date, post_op_day=post_op_day, ampm=ampm,
    )
    user = prompts.DEEPEN_PROMPT.format(
        deepen_direction=direction,
        current_spec_json=json.dumps(current_spec, indent=2, default=str),
    )
    return _call_with_tool([
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ])


def drilldown_spec(role: str, ctx_kwargs: dict, current_time: str, current_date: str,
                   post_op_day: int, ampm: str,
                   current_spec: dict,
                   entity_type: str, entity_id: str, entity_label: str) -> dict:
    system = prompts.build_master_system(
        role=role, ctx_kwargs=ctx_kwargs,
        current_time=current_time, current_date=current_date, post_op_day=post_op_day, ampm=ampm,
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
