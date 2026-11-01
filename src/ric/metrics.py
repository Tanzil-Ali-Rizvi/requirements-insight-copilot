"""Semantic layer: the governed business questions, each with its SQL and a plain-English summary.

The same definitions drive the dashboard, the findings report and the copilot, so a number
means the same thing everywhere (requirement FR-05 in docs/BRD.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

DELIVERED = "FROM fct_orders WHERE is_delivered"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


@dataclass(frozen=True)
class Metric:
    key: str
    title: str
    question: str
    keywords: str
    sql: str
    summarize: Callable[[pd.DataFrame], str]
    chart: tuple[str, str, str] | None = None  # (kind, x, y)
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def search_text(self) -> str:
        return f"{self.title} {self.question} {self.keywords}"


def _s_overall(df: pd.DataFrame) -> str:
    r = df.iloc[0]
    return (f"{int(r.late_orders):,} of {int(r.delivered_orders):,} delivered orders arrived after the promised "
            f"date: a late rate of {_pct(r.late_rate)}.")


def _s_month(df: pd.DataFrame) -> str:
    d = df[df.delivered_orders >= 500]
    worst = d.sort_values("late_rate", ascending=False).head(3)
    months = ", ".join(f"{pd.Timestamp(m):%b %Y} ({_pct(v)})" for m, v in zip(worst.purchase_month, worst.late_rate))
    return f"Late deliveries spike in peak months. Worst months by late rate: {months}."


def _s_region(df: pd.DataFrame) -> str:
    top, low = df.iloc[0], df.iloc[-1]
    return (f"{top.customer_region} customers get the most late orders ({_pct(top.late_rate)}), "
            f"versus {_pct(low.late_rate)} in the {low.customer_region}.")


def _s_state(df: pd.DataFrame) -> str:
    top = df.head(3)
    return "States with the highest late rate (min. 500 orders): " + ", ".join(
        f"{s} {_pct(v)}" for s, v in zip(top.customer_state, top.late_rate)) + "."


def _s_reviews(df: pd.DataFrame) -> str:
    late = df[df.delivery == "Late"].iloc[0]
    ok = df[df.delivery == "On time"].iloc[0]
    return (f"Late orders average {late.avg_review:.2f} stars versus {ok.avg_review:.2f} on time; "
            f"{_pct(late.share_1_2_star)} of late orders get a 1-2 star review, versus {_pct(ok.share_1_2_star)}.")


def _s_handoff(df: pd.DataFrame) -> str:
    late = df[df.seller_handoff == "Late handoff"].iloc[0]
    ok = df[df.seller_handoff == "On-time handoff"].iloc[0]
    return (f"When the seller hands the parcel to the carrier after the shipping limit ({_pct(late.share_of_orders)} "
            f"of orders), {_pct(late.late_rate)} arrive late, versus {_pct(ok.late_rate)} otherwise: "
            f"{late.late_rate / ok.late_rate:.1f}x the risk.")


def _s_interstate(df: pd.DataFrame) -> str:
    a = df[df.route == "Interstate"].iloc[0]
    b = df[df.route == "Same state"].iloc[0]
    return (f"Interstate orders are late {_pct(a.late_rate)} of the time versus {_pct(b.late_rate)} within a state; "
            f"carrier transit takes {a.avg_transit_days:.1f} days versus {b.avg_transit_days:.1f}.")


def _s_stages(df: pd.DataFrame) -> str:
    late = df[df.delivery == "Late"].iloc[0]
    ok = df[df.delivery == "On time"].iloc[0]
    return (f"The carrier leg is where late orders lose time: median transit {late.median_transit_days:.1f} days "
            f"versus {ok.median_transit_days:.1f} on time. Seller handoff is slower too "
            f"({late.median_days_to_carrier:.1f} vs {ok.median_days_to_carrier:.1f} days).")


def _s_gmv(df: pd.DataFrame) -> str:
    r = df.iloc[0]
    return f"Late orders carried BRL {r.late_gmv:,.0f} of order value, {_pct(r.late_share)} of delivered GMV."


def _s_peak(df: pd.DataFrame) -> str:
    r = df.iloc[0]
    return (f"Three peak months (Nov 2017, Feb 2018, Mar 2018) hold {_pct(r.share_of_late)} of all late orders "
            f"but only {_pct(r.share_of_orders)} of delivered orders.")


def _s_sellers(df: pd.DataFrame) -> str:
    r = df.iloc[0]
    return (f"{int(r.sellers_for_half):,} sellers ({_pct(r.sellers_for_half / r.sellers)} of {int(r.sellers):,}) "
            f"account for half of all {int(r.late_handoffs):,} late handoffs.")


def _s_top_sellers(df: pd.DataFrame) -> str:
    r = df.iloc[0]
    return (f"The seller with the most late handoffs missed the shipping limit on {int(r.late_handoffs):,} of "
            f"{int(r.orders):,} orders ({_pct(r.late_handoff_rate)}).")


def _s_padding(df: pd.DataFrame) -> str:
    r = df.iloc[0]
    return (f"Customers are promised {r.avg_promised_days:.1f} days on average, but the median order arrives in "
            f"{r.median_actual_days:.1f} days, {abs(r.avg_days_vs_estimate):.1f} days before the promised date on average.")


def _s_category(df: pd.DataFrame) -> str:
    top = df.head(3)
    return "Categories with the highest late rate (min. 1,000 orders): " + ", ".join(
        f"{c} {_pct(v)}" for c, v in zip(top.category, top.late_rate)) + "."


def _s_counterfactual(df: pd.DataFrame) -> str:
    r = df.iloc[0]
    return (f"If late-handoff orders arrived late only as often as on-time-handoff orders on the same kind of route, "
            f"about {int(r.avoidable_late_orders):,} late orders ({_pct(r.share_of_late)}) would not have been late. "
            f"This is an association-based upper bound, not a causal estimate.")


def _s_status(df: pd.DataFrame) -> str:
    total = df.orders.sum()
    d = df[df.order_status == "delivered"].orders.sum()
    return f"{total:,} orders in total; {d:,} ({_pct(d / total)}) were delivered."


METRICS: tuple[Metric, ...] = (
    Metric(
        "late_rate_overall", "Overall late-delivery rate",
        "What share of delivered orders arrived late?",
        "late rate percentage overall total how many orders late delivery delivered after promised date "
        "arrive kpi target on-time otd",
        f"""SELECT COUNT(*) AS delivered_orders, SUM(is_late::INT) AS late_orders,
       AVG(is_late::INT) AS late_rate {DELIVERED}""",
        _s_overall, tags=("kpi",)),
    Metric(
        "late_rate_by_month", "Late rate by purchase month",
        "How has the late-delivery rate changed month by month?",
        "trend monthly month over time seasonality peak black friday when worse timeline",
        f"""SELECT purchase_month, COUNT(*) AS delivered_orders, AVG(is_late::INT) AS late_rate
{DELIVERED} GROUP BY 1 ORDER BY 1""",
        _s_month, chart=("line", "purchase_month", "late_rate")),
    Metric(
        "late_rate_by_region", "Late rate by customer region",
        "Which customer regions get the most late deliveries?",
        "region regions north northeast south southeast center-west geography location",
        f"""SELECT customer_region, COUNT(*) AS delivered_orders, AVG(is_late::INT) AS late_rate,
       AVG(promised_days) AS avg_promised_days, AVG(total_days) AS avg_actual_days
{DELIVERED} GROUP BY 1 ORDER BY late_rate DESC""",
        _s_region, chart=("bar", "customer_region", "late_rate")),
    Metric(
        "late_rate_by_state", "Late rate by customer state",
        "Which customer states have the highest late-delivery rate?",
        "state states uf rio de janeiro sao paulo bahia maranhao worst best geography",
        f"""SELECT customer_state, COUNT(*) AS delivered_orders, AVG(is_late::INT) AS late_rate
{DELIVERED} GROUP BY 1 HAVING COUNT(*) >= 500 ORDER BY late_rate DESC""",
        _s_state, chart=("bar", "customer_state", "late_rate")),
    Metric(
        "review_impact", "Review scores: late vs on time",
        "How do late deliveries affect customer review scores?",
        "review reviews score stars fewer lower rating satisfaction customers experience nps impact complaints",
        f"""SELECT CASE WHEN is_late THEN 'Late' ELSE 'On time' END AS delivery, COUNT(*) AS orders,
       AVG(review_score) AS avg_review, AVG((review_score <= 2)::INT) AS share_1_2_star
{DELIVERED} AND review_score IS NOT NULL GROUP BY 1 ORDER BY 1""",
        _s_reviews, chart=("bar", "delivery", "avg_review")),
    Metric(
        "seller_handoff", "Late rate by seller handoff",
        "Do late seller handoffs to the carrier cause late deliveries?",
        "seller handoff shipping limit dispatch sla carrier handover sellers ship late cause root",
        f"""SELECT CASE WHEN seller_handoff_late THEN 'Late handoff' ELSE 'On-time handoff' END AS seller_handoff,
       COUNT(*) AS orders, COUNT(*) / SUM(COUNT(*)) OVER () AS share_of_orders, AVG(is_late::INT) AS late_rate
{DELIVERED} AND seller_handoff_late IS NOT NULL GROUP BY 1 ORDER BY 1""",
        _s_handoff, chart=("bar", "seller_handoff", "late_rate")),
    Metric(
        "interstate", "Late rate: interstate vs same state",
        "Are interstate orders late more often than same-state orders?",
        "interstate same state across states distance route long-distance cross-state transit longer shipping lane",
        f"""SELECT CASE WHEN same_state THEN 'Same state' ELSE 'Interstate' END AS route, COUNT(*) AS orders,
       AVG(is_late::INT) AS late_rate, AVG(transit_days) AS avg_transit_days
{DELIVERED} AND same_state IS NOT NULL GROUP BY 1 ORDER BY 1""",
        _s_interstate, chart=("bar", "route", "late_rate")),
    Metric(
        "stage_durations", "Where late orders lose time",
        "Which stage of fulfilment causes the delay in late orders?",
        "stage stages bottleneck carrier transit days to carrier where delay time lost fulfilment process step",
        f"""SELECT CASE WHEN is_late THEN 'Late' ELSE 'On time' END AS delivery,
       MEDIAN(days_to_carrier) AS median_days_to_carrier, MEDIAN(transit_days) AS median_transit_days,
       AVG(days_to_carrier) AS avg_days_to_carrier, AVG(transit_days) AS avg_transit_days
{DELIVERED} GROUP BY 1 ORDER BY 1""",
        _s_stages),
    Metric(
        "late_gmv", "Order value in late deliveries",
        "How much revenue or GMV was in late orders?",
        "revenue gmv money value brl reais payment sales at risk financial impact cost",
        f"""SELECT SUM(CASE WHEN is_late THEN payment_value END) AS late_gmv,
       SUM(payment_value) AS delivered_gmv,
       SUM(CASE WHEN is_late THEN payment_value END) / SUM(payment_value) AS late_share {DELIVERED}""",
        _s_gmv),
    Metric(
        "peak_share", "Late orders in peak months",
        "What share of late orders happened in the peak months?",
        "peak months november february march black friday carnival capacity share concentration season",
        f"""SELECT SUM((is_late AND purchase_month IN (DATE '2017-11-01', DATE '2018-02-01', DATE '2018-03-01'))::INT)
         / SUM(is_late::INT) AS share_of_late,
       AVG((purchase_month IN (DATE '2017-11-01', DATE '2018-02-01', DATE '2018-03-01'))::INT) AS share_of_orders
{DELIVERED}""",
        _s_peak),
    Metric(
        "seller_concentration", "Concentration of late handoffs",
        "How concentrated are late handoffs among sellers?",
        "concentration pareto few sellers responsible share of late handoffs 80/20 watchlist",
        f"""WITH s AS (SELECT seller_id, SUM(seller_handoff_late::INT) AS lh {DELIVERED} GROUP BY 1),
r AS (SELECT lh, ROW_NUMBER() OVER (ORDER BY lh DESC) AS rk,
             SUM(lh) OVER (ORDER BY lh DESC ROWS UNBOUNDED PRECEDING) AS cum, SUM(lh) OVER () AS tot FROM s)
SELECT (SELECT COUNT(*) FROM s) AS sellers, MAX(tot) AS late_handoffs,
       MIN(rk) FILTER (WHERE cum >= tot * 0.5) AS sellers_for_half FROM r""",
        _s_sellers),
    Metric(
        "top_late_sellers", "Sellers with the most late handoffs",
        "Which sellers miss the shipping limit most often?",
        "top worst sellers list ranking seller id miss shipping limit scorecard most late handoffs",
        f"""SELECT seller_id, seller_state, COUNT(*) AS orders, SUM(seller_handoff_late::INT) AS late_handoffs,
       AVG(seller_handoff_late::INT) AS late_handoff_rate, AVG(is_late::INT) AS late_delivery_rate
{DELIVERED} GROUP BY 1, 2 HAVING COUNT(*) >= 30 ORDER BY late_handoffs DESC LIMIT 15""",
        _s_top_sellers),
    Metric(
        "estimate_padding", "Promised vs actual delivery time",
        "How accurate are the promised delivery dates?",
        "estimate estimated promised date accuracy padding early buffer delivery promise eta how long days",
        f"""SELECT AVG(promised_days) AS avg_promised_days, MEDIAN(total_days) AS median_actual_days,
       AVG(days_vs_estimate) AS avg_days_vs_estimate {DELIVERED}""",
        _s_padding),
    Metric(
        "late_rate_by_category", "Late rate by product category",
        "Which product categories are delivered late most often?",
        "category categories product products furniture health beauty bed bath item type",
        """SELECT p.category, COUNT(DISTINCT o.order_id) AS delivered_orders, AVG(o.is_late::INT) AS late_rate
FROM fct_orders o JOIN fct_order_items i ON i.order_id = o.order_id AND i.order_item_id = 1
JOIN dim_product p ON p.product_id = i.product_id
WHERE o.is_delivered GROUP BY 1 HAVING COUNT(DISTINCT o.order_id) >= 1000 ORDER BY late_rate DESC""",
        _s_category, chart=("bar", "category", "late_rate")),
    Metric(
        "handoff_counterfactual", "Late orders linked to late handoffs",
        "How many late orders could be avoided if sellers handed off on time?",
        "avoid avoidable prevent impact opportunity sizing what if fix handoff counterfactual reduction",
        f"""WITH g AS (SELECT same_state, seller_handoff_late, COUNT(*) AS n, AVG(is_late::INT) AS lr
           {DELIVERED} AND seller_handoff_late IS NOT NULL AND same_state IS NOT NULL GROUP BY 1, 2),
b AS (SELECT same_state, lr AS base_lr FROM g WHERE NOT seller_handoff_late)
SELECT ROUND(SUM(g.n * (g.lr - b.base_lr))) AS avoidable_late_orders,
       SUM(g.n * (g.lr - b.base_lr)) / (SELECT SUM(is_late::INT) {DELIVERED}) AS share_of_late
FROM g JOIN b USING (same_state) WHERE g.seller_handoff_late""",
        _s_counterfactual),
    Metric(
        "orders_by_status", "Orders by status",
        "How many orders are there by status?",
        "status count orders total canceled cancelled shipped delivered unavailable volume number",
        "SELECT order_status, COUNT(*) AS orders FROM fct_orders GROUP BY 1 ORDER BY orders DESC",
        _s_status, chart=("bar", "order_status", "orders")),
)

BY_KEY = {m.key: m for m in METRICS}
