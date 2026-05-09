"""Patient-side safety router and fixed response cards.

Every patient-side NL question goes through `route_patient_question` first.
The classifier (in llm.py) is intentionally biased toward `symptom`: a false
positive only causes an unnecessary nurse call, while a false negative could
let the LLM produce medical advice. We never let the LLM answer symptom or
emotional questions directly - those always render fixed cards.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import data
import llm

QUESTIONS_LOG = Path(__file__).parent / "data" / "patient_questions.csv"


# ---------------------------------------------------------------- routing
def route_patient_question(question: str) -> str:
    """Classify; default to 'symptom' if anything goes wrong (safety-first)."""
    try:
        return llm.classify_patient_question(question)
    except Exception:
        return "symptom"


# ---------------------------------------------------------------- audit log
def log_patient_question(patient_id: str, question: str,
                         classification: str, nurse_id: str | None) -> None:
    row = {
        "patient_id":         patient_id,
        "asked_at":           datetime.now().isoformat(timespec="seconds"),
        "question":           question,
        "classification":     classification,
        "routed_to_nurse_id": nurse_id or "",
    }
    if QUESTIONS_LOG.exists():
        df = pd.read_csv(QUESTIONS_LOG)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    df.to_csv(QUESTIONS_LOG, index=False)


# ---------------------------------------------------------------- on-call lookup
def on_call_nurse_for(patient_id: str) -> dict:
    """Pick the patient's primary nurse if currently on shift, else any nurse
    on the morning shift."""
    patient = data.get_patient(patient_id)
    nurses = data.list_nurses()
    primary = nurses[nurses["id"] == patient["primary_nurse_id"]]
    if not primary.empty and primary.iloc[0]["current_shift"] == "morning":
        return primary.iloc[0].to_dict()
    morning = nurses[nurses["current_shift"] == "morning"]
    if not morning.empty:
        return morning.iloc[0].to_dict()
    return nurses.iloc[0].to_dict()


# ---------------------------------------------------------------- fixed cards
def render_symptom_card(question: str, patient_id: str) -> None:
    nurse = on_call_nurse_for(patient_id)
    log_patient_question(patient_id, question, "symptom", nurse["id"])
    with st.container(border=True):
        st.markdown("### A nurse is on the way")
        st.markdown(
            f"I have already notified **{nurse['name']}** "
            f"({nurse['level']} nurse, {nurse['current_shift']} shift). "
            "She will come to your bedside within a few minutes."
        )
        st.markdown(
            "I do not give medical opinions on how you are feeling - "
            "that is your nurse's job. Please rest while you wait."
        )
        if st.button("Call nurse again", type="primary", key="call_again_symptom"):
            log_patient_question(patient_id, question + " [recall]",
                                 "symptom", nurse["id"])
            st.success(f"{nurse['name']} has been paged again.")


def render_emotional_card(question: str, patient_id: str) -> None:
    nurse = on_call_nurse_for(patient_id)
    log_patient_question(patient_id, question, "emotional", nurse["id"])
    with st.container(border=True):
        st.markdown("### You are not alone")
        st.markdown(
            "It is normal to feel uneasy after surgery. I will not pretend "
            "I can tell you everything will be fine - I can connect you "
            "with someone who can actually help."
        )
        cols = st.columns(2)
        with cols[0]:
            if st.button(f"Call {nurse['name']}", key="call_nurse_emotional",
                         type="primary"):
                log_patient_question(patient_id, question + " [nurse call]",
                                     "emotional", nurse["id"])
                st.success(f"{nurse['name']} has been paged.")
        with cols[1]:
            if st.button("Message my family", key="call_family_emotional"):
                log_patient_question(patient_id, question + " [family msg]",
                                     "emotional", None)
                st.success("A short status update was sent to your family.")


def render_chitchat_card(question: str) -> None:
    with st.container(border=True):
        st.markdown(
            "I am the post-op information board, not a chatbot. "
            "Try asking about your schedule, today's medication, or when "
            "your family can visit."
        )
