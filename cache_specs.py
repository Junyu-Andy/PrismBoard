"""Killer-prompt cache.

The eight rehearsed demo prompts each get a serialised spec on disk. At
runtime we look up the user's query against this map (case- and
whitespace-insensitive). If the LLM call throws, the cached spec is loaded
as a fallback so the demo never freezes.

Run `python cache_specs.py rebuild` to regenerate the cache against the
live LLM (requires DEEPSEEK_API_KEY). The build will quietly skip prompts
that already have a saved spec; pass `--force` to overwrite.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Each entry: id, role, patient_id, actor_id, query, ctx_kwargs (filled at build)
KILLER_PROMPTS = [
    {"id": "doc_p001_24h",    "role": "doctor",  "patient_id": "P001", "actor_id": "D001",
     "query": "How has Wang Wei recovered in the last 24 hours?"},
    {"id": "doc_p002_glu_bp", "role": "doctor",  "patient_id": "P002", "actor_id": "D001",
     "query": "Is Li Xiuying's blood glucose correlated with her blood pressure?"},

    {"id": "nur_p001_4h",     "role": "nurse",   "patient_id": "P001", "actor_id": "N001",
     "query": "What do I need to do for Wang Wei in the next 4 hours?"},
    {"id": "nur_p002_glu",    "role": "nurse",   "patient_id": "P002", "actor_id": "N003",
     "query": "Is Li Xiuying due for a glucose check, and what else is urgent today?"},

    {"id": "pat_p001_dc",     "role": "patient", "patient_id": "P001", "actor_id": "P001",
     "query": "When can I be discharged?"},
    {"id": "pat_p002_heart",  "role": "patient", "patient_id": "P002", "actor_id": "P002",
     "query": "Will something happen to my heart?"},

    {"id": "fam_p001_bro",    "role": "family",  "patient_id": "P001", "actor_id": "Wang Tao",
     "query": "How is my brother doing today, can he be discharged tomorrow?"},
    {"id": "fam_p002_dau",    "role": "family",  "patient_id": "P002", "actor_id": "Li Min",
     "query": "How has my mum been over the last day, can I visit her today?"},
]

DEMO_NOW = datetime(2026, 5, 7, 10, 0)


# ---------------------------------------------------------------- normalisation
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _key(role: str, patient_id: str, query: str) -> str:
    return f"{role}|{patient_id}|{_norm(query)}"


# ---------------------------------------------------------------- public
def lookup(role: str, patient_id: str, query: str) -> Optional[dict]:
    """Return a cached spec for this (role, patient, query) tuple, if any."""
    k = _key(role, patient_id, query)
    for p in CACHE_DIR.glob("*.json"):
        blob = json.loads(p.read_text())
        if blob.get("key") == k:
            return blob.get("spec")
    return None


def list_cached() -> list[dict]:
    out = []
    for p in CACHE_DIR.glob("*.json"):
        blob = json.loads(p.read_text())
        out.append({"id": p.stem, "key": blob.get("key", "")})
    return out


# ---------------------------------------------------------------- builder (offline)
def _ctx_kwargs_for(prompt: dict, patient: dict, doctor=None, nurse=None,
                    family_relation: str = "relative") -> dict:
    out = {"patient_id": patient["patient_id"], "patient_name": patient["name"],
           "post_op_day": 2}
    if prompt["role"] == "doctor":
        out.update(actor_name=doctor["name"], department=doctor["department"])
    elif prompt["role"] == "nurse":
        out.update(actor_name=nurse["name"], nurse_id=nurse["id"],
                   nurse_level=nurse["level"], current_shift=nurse["current_shift"])
    elif prompt["role"] == "family":
        out.update(actor_name=prompt["actor_id"], family_relation=family_relation)
    return out


def rebuild(force: bool = False):
    # Imports live here so the runtime doesn't require openai/data unless rebuilding.
    from dotenv import load_dotenv
    load_dotenv()
    import data
    import llm

    family_relations = {"Wang Tao": "brother", "Li Min": "daughter"}

    for prompt in KILLER_PROMPTS:
        out_path = CACHE_DIR / f"{prompt['id']}.json"
        if out_path.exists() and not force:
            print(f"  skip   {prompt['id']:18s} (already cached)")
            continue

        patient = data.get_patient(prompt["patient_id"])
        doctor = nurse = None
        if prompt["role"] == "doctor":
            doctors = data.list_doctors()
            doctor = doctors[doctors["id"] == prompt["actor_id"]].iloc[0].to_dict()
        elif prompt["role"] == "nurse":
            nurses = data.list_nurses()
            nurse = nurses[nurses["id"] == prompt["actor_id"]].iloc[0].to_dict()

        ctx_kwargs = _ctx_kwargs_for(
            prompt, patient, doctor=doctor, nurse=nurse,
            family_relation=family_relations.get(prompt["actor_id"], "relative"),
        )

        # Patient symptom/emotional should not be cached (they go through safety.py).
        # Only cache the procedural patient prompts.
        if prompt["role"] == "patient" and prompt["id"] == "pat_p002_heart":
            print(f"  skip   {prompt['id']:18s} (handled by safety.py, not LLM)")
            continue

        try:
            spec = llm.generate_spec(
                role=prompt["role"], ctx_kwargs=ctx_kwargs,
                current_time=DEMO_NOW.strftime("%Y-%m-%d %H:%M:%S"),
                current_date=DEMO_NOW.strftime("%Y-%m-%d"),
                post_op_day=2, ampm="morning",
                user_query=prompt["query"],
            )
        except Exception as e:
            print(f"  FAIL   {prompt['id']:18s}  {e}")
            continue

        blob = {
            "key":   _key(prompt["role"], prompt["patient_id"], prompt["query"]),
            "role":  prompt["role"],
            "patient_id": prompt["patient_id"],
            "query": prompt["query"],
            "spec":  spec,
        }
        out_path.write_text(json.dumps(blob, indent=2, default=str))
        print(f"  ok     {prompt['id']:18s} -> {out_path.name}")


# ---------------------------------------------------------------- cli
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["rebuild", "list"])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.action == "list":
        for entry in list_cached():
            print(entry)
        sys.exit(0)
    if args.action == "rebuild":
        rebuild(force=args.force)
