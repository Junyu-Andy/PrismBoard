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
        st.error(f"SQL guard blocked the query: {e}")
        st.code(query, language="sql")
        return None


# ---------------------------------------------------------------- primitives
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


def _render_bar_chart(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    x = cfg.get("x") or df.columns[0]
    y = cfg.get("y") or df.columns[-1]
    fig = px.bar(df, x=x, y=y, title=component.get("title"))
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
    st.plotly_chart(fig, use_container_width=True)


def _render_line_chart(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    x = cfg.get("x") or df.columns[0]
    y = cfg.get("y") or df.columns[-1]
    group_by = cfg.get("group_by")
    fig = px.line(df, x=x, y=y, color=group_by, title=component.get("title"),
                  markers=True)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
    st.plotly_chart(fig, use_container_width=True)


def _render_scatter(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    x = cfg.get("x") or df.columns[0]
    y = cfg.get("y") or df.columns[1]
    color = cfg.get("color_by")
    fig = px.scatter(df, x=x, y=y, color=color, title=component.get("title"))
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
    st.plotly_chart(fig, use_container_width=True)


def _render_heatmap(component, df, role_ctx):
    cfg = component.get("config", {})
    if df is None or df.empty:
        st.info("No data.")
        return
    x = cfg.get("x") or df.columns[0]
    y = cfg.get("y") or df.columns[1]
    val = cfg.get("value") or df.columns[-1]
    pivot = df.pivot_table(index=y, columns=x, values=val, aggfunc="mean")
    fig = px.imshow(pivot, aspect="auto", title=component.get("title"))
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
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
    cfg = component.get("config", {})
    body = cfg.get("content")
    if not body and df is not None and not df.empty:
        body = df.iloc[0, 0]
    st.markdown(body or "_(no content)_")


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
    fig = go.Figure()
    # Use subplots
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[v.upper() for v in available],
        vertical_spacing=0.12,
    )
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
        height=240 * rows, margin=dict(l=10, r=10, t=40, b=10),
        title=component.get("title"),
    )
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


def render_component(component: dict, role_ctx: dict):
    ctype = component.get("type")
    fn = PRIMITIVES.get(ctype)
    if fn is None:
        st.warning(f"Unknown component type: {ctype}")
        return
    df = _run_query(component.get("data_query", ""), role_ctx)
    fn(component, df, role_ctx)


def render_spec(spec: dict, role_ctx: dict):
    """Render the full spec (intent + reasoning + components)."""
    intent = spec.get("intent", "")
    reasoning = spec.get("reasoning", "")
    layout = spec.get("layout", []) or []

    if intent:
        st.markdown(f"**Intent:** {intent}")
    if reasoning:
        st.caption(f"Why this view: {reasoning}")

    # Two-column layout if 4+ components, single column otherwise
    if len(layout) >= 4:
        cols = st.columns(2)
        for i, comp in enumerate(layout):
            with cols[i % 2]:
                with st.container(border=True):
                    if comp.get("title"):
                        st.markdown(f"##### {comp['title']}")
                    render_component(comp, role_ctx)
    else:
        for comp in layout:
            with st.container(border=True):
                if comp.get("title"):
                    st.markdown(f"##### {comp['title']}")
                render_component(comp, role_ctx)


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
