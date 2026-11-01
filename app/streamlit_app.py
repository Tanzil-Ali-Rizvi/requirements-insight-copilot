"""Requirements-to-Insight Copilot: Streamlit front end.

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ric import agent, llm  # noqa: E402
from ric.metrics import BY_KEY  # noqa: E402
from ric.sql_guard import validate  # noqa: E402
from ric.warehouse import query  # noqa: E402

BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e6e5e1"

st.set_page_config(page_title="Requirements-to-Insight Copilot", page_icon="📦", layout="wide")


@st.cache_data
def metric(key: str) -> pd.DataFrame:
    return query(validate(BY_KEY[key].sql))


def summary(key: str) -> str:
    return BY_KEY[key].summarize(metric(key))


def style(fig: go.Figure, title: str, y_pct: bool = True, height: int = 320) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK), x=0, xanchor="left"),
        height=height, margin=dict(l=10, r=10, t=50, b=10), plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color=MUTED, size=12), showlegend=False, hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickformat=".0%" if y_pct else None, rangemode="tozero")
    return fig


def bar(df: pd.DataFrame, x: str, y: str, title: str, highlight: str | None = None, pct: bool = True,
        fmt: str = ".1%") -> go.Figure:
    colors = [ORANGE if highlight is not None and v == highlight else BLUE for v in df[x]]
    fig = go.Figure(go.Bar(x=df[x], y=df[y], marker=dict(color=colors, cornerradius=4), width=0.55,
                           text=[format(v, fmt) for v in df[y]], textposition="outside",
                           textfont=dict(color=INK), hovertemplate=f"%{{x}}<br>%{{y:{fmt}}}<extra></extra>"))
    return style(fig, title, y_pct=pct)


# ------------------------------------------------------------------ header
overall = metric("late_rate_overall").iloc[0]
reviews = metric("review_impact").set_index("delivery")
gmv = metric("late_gmv").iloc[0]
handoff = metric("seller_handoff").set_index("seller_handoff")

st.title("Requirements-to-Insight Copilot")
st.markdown(
    "**Why do 1 in 15 marketplace orders arrive late, and what system change fixes it?** "
    "A business-systems analysis of 96,470 delivered Olist orders, with the BRD it led to and a copilot "
    "that answers from those documents and the data."
)

k = st.columns(5)
k[0].metric("Late-delivery rate", f"{overall.late_rate:.1%}", help="Delivered after the promised date")
k[1].metric("Late orders", f"{int(overall.late_orders):,}")
k[2].metric("Review score, late orders", f"{reviews.loc['Late', 'avg_review']:.2f}",
            f"{reviews.loc['Late', 'avg_review'] - reviews.loc['On time', 'avg_review']:.2f} vs on time")
k[3].metric("Order value in late orders", f"BRL {gmv.late_gmv / 1e6:.2f}M", f"{gmv.late_share:.1%} of GMV",
            delta_color="off", delta_arrow="off")
k[4].metric("Late seller handoffs", f"{handoff.loc['Late handoff', 'share_of_orders']:.1%}",
            f"{handoff.loc['Late handoff', 'late_rate'] / handoff.loc['On-time handoff', 'late_rate']:.1f}x late risk",
            delta_color="off", delta_arrow="off")

tab_sum, tab_ask, tab_req, tab_back, tab_how = st.tabs(
    ["Executive summary", "Ask the copilot", "Requirements (BRD)", "Estimate backtest", "Data & method"])

# ------------------------------------------------------------------ summary
with tab_sum:
    st.subheader("Three causes, three system changes")
    st.markdown(
        f"1. **Peak-season congestion.** {summary('peak_share')}\n"
        f"2. **Late seller handoffs.** {summary('seller_handoff')} {summary('seller_concentration')}\n"
        f"3. **Long routes into the North and Northeast.** {summary('late_rate_by_region')} {summary('interstate')}"
    )
    c1, c2 = st.columns(2)
    m = metric("late_rate_by_month")
    m = m[m.delivered_orders >= 200]
    peaks = pd.to_datetime(["2017-11-01", "2018-02-01", "2018-03-01"])
    fig = go.Figure(go.Scatter(x=m.purchase_month, y=m.late_rate, mode="lines+markers",
                               line=dict(color=BLUE, width=2), marker=dict(size=8, color=BLUE),
                               hovertemplate="%{x|%b %Y}<br>%{y:.1%} late<extra></extra>"))
    pk = m[pd.to_datetime(m.purchase_month).isin(peaks)]
    fig.add_trace(go.Scatter(x=pk.purchase_month, y=pk.late_rate, mode="markers+text", marker=dict(size=10, color=ORANGE),
                             text=[f"{v:.0%}" for v in pk.late_rate], textposition="top center",
                             textfont=dict(color=INK), hoverinfo="skip"))
    c1.plotly_chart(style(fig, "Late rate by purchase month: three peaks hold 48% of late orders"),
                    use_container_width=True)

    h = metric("seller_handoff")
    c2.plotly_chart(bar(h, "seller_handoff", "late_rate", "Late rate by seller handoff: 3.9x higher when late",
                        highlight="Late handoff"), use_container_width=True)

    c3, c4 = st.columns(2)
    r = metric("late_rate_by_region")
    c3.plotly_chart(bar(r, "customer_region", "late_rate", "Late rate by customer region", highlight="Northeast"),
                    use_container_width=True)
    s = metric("stage_durations")
    fig = go.Figure(go.Bar(x=s.delivery, y=s.median_transit_days, marker=dict(color=[ORANGE, BLUE], cornerradius=4),
                           width=0.55, text=[f"{v:.1f} days" for v in s.median_transit_days], textposition="outside",
                           textfont=dict(color=INK), hovertemplate="%{x}<br>%{y:.1f} days<extra></extra>"))
    c4.plotly_chart(style(fig, "Median carrier transit: late orders lose time in transit", y_pct=False),
                    use_container_width=True)
    st.info(summary("handoff_counterfactual"))
    st.caption("Full memo: docs/findings.md")

# ------------------------------------------------------------------ copilot
with tab_ask:
    mode = "LLM mode" if llm.enabled() else "Offline mode (no API key needed)"
    st.markdown(f"Ask about the requirements, policies or delivery data. Every answer shows its source. *{mode}.*")
    examples = ["Which regions get the most late deliveries?", "What is the seller handoff SLA?",
                "Are we meeting the late rate target?", "Where do late orders lose time, seller or carrier?",
                "When does a seller go on the watchlist?", "How much revenue was in late orders?"]
    cols = st.columns(3)
    for i, ex in enumerate(examples):
        if cols[i % 3].button(ex, key=f"ex{i}", use_container_width=True):
            st.session_state["q"] = ex
    q = st.chat_input("Ask a question") or st.session_state.pop("q", None)
    if q:
        with st.chat_message("user"):
            st.write(q)
        a = agent.ask(q)
        with st.chat_message("assistant"):
            st.markdown(a.text)
            if a.citations:
                st.caption("Sources: " + " · ".join(a.citations))
            if a.table is not None:
                fmt = {c: "{:.1%}" for c in a.table.columns if "rate" in c or c.startswith("share")}
                st.dataframe(a.table.style.format(fmt, precision=2, thousands=","), use_container_width=True,
                             hide_index=True)
            if a.sql:
                with st.expander("SQL used (read-only, guarded)"):
                    st.code(a.sql, language="sql")
            st.caption(f"Route: {a.route} · {a.mode}")

# ------------------------------------------------------------------ requirements
with tab_req:
    doc = st.radio("Document", ["BRD", "User stories", "Process maps", "Seller policy", "Delivery policy"],
                   horizontal=True)
    files = {"BRD": "BRD.md", "User stories": "user_stories.md",
             "Seller policy": "policies/seller_handling_policy.md",
             "Delivery policy": "policies/delivery_promise_policy.md"}
    if doc == "Process maps":
        st.markdown("**As-is:** static promise, no monitoring, customer learns of delays after the fact.")
        st.image(str(ROOT / "docs/process/as_is.png"), use_container_width=True)
        st.markdown("**To-be:** route- and load-aware promise, handoff alerts, running-late notice.")
        st.image(str(ROOT / "docs/process/to_be.png"), use_container_width=True)
    else:
        st.markdown((ROOT / "docs" / files[doc]).read_text())

# ------------------------------------------------------------------ backtest
with tab_back:
    rows = json.loads((ROOT / "reports/backtest.json").read_text())
    b = pd.DataFrame(rows)
    base = rows[0]
    st.markdown(
        f"Trained on 2017 orders, tested on {int(base['test_orders']):,} orders from Jan-Aug 2018. "
        "A route- and load-aware estimate (FR-01) is compared with Olist's actual promise. "
        "Lower and further left is better."
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=b.load_promised_days, y=b.load_late_rate, mode="lines+markers+text",
                             line=dict(color=BLUE, width=2), marker=dict(size=9, color=BLUE),
                             text=[f"p{int(p * 100)}" for p in b.percentile], textposition="top right",
                             textfont=dict(color=MUTED),
                             hovertemplate="%{y:.2%} late at %{x:.1f} promised days<extra>Route + load</extra>"))
    fig.add_trace(go.Scatter(x=[base["olist_promised_days"]], y=[base["olist_late_rate"]], mode="markers+text",
                             marker=dict(size=12, color=ORANGE, symbol="diamond"), text=["Olist today"],
                             textposition="top center", textfont=dict(color=INK),
                             hovertemplate="%{y:.2%} late at %{x:.1f} promised days<extra>Olist</extra>"))
    fig = style(fig, "Late rate vs average promised days", height=380)
    fig.update_xaxes(title="Average promised days")
    st.plotly_chart(fig, use_container_width=True)
    show = pd.DataFrame({
        "Percentile": [f"p{int(p * 100)}" for p in b.percentile],
        "Route + load: late rate": b.load_late_rate, "Route + load: promised days": b.load_promised_days,
        "Route only: late rate": b.route_late_rate, "Route only: promised days": b.route_promised_days})
    st.dataframe(show.style.format({c: ("{:.2%}" if "rate" in c else "{:.1f}") for c in show.columns[1:]}),
                 hide_index=True, use_container_width=True)
    st.caption("At about the same promise length (p90: 23.6 vs 23.4 days) the late rate falls from 7.73% to 7.06%. "
               "The gain is modest alone, so FR-01 ships with the handoff alerts (FR-02) and notices (FR-03).")

# ------------------------------------------------------------------ method
with tab_how:
    st.markdown((ROOT / "docs/data_dictionary.md").read_text())
    ev = ROOT / "evals/results.md"
    if ev.exists():
        st.subheader("Copilot evaluation")
        st.markdown(ev.read_text())
