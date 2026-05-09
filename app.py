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

import cache_specs
import data
import llm
import renderer
import safety

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

    patients = data.list_patients()
    primary = patients[patients["patient_id"].isin(["P001", "P002"])]
    patient_label = {row["patient_id"]: f"{row['name']} ({row['patient_id']}) - {row['primary_diagnosis']}"
                     for _, row in primary.iterrows()}

    actor_id = None
    actor_label = None
    patient_id = None

    if role == "doctor":
        # Doctor picks a patient to look at, then picks which doctor they are.
        patient_id = st.sidebar.selectbox(
            "Patient", options=list(patient_label.keys()),
            format_func=lambda pid: patient_label[pid], key="doctor_patient_id",
        )
        docs = data.list_doctors()
        actor_id = st.sidebar.selectbox(
            "Logged in as",
            options=list(docs["id"]),
            format_func=lambda d: f"{d} - {docs[docs['id']==d].iloc[0]['name']} "
                                  f"({docs[docs['id']==d].iloc[0]['department']})",
            key="doctor_actor_id",
        )
        actor_label = docs[docs["id"] == actor_id].iloc[0]["name"]

    elif role == "nurse":
        # Nurse picks a patient to look at, then picks which nurse they are.
        patient_id = st.sidebar.selectbox(
            "Patient", options=list(patient_label.keys()),
            format_func=lambda pid: patient_label[pid], key="nurse_patient_id",
        )
        nurses = data.list_nurses()
        opts = list(nurses["id"])
        primary_nurse = data.get_patient(patient_id).get("primary_nurse_id")
        default_idx = opts.index(primary_nurse) if primary_nurse in opts else 0
        actor_id = st.sidebar.selectbox(
            "Logged in as", options=opts,
            format_func=lambda n: f"{n} - {nurses[nurses['id']==n].iloc[0]['name']} "
                                  f"({nurses[nurses['id']==n].iloc[0]['current_shift']})",
            index=default_idx, key="nurse_actor_id",
        )
        actor_label = nurses[nurses["id"] == actor_id].iloc[0]["name"]

    elif role == "patient":
        # The actor IS the patient. Picking "Logged in as" picks the patient.
        patient_id = st.sidebar.selectbox(
            "Logged in as", options=list(patient_label.keys()),
            format_func=lambda pid: patient_label[pid], key="patient_self_id",
        )
        actor_id = patient_id
        actor_label = data.get_patient(patient_id)["name"]

    elif role == "family":
        # Family identity is bound to a single patient. There is NO patient
        # picker - you log in as a specific family member and that fixes
        # which patient you can see.
        FAMILY_ROSTER = [
            ("Liu Jia",  "wife",     "P001"),
            ("Wang Tao", "brother",  "P001"),
            ("Li Min",   "daughter", "P002"),
            ("Li Qiang", "son",      "P002"),
        ]
        idx = st.sidebar.selectbox(
            "Logged in as",
            options=range(len(FAMILY_ROSTER)),
            format_func=lambda i: (
                f"{FAMILY_ROSTER[i][0]} ({FAMILY_ROSTER[i][1]} of "
                f"{data.get_patient(FAMILY_ROSTER[i][2])['name']})"
            ),
            key="family_actor_idx",
        )
        name, rel, pid = FAMILY_ROSTER[idx]
        patient_id = pid
        actor_id = name
        actor_label = name
        st.session_state["family_relation"] = rel
        st.sidebar.caption(
            "You can only see information for the patient you are related to."
        )

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
    st.caption("Demo data only - patients, vitals, labs, meds and tasks "
               "are all synthetic.")


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


def _examples_for(role: str, patient_name: str) -> list[str]:
    p = patient_name
    return {
        "doctor": [
            f"How has {p} recovered in the last 24 hours?",
            f"Find anomalies in {p}'s vitals since surgery",
            f"Summarise {p}'s medication adherence and any missed doses",
        ],
        "nurse": [
            f"What do I need to do for {p} in the next 4 hours?",
            f"Are any of {p}'s vitals out of range right now?",
            f"What medication is {p} due to receive this shift?",
        ],
        "patient": [
            "When can I be discharged?",
            "What time will my next medication arrive?",
            "When can my family visit?",
        ],
        "family": [
            f"How has {p} been over the last day, can I visit?",
            "What is the plan for today?",
            "Did the doctor leave any new instructions?",
        ],
    }[role]


def _main_panel(ctx: dict):
    st.subheader("Ask the dashboard")

    patient_name = data.get_patient(ctx["patient_id"])["name"]

    # Scope banner: tell the user explicitly which patient and actor the
    # next query will run under. Avoids the "I asked about Li Xiuying but
    # the sidebar still has Wang Wei selected" surprise.
    scope_note = {
        "doctor":  f"Asking as **{ctx['actor_label']}** about **{patient_name}** "
                   f"({ctx['patient_id']}). To switch patients, use the sidebar.",
        "nurse":   f"Asking as **{ctx['actor_label']}** about **{patient_name}** "
                   f"({ctx['patient_id']}). Cross-patient ward views are not "
                   "supported in this demo - pick the patient in the sidebar first.",
        "patient": f"You are signed in as **{patient_name}**. "
                   "We will never give a medical opinion - any concern routes "
                   "straight to a nurse.",
        "family":  f"Asking as **{ctx['actor_label']}** about **{patient_name}** "
                   f"({ctx['patient_id']}). Some clinical detail is restricted "
                   "to the medical team.",
    }[ctx["role"]]
    st.info(scope_note)

    # If a chip was clicked on the previous run, copy its text into the
    # input widget BEFORE the widget is instantiated this run (otherwise
    # Streamlit refuses the assignment).
    preset = st.session_state.pop("_preset_query", None)
    auto_run = st.session_state.pop("_auto_run", None)
    if preset is not None:
        st.session_state["nl_query"] = preset

    # Example chips (one-click prompts the user can run as-is)
    st.caption("Quick prompts (click to fill and run):")
    examples = _examples_for(ctx["role"], patient_name)
    chip_cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        with chip_cols[i]:
            if st.button(ex, key=f"chip_{ctx['role']}_{i}",
                         use_container_width=True):
                st.session_state["_preset_query"] = ex
                st.session_state["_auto_run"]    = ex
                st.rerun()

    placeholder = {
        "doctor":  f"e.g. How has {patient_name} recovered in the last 24 hours?",
        "nurse":   f"e.g. What do I need to do for {patient_name} in the next 4 hours?",
        "patient": "e.g. When can I be discharged?",
        "family":  f"e.g. How is {patient_name} doing today, can I visit?",
    }[ctx["role"]]

    query = st.text_input("Natural language query",
                          placeholder=placeholder, key="nl_query")
    submitted = st.button("Generate", type="primary")

    # If a chip queued an auto-run, fire it now (after widget render).
    if auto_run:
        submitted = True
        query = auto_run

    if submitted and query:
        # Patient-side safety router runs BEFORE any spec generation.
        if ctx["role"] == "patient":
            with st.spinner("Routing your question ..."):
                cls = safety.route_patient_question(query)
            st.session_state["last_classification"] = cls
            if cls in ("symptom", "emotional", "chitchat"):
                # Bypass spec generation entirely.
                st.session_state["last_spec"] = None
                st.session_state["last_safety_question"] = query
                st.session_state["last_safety_class"] = cls
            else:  # procedural -> normal spec generation
                _generate_and_store(ctx, query)
        else:
            _generate_and_store(ctx, query)

    # Render either a safety card (patient symptom/emotional/chitchat) or a spec.
    if ctx["role"] == "patient" and st.session_state.get("last_safety_class") in (
            "symptom", "emotional", "chitchat"):
        cls = st.session_state["last_safety_class"]
        q   = st.session_state.get("last_safety_question", "")
        st.caption(f"Classified as **{cls}** - response is a fixed safety card, "
                   f"the LLM never produced a medical answer.")
        if cls == "symptom":
            safety.render_symptom_card(q, ctx["patient_id"])
        elif cls == "emotional":
            safety.render_emotional_card(q, ctx["patient_id"])
        else:
            safety.render_chitchat_card(q)
        return

    spec = st.session_state.get("last_spec")
    if spec:
        _render_spec_with_controls(spec, ctx)


def _store_spec(spec: dict):
    """Push the current spec into previous_spec so the next render can diff."""
    if st.session_state.get("last_spec") is not None:
        st.session_state["previous_spec"] = st.session_state["last_spec"]
    st.session_state["last_spec"] = spec
    st.session_state["last_safety_class"] = None


def _generate_and_store(ctx: dict, query: str):
    ctx_kwargs = _build_ctx_kwargs(ctx)
    spec = None
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
            cached = cache_specs.lookup(ctx["role"], ctx["patient_id"], query)
            if cached is not None:
                st.warning(f"LLM call failed ({e}). Falling back to a cached spec.")
                spec = cached
            else:
                st.error(f"LLM call failed and no cached fallback exists: {e}")
                return
    _store_spec(spec)


def _render_spec_with_controls(spec: dict, ctx: dict):
    renderer.render_spec(spec, ctx,
                         previous_spec=st.session_state.get("previous_spec"))
    st.divider()

    # Doctor-only "Adjust view" controls. Two clearly-grouped dimensions
    # (time window + information dimension) so the user sees the axes of
    # adjustment, instead of a flat row of LLM-generated button labels.
    if ctx["role"] == "doctor":
        st.markdown("##### Adjust view")
        st.caption(
            "Reshape this dashboard along two dimensions. You can always "
            "re-type your question above instead - the buttons are just faster."
        )

        # Time window dimension
        st.markdown("**Time window**")
        time_opts = [
            ("Last 2 hours",  "Time resolution -> 2h"),
            ("Last 24 hours", "Time resolution -> 24h"),
            ("5 days",        "Time resolution -> 5d"),
        ]
        tcols = st.columns(len(time_opts))
        for i, (label, direction) in enumerate(time_opts):
            with tcols[i]:
                if st.button(label, key=f"time_{i}",
                             use_container_width=True):
                    _deepen(ctx, spec, direction); st.rerun()

        # Information dimension
        st.markdown("**Information**")
        info_opts = [
            ("Vitals",         "Information -> vitals"),
            ("Labs",           "Information -> labs"),
            ("Medications",    "Information -> medications"),
            ("Find anomalies", "Find anomalies"),
        ]
        icols = st.columns(len(info_opts))
        for i, (label, direction) in enumerate(info_opts):
            with icols[i]:
                if st.button(label, key=f"info_{i}",
                             use_container_width=True):
                    _deepen(ctx, spec, direction); st.rerun()

        # Surface the AI's own suggestion as a hint, but don't make it
        # the primary affordance.
        ai_opts = spec.get("granularity_options") or []
        if ai_opts:
            st.caption("AI suggestion: " + " · ".join(ai_opts))
        st.write("")  # breathing space

    # Drilldown ("Focus on..."): pick an entity and rebuild the dashboard
    # around it. Only meaningful for clinicians who actually navigate
    # records; hidden for patient/family.
    targets = spec.get("drill_targets") or []
    if targets and ctx["role"] in ("doctor", "nurse"):
        st.markdown("##### Focus on...")
        st.caption(
            "Pick a field (e.g. patient_id, lab_panel, drug_name) and a "
            "value to refocus the whole dashboard on that one entity."
        )
        cols = st.columns([2, 3, 3, 1])
        with cols[0]:
            entity_type = st.selectbox("Field", targets, key="drill_field")
        with cols[1]:
            entity_id = st.text_input("Value", key="drill_value")
        with cols[2]:
            entity_label = st.text_input("Label (optional)", key="drill_label")
        with cols[3]:
            if st.button("Focus", key="drill_btn") and entity_id:
                _drilldown(ctx, spec, entity_type, entity_id,
                           entity_label or entity_id)
                st.rerun()

    # Step-back editor
    with st.expander("Step back: edit the dashboard spec"):
        edited = renderer.render_spec_editor(spec)
        if st.button("Re-render edited spec", key="rerender_spec"):
            _store_spec(edited)
            st.rerun()


def _deepen(ctx: dict, spec: dict, direction: str):
    ctx_kwargs = _build_ctx_kwargs(ctx)
    with st.spinner(f"Deepening: {direction}"):
        try:
            new_spec = llm.deepen_spec(
                role=ctx["role"], ctx_kwargs=ctx_kwargs,
                current_time=ctx["now"].strftime("%a %Y-%m-%d %H:%M"),
                post_op_day=ctx["post_op_day"], ampm=ctx["ampm"],
                current_spec=spec, direction=direction,
            )
        except Exception as e:
            st.error(f"Deepen failed: {e}")
            return
    _store_spec(new_spec)


def _drilldown(ctx: dict, spec: dict, entity_type: str,
               entity_id: str, entity_label: str):
    ctx_kwargs = _build_ctx_kwargs(ctx)
    with st.spinner(f"Drilling into {entity_type} = {entity_id}"):
        try:
            new_spec = llm.drilldown_spec(
                role=ctx["role"], ctx_kwargs=ctx_kwargs,
                current_time=ctx["now"].strftime("%a %Y-%m-%d %H:%M"),
                post_op_day=ctx["post_op_day"], ampm=ctx["ampm"],
                current_spec=spec,
                entity_type=entity_type, entity_id=entity_id,
                entity_label=entity_label,
            )
        except Exception as e:
            st.error(f"Drilldown failed: {e}")
            return
    _store_spec(new_spec)


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

    # If the role / patient / actor identity changed, drop everything that
    # was rendered for the previous context.
    sig = (ctx["role"], ctx["patient_id"], ctx.get("actor_id"))
    if st.session_state.get("_ctx_sig") != sig:
        st.session_state["_ctx_sig"] = sig
        for k in ("last_spec", "previous_spec",
                  "last_safety_class", "last_safety_question",
                  "last_classification", "nl_query"):
            st.session_state.pop(k, None)

    _header(ctx)
    st.divider()
    _main_panel(ctx)


if __name__ == "__main__":
    main()
