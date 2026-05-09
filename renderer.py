"""Spec -> Streamlit / Plotly renderer.

Nine primitives. vital_trajectory is the medical-specific one and gets the
most attention (reference bands + abnormal markers). All other primitives
are intentionally short.
"""
from __future__ import annotations

import math
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data

# ---------------------------------------------------------------- constants
VITAL_REFERENCE = {
    "hr":         (60, 100,   "bpm"),
    "bp_sys":     (90, 140,   "mmHg"),
    "bp_dia":     (60, 90,    "mmHg"),
    "spo2":       (95, 100,   "%"),
    "rr":         (12, 20,    "/min"),
    "temp_c":     (36.1, 37.5, "C"),
    "pain_score": (0,  3,     "NRS"),
}

STATUS_COLOR_MAP = {
    "green":  "#16a34a",
    "yellow": "#eab308",
    "red":    "#dc2626",
}


# ---------------------------------------------------------------- query helper
_FRIENDLY_PERMISSION_MSG = {
    "patient": ("This information is part of your medical record and is "
                "managed by your care team. Please ask the on-shift nurse "
                "or your doctor."),
    "family":  ("Some clinical details are kept with the medical team. "
                "Please ask the doctor or on-shift nurse if you need this "
                "information."),
    "nurse":   ("Your role does not have access to this information. "
                "Please ask the attending physician."),
    "doctor":  "This query was blocked by a guard rule.",
}


def _friendly_sql_error(err_text: str, role: str) -> str:
    if "may not query" in err_text or "must filter by patient_id" in err_text:
        return _FRIENDLY_PERMISSION_MSG.get(role, _FRIENDLY_PERMISSION_MSG["doctor"])
    if "Binder Error" in err_text:
        return ("This panel could not load (data layout mismatch). "
                "Try regenerating the dashboard.")
    return "This panel could not load."


def _run_query(query: str, role_ctx: dict) -> Optional[pd.DataFrame]:
    if not query:
        return None
    try:
        return data.safe_execute(
            query,
            role=role_ctx["role"],
            user_id=role_ctx["actor_id"],
            patient_id=role_ctx["patient_id"],
        )
    except data.SqlSafetyError as e:
        st.warning(_friendly_sql_error(str(e), role_ctx["role"]))
        with st.expander("Why? (technical detail)"):
            st.caption(str(e))
            st.code(query, language="sql")
        return None


# ---------------------------------------------------------------- primitives
def _resolve_col(col, df):
    """Match an LLM-named column against the dataframe, tolerating SQL casts.

    The LLM sometimes writes 'recorded_at::date' or 'value::float' as a
    config field. Strip cast suffixes and only return a column that
    actually exists - otherwise return None so the caller can drop it.
    """
    if not col or df is None:
        return None
    if col in df.columns:
        return col
    base = str(col).split("::", 1)[0].strip()
    if base in df.columns:
        return base
    return None


def _render_metric_card(component, df, role_ctx):
    cfg = component.get("config", {})
    label = cfg.get("label") or component.get("title", "Metric")
    value = cfg.get("value")
    if value is None and df is not None and not df.empty:
        # Take the first scalar value of the first column.
        value = df.iloc[0, 0]
    delta = cfg.get("delta")
    color = STATUS_COLOR_MAP.get(cfg.get("status_color"), None)
    st.metric(label=label, value=value if value is not None else "-",
              delta=delta if delta is not None else None)
    if color:
        st.markdown(
            f"<div style='height:4px;background:{color};border-radius:2px'></div>",
            unsafe_allow_html=True,
        )


def _render_line_chart(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    x = _resolve_col(cfg.get("x"), df) or df.columns[0]
    y = _resolve_col(cfg.get("y"), df) or df.columns[-1]
    group_by = _resolve_col(cfg.get("group_by"), df)
    fig = px.line(df, x=x, y=y, color=group_by, title=None, markers=True)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=30), height=320)
    if pd.api.types.is_datetime64_any_dtype(df[x]) or "_at" in str(x) or "date" in str(x):
        fig.update_xaxes(tickformat="%a %H:%M", tickangle=-30, nticks=6)
    st.plotly_chart(fig, use_container_width=True)


def _render_bar_chart(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    x = _resolve_col(cfg.get("x"), df) or df.columns[0]
    y = _resolve_col(cfg.get("y"), df) or df.columns[-1]
    fig = px.bar(df, x=x, y=y, title=None)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=30), height=320)
    st.plotly_chart(fig, use_container_width=True)


def _render_scatter(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    x = _resolve_col(cfg.get("x"), df) or df.columns[0]
    y = _resolve_col(cfg.get("y"), df) or df.columns[1]
    color = _resolve_col(cfg.get("color_by"), df)
    fig = px.scatter(df, x=x, y=y, color=color, title=None)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=30), height=320)
    st.plotly_chart(fig, use_container_width=True)


def _render_heatmap(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    x = _resolve_col(cfg.get("x"), df) or df.columns[0]
    y = _resolve_col(cfg.get("y"), df) or df.columns[1]
    val = _resolve_col(cfg.get("value"), df) or df.columns[-1]
    pivot = df.pivot_table(index=y, columns=x, values=val, aggfunc="mean")
    fig = px.imshow(pivot, aspect="auto", title=None)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=30), height=320)
    st.plotly_chart(fig, use_container_width=True)


def _render_table(component, df, role_ctx):
    if df is None or df.empty:
        st.info("No data.")
        return
    cfg = component.get("config", {})
    cols = cfg.get("columns")
    if cols:
        existing = [c for c in cols if c in df.columns]
        if existing:
            df = df[existing]
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_distribution(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    val = cfg.get("value") or df.select_dtypes("number").columns[0]
    bins = cfg.get("bins", 20)
    fig = px.histogram(df, x=val, nbins=int(bins), title=component.get("title"))
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
    st.plotly_chart(fig, use_container_width=True)


def _render_text_summary(component, df, role_ctx):
    import re as _re
    cfg = component.get("config", {})
    body = cfg.get("content")
    if not body and df is not None and not df.empty:
        body = str(df.iloc[0, 0])
    if not body:
        st.markdown("_(no content)_")
        return
    # Strip leading markdown header markers so the LLM cannot blow up the
    # font by writing "## Foo" inside a panel that already has a title.
    body = _re.sub(r"^#+\s+", "", body, flags=_re.M)
    st.markdown(
        f"<div style='font-size:0.95rem;line-height:1.55'>{body}</div>",
        unsafe_allow_html=True,
    )


def _render_vital_trajectory(component, df, role_ctx):
    """Multi-panel vital-trajectory chart with reference bands and red dots."""
    cfg = component.get("config", {})
    vital_names = cfg.get("vital_names") or ["hr", "bp_sys", "spo2", "pain_score"]
    if df is None or df.empty:
        st.info("No vitals in window.")
        return
    if "recorded_at" not in df.columns:
        st.warning("vital_trajectory expected 'recorded_at' in result set.")
        st.dataframe(df, use_container_width=True)
        return
    df = df.copy()
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    df = df.sort_values("recorded_at")

    available = [v for v in vital_names if v in df.columns]
    if not available:
        st.warning(f"None of the requested vitals are present: {vital_names}")
        return

    n = len(available)
    cols = 2 if n > 2 else 1
    rows = math.ceil(n / cols)
    from plotly.subplots import make_subplots
    # Pad subplot titles with None (NOT empty string) for unfilled slots,
    # otherwise Plotly renders the slot title as "undefined".
    titles = [v.upper() for v in available]
    titles += [None] * (rows * cols - len(titles))
    sub_kwargs = dict(rows=rows, cols=cols, subplot_titles=titles)
    if rows > 1:
        sub_kwargs["vertical_spacing"] = 0.18
    fig = make_subplots(**sub_kwargs)
    for i, vital in enumerate(available):
        r = i // cols + 1
        c = i % cols + 1
        ref = VITAL_REFERENCE.get(vital)
        # Reference band
        if ref:
            lo, hi, _ = ref
            fig.add_trace(
                go.Scatter(
                    x=[df["recorded_at"].min(), df["recorded_at"].max(),
                       df["recorded_at"].max(), df["recorded_at"].min()],
                    y=[lo, lo, hi, hi],
                    fill="toself", fillcolor="rgba(34,197,94,0.10)",
                    line=dict(width=0), hoverinfo="skip",
                    showlegend=False, name=f"{vital} ref",
                ),
                row=r, col=c,
            )
        # Trace
        fig.add_trace(
            go.Scatter(
                x=df["recorded_at"], y=df[vital],
                mode="lines+markers",
                line=dict(color="#2563eb", width=1.5),
                marker=dict(size=4, color="#2563eb"),
                name=vital, showlegend=False,
            ),
            row=r, col=c,
        )
        # Abnormal red overlay
        if ref:
            lo, hi, _ = ref
            mask = (df[vital] < lo) | (df[vital] > hi)
            if mask.any():
                fig.add_trace(
                    go.Scatter(
                        x=df.loc[mask, "recorded_at"], y=df.loc[mask, vital],
                        mode="markers",
                        marker=dict(size=8, color="#dc2626", symbol="circle"),
                        name=f"{vital} abnormal", showlegend=False,
                        hovertemplate=f"%{{x|%a %H:%M}}<br>{vital}=%{{y}}<extra></extra>",
                    ),
                    row=r, col=c,
                )
    fig.update_layout(
        height=300 * rows, margin=dict(l=10, r=10, t=40, b=30),
        title=None,  # title is already shown above the container
    )
    fig.update_xaxes(tickformat="%a %H:%M", tickangle=-30, nticks=8)
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------- dispatcher
PRIMITIVES = {
    "metric_card":      _render_metric_card,
    "bar_chart":        _render_bar_chart,
    "line_chart":       _render_line_chart,
    "vital_trajectory": _render_vital_trajectory,
    "scatter":          _render_scatter,
    "heatmap":          _render_heatmap,
    "table":            _render_table,
    "distribution":     _render_distribution,
    "text_summary":     _render_text_summary,
}


def render_component(component: dict, role_ctx: dict,
                     diff_status: str = "initial"):
    ctype = component.get("type")
    fn = PRIMITIVES.get(ctype)
    if fn is None:
        st.warning(f"Unknown component type: {ctype}")
        return
    df = _run_query(component.get("data_query", ""), role_ctx)
    fn(component, df, role_ctx)


# ---------------------------------------------------------------- agentic-UI add-ons
DIFF_BADGE = {
    "new":       "&nbsp;<span style='color:#16a34a;font-size:0.8em'>New</span>",
    "modified":  "&nbsp;<span style='color:#eab308;font-size:0.8em'>Updated</span>",
    "unchanged": "",
    "initial":   "",
}


def render_reasoning_panel(spec: dict):
    """Top-of-board collapsible 'How the AI thought about this' card."""
    intent_u  = spec.get("intent_understood") or spec.get("intent", "")
    reasoning = spec.get("reasoning", "")
    layout    = spec.get("layout", []) or []
    rejected  = spec.get("rejected_options", []) or []

    with st.expander("How the AI thought about this", expanded=False):
        if intent_u:
            st.markdown(f"**What I understood you want:** {intent_u}")
        if reasoning:
            st.markdown(
                f"**Why I picked these {len(layout)} component(s):** {reasoning}"
            )
        if rejected:
            st.markdown("**What I considered but did NOT include:**")
            for r in rejected:
                st.markdown(
                    f"- `{r.get('type','?')}` - {r.get('reason','(no reason given)')}"
                )
        if not (intent_u or reasoning or rejected):
            st.caption("(The model did not produce reasoning fields.)")


def compute_spec_diff(old_spec: dict | None, new_spec: dict) -> dict:
    """Diff two specs by component title. Returns:

      {
        "per_component": {idx: 'new'|'modified'|'unchanged'|'initial'},
        "removed":       [titles_dropped_from_old_spec],
        "is_initial":    bool,
      }
    """
    new_layout = new_spec.get("layout", []) or []
    if old_spec is None:
        return {
            "per_component": {i: "initial" for i in range(len(new_layout))},
            "removed":       [],
            "is_initial":    True,
        }
    old_by_title = {c.get("title", f"_idx{i}"): c
                    for i, c in enumerate(old_spec.get("layout", []) or [])}
    per_component = {}
    for i, c in enumerate(new_layout):
        title = c.get("title", f"_idx{i}")
        if title not in old_by_title:
            per_component[i] = "new"
        elif c != old_by_title[title]:
            per_component[i] = "modified"
        else:
            per_component[i] = "unchanged"
    new_titles = {c.get("title", f"_idx{i}") for i, c in enumerate(new_layout)}
    removed = [t for t in old_by_title if t not in new_titles]
    return {
        "per_component": per_component,
        "removed":       removed,
        "is_initial":    False,
    }


def _render_diff_summary(diff: dict):
    if diff["is_initial"]:
        return
    new_n = sum(1 for v in diff["per_component"].values() if v == "new")
    mod_n = sum(1 for v in diff["per_component"].values() if v == "modified")
    rem_n = len(diff["removed"])
    if new_n + mod_n + rem_n == 0:
        st.caption("Refined - no panels changed.")
        return
    bits = []
    if new_n: bits.append(f"{new_n} added")
    if mod_n: bits.append(f"{mod_n} changed")
    if rem_n: bits.append(f"{rem_n} removed")
    st.caption("Refined - " + ", ".join(bits))
    if diff["removed"]:
        st.caption("Removed: " + ", ".join(diff["removed"]))


def render_spec(spec: dict, role_ctx: dict,
                previous_spec: dict | None = None):
    """Render the full spec.

    Adds two agentic-UI affordances:
      - top reasoning panel ('how the AI thought about this')
      - per-component diff badges + a top toast comparing to previous_spec
    """
    layout = spec.get("layout", []) or []

    # Diff vs. previous spec (None => initial render, no badges).
    diff = compute_spec_diff(previous_spec, spec)
    _render_diff_summary(diff)

    render_reasoning_panel(spec)
    st.divider()

    def _heading(comp, idx):
        badge = DIFF_BADGE.get(diff["per_component"].get(idx, "initial"), "")
        title = comp.get("title", "")
        if title:
            st.markdown(f"##### {title}{badge}", unsafe_allow_html=True)

    def _render_one(comp, idx):
        with st.container(border=True):
            _heading(comp, idx)
            render_component(
                comp, role_ctx,
                diff_status=diff["per_component"].get(idx, "initial"),
            )

    # Layout rule (top to bottom):
    #   1. text_summary panels (the "what's going on" headline) - full width
    #   2. all vital_trajectory panels - full width, the main charts
    #   3. everything else - 2 columns
    text_summaries = [(i, c) for i, c in enumerate(layout)
                      if c.get("type") == "text_summary"]
    vital_trajs    = [(i, c) for i, c in enumerate(layout)
                      if c.get("type") == "vital_trajectory"]
    used = {i for i, _ in text_summaries} | {i for i, _ in vital_trajs}
    others         = [(i, c) for i, c in enumerate(layout) if i not in used]

    for i, comp in text_summaries:
        _render_one(comp, i)
    for i, comp in vital_trajs:
        _render_one(comp, i)
    if others:
        cols = st.columns(2)
        for n, (i, comp) in enumerate(others):
            with cols[n % 2]:
                _render_one(comp, i)


# ---------------------------------------------------------------- spec editor
def render_spec_editor(spec: dict, key_prefix: str = "edit") -> dict:
    """Expose the spec as an editable form. Returns the (possibly updated) spec."""
    st.markdown("##### Edit dashboard spec")
    layout = spec.get("layout", []) or []
    new_layout = []
    for i, comp in enumerate(layout):
        with st.expander(f"{i+1}. {comp.get('title', comp.get('type'))}", expanded=False):
            ctype = st.selectbox(
                "Type", list(PRIMITIVES.keys()),
                index=list(PRIMITIVES.keys()).index(comp.get("type", "table")),
                key=f"{key_prefix}_type_{i}",
            )
            title = st.text_input("Title", comp.get("title", ""),
                                  key=f"{key_prefix}_title_{i}")
            query = st.text_area("data_query (SQL)", comp.get("data_query", ""),
                                 height=110, key=f"{key_prefix}_query_{i}")
            keep = st.checkbox("Keep this component", value=True,
                               key=f"{key_prefix}_keep_{i}")
            if keep:
                new_comp = dict(comp)
                new_comp["type"] = ctype
                new_comp["title"] = title
                new_comp["data_query"] = query
                new_layout.append(new_comp)
    spec = dict(spec)
    spec["layout"] = new_layout
    return spec
