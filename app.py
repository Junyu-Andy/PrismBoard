"""Streamlit entry for the PrismBoard demo.

Phase 1 skeleton: sidebar (role + patient + actor selection), main area
(NL input + render placeholder). LLM/render wiring lands in Phase 2.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

import data
import llm
import renderer

# Demo time anchor must match seed.py
DEMO_NOW = datetime(2026, 5, 7, 10, 0)
SURGERY_START = datetime(2026, 5, 4, 13, 0)


def _post_op_day(now: datetime, surgery_start: datetime) -> int:
    delta = now - surgery_start
    return max(0, delta.days)


def _ampm(now: datetime) -> str:
    return "morning" if now.hour < 12 else ("afternoon" if now.hour < 18 else "evening")


def _setup_page():
    st.set_page_config(
        page_title="PrismBoard - Generative Post-op Care Dashboard",
        page_icon=None,
        layout="wide",
    )


def _sidebar():
    st.sidebar.title("PrismBoard")
    st.sidebar.caption("Generative post-op care dashboard - demo")

    # Time anchor
    st.sidebar.markdown(
        f"**Now:** {DEMO_NOW.strftime('%a %Y-%m-%d %H:%M')}  \n"
        f"**POD#{_post_op_day(DEMO_NOW, SURGERY_START)} ({_ampm(DEMO_NOW)})**"
    )
    st.sidebar.divider()

    # Role
    role = st.sidebar.radio(
        "Role",
        options=["doctor", "nurse", "patient", "family"],
        format_func=lambda r: r.capitalize(),
        index=0,
        key="role",
    )

    # Patient
    patients = data.list_patients()
    primary = patients[patients["id"].isin(["P001", "P002"])]
    patient_label = {row["id"]: f"{row['name']} ({row['id']}) - {row['primary_diagnosis']}"
                     for _, row in primary.iterrows()}
    patient_id = st.sidebar.selectbox(
        "Patient",
        options=list(patient_label.keys()),
        format_func=lambda pid: patient_label[pid],
        key="patient_id",
    )

    # Actor binding (who is logged in)
    actor_id = None
    actor_label = None
    if role == "doctor":
        docs = data.list_doctors()
        opts = list(docs["id"])
        actor_id = st.sidebar.selectbox(
            "Logged in as",
            options=opts,
            format_func=lambda d: f"{d} - {docs[docs['id']==d].iloc[0]['name']} ({docs[docs['id']==d].iloc[0]['department']})",
            index=0,
            key="actor_id",
        )
        actor_label = docs[docs["id"] == actor_id].iloc[0]["name"]
    elif role == "nurse":
        nurses = data.list_nurses()
        opts = list(nurses["id"])
        # Default to the patient's primary nurse
        primary_nurse = data.get_patient(patient_id).get("primary_nurse_id")
        default_idx = opts.index(primary_nurse) if primary_nurse in opts else 0
        actor_id = st.sidebar.selectbox(
            "Logged in as",
            options=opts,
            format_func=lambda n: f"{n} - {nurses[nurses['id']==n].iloc[0]['name']} ({nurses[nurses['id']==n].iloc[0]['current_shift']})",
            index=default_idx,
            key="actor_id",
        )
        actor_label = nurses[nurses["id"] == actor_id].iloc[0]["name"]
    elif role == "patient":
        actor_id = patient_id
        actor_label = data.get_patient(patient_id)["name"]
        st.sidebar.markdown(f"**Logged in as:** {actor_label}")
    elif role == "family":
        # Mock family roster derived from family_communications
        family_for = {
            "P001": [("Liu Jia", "wife"), ("Wang Tao", "brother")],
            "P002": [("Li Min", "daughter"), ("Li Qiang", "son")],
        }
        opts = family_for.get(patient_id, [("Family", "relative")])
        choice = st.sidebar.selectbox(
            "Logged in as",
            options=range(len(opts)),
            format_func=lambda i: f"{opts[i][0]} ({opts[i][1]})",
            key="actor_id_family",
        )
        actor_id = opts[choice][0]
        actor_label = opts[choice][0]
        st.session_state["family_relation"] = opts[choice][1]

    st.sidebar.divider()

    # API key status
    key_present = bool(os.environ.get("DEEPSEEK_API_KEY"))
    if key_present:
        st.sidebar.success("DEEPSEEK_API_KEY loaded")
    else:
        st.sidebar.error("DEEPSEEK_API_KEY missing - set it in .env")

    return {
        "role": role,
        "patient_id": patient_id,
        "actor_id": actor_id,
        "actor_label": actor_label,
        "now": DEMO_NOW,
        "post_op_day": _post_op_day(DEMO_NOW, SURGERY_START),
        "ampm": _ampm(DEMO_NOW),
    }


def _header(ctx: dict):
    patient = data.get_patient(ctx["patient_id"])
    cols = st.columns([3, 2, 2])
    with cols[0]:
        st.markdown(
            f"### {patient['name']}  \n"
            f"{patient['age']}{patient['gender']} - {patient['primary_diagnosis']}"
        )
        st.caption(patient["profile_summary"])
    with cols[1]:
        st.markdown(
            f"**Surgery:** {patient['surgery_type']}  \n"
            f"**Ward / Bed:** {patient['ward']} / {patient['bed']}"
        )
    with cols[2]:
        st.markdown(
            f"**Role:** {ctx['role'].capitalize()}  \n"
            f"**You:** {ctx['actor_label']}"
        )


def _build_ctx_kwargs(ctx: dict) -> dict:
    """Assemble the kwargs needed to format role context / permission strings."""
    patient = data.get_patient(ctx["patient_id"])
    out = {
        "patient_id":   ctx["patient_id"],
        "patient_name": patient["name"],
        "post_op_day":  ctx["post_op_day"],
    }
    if ctx["role"] == "doctor":
        doc_df = data.list_doctors()
        row = doc_df[doc_df["id"] == ctx["actor_id"]].iloc[0]
        out.update(actor_name=row["name"], department=row["department"])
    elif ctx["role"] == "nurse":
        nu_df = data.list_nurses()
        row = nu_df[nu_df["id"] == ctx["actor_id"]].iloc[0]
        out.update(
            actor_name=row["name"],
            nurse_id=row["id"],
            nurse_level=row["level"],
            current_shift=row["current_shift"],
        )
    elif ctx["role"] == "family":
        out.update(
            actor_name=ctx["actor_label"],
            family_relation=st.session_state.get("family_relation", "relative"),
        )
    return out


def _main_panel(ctx: dict):
    st.subheader("Ask the dashboard")
    placeholder = {
        "doctor":  "e.g. How has Wang Wei recovered in the last 24 hours?",
        "nurse":   "e.g. What do I need to do in the next 4 hours?",
        "patient": "e.g. When can I be discharged?",
        "family":  "e.g. How is mum doing today, can I visit?",
    }[ctx["role"]]

    query = st.text_input("Natural language query",
                          placeholder=placeholder, key="nl_query")
    submitted = st.button("Generate", type="primary")

    if submitted and query:
        ctx_kwargs = _build_ctx_kwargs(ctx)
        with st.spinner("Generating dashboard ..."):
            try:
                spec = llm.generate_spec(
                    role=ctx["role"],
                    ctx_kwargs=ctx_kwargs,
                    current_time=ctx["now"].strftime("%a %Y-%m-%d %H:%M"),
                    post_op_day=ctx["post_op_day"],
                    ampm=ctx["ampm"],
                    user_query=query,
                )
            except Exception as e:
                st.error(f"LLM call failed: {e}")
                return
        st.session_state["last_spec"] = spec

    spec = st.session_state.get("last_spec")
    if spec:
        renderer.render_spec(spec, ctx)


def main():
    load_dotenv()
    _setup_page()

    # Surface a friendly error if the user forgot to seed.
    try:
        data.get_conn()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    ctx = _sidebar()
    _header(ctx)
    st.divider()
    _main_panel(ctx)


if __name__ == "__main__":
    main()
