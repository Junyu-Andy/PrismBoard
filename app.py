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

    # Patient
    patients = data.list_patients()
    primary = patients[patients["patient_id"].isin(["P001", "P002"])]
    patient_label = {row["patient_id"]: f"{row['name']} ({row['patient_id']}) - {row['primary_diagnosis']}"
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

    # Scope banner: tell the user explicitly which patient and actor the
    # next query will run under. Avoids the "I asked about Li Xiuying but
    # the sidebar still has Wang Wei selected" surprise.
    patient_name = data.get_patient(ctx["patient_id"])["name"]
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
    # around it.
    targets = spec.get("drill_targets") or []
    if targets:
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
