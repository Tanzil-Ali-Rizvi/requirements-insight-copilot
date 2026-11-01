# Findings memo: why orders arrive late

**To:** Head of Operations · **From:** Business Systems Analyst · **Data:** Olist marketplace, 96,470 delivered orders, Oct 2016 to Aug 2018

## Summary

6.8% of delivered orders (6,534) arrived after the promised date. Those orders average 2.27 review stars against 4.29 for on-time orders, and 62.4% of them get a 1-2 star review. Late orders carried BRL 1.15M of order value (7.5% of delivered GMV).

Three causes explain most of it, and each points to a system change:

1. **Peak-season carrier congestion.** Nov 2017, Feb 2018 and Mar 2018 hold 48.3% of late orders but only 21.6% of orders. Carrier transit rose from about 8 days to 13 days in those months, but promised dates did not move.
2. **Late seller handoffs.** 9.0% of orders reach the carrier after the seller's shipping limit; 20.8% of those arrive late against 5.4% otherwise (3.9x). 83 sellers (2.8%) cause half of all late handoffs.
3. **Long interstate routes into the North and Northeast.** Northeast customers see a 12.7% late rate against 5.9% in the South; interstate transit takes 11.9 days against 4.8 within a state.

## Where the time is lost

Late orders lose most of their time with the carrier: median transit is 26.2 days against 7.0 for on-time orders. The seller stage is slower too (3.5 vs 2.2 days to reach the carrier), but it is the smaller gap.

## The delivery promise is static

Customers are promised 24.4 days on average, but the median order arrives in 10.2 days, 11.9 days early. The promise is long in normal weeks and too short in peak weeks, because it does not react to current carrier load.

A backtest on Jan-Aug 2018 orders (trained on 2017) compared Olist's promise with a route- and load-aware estimate that uses only data known at purchase time:

| Estimate | Late rate | Avg promised days |
| --- | --- | --- |
| Olist's actual promise | 7.73% | 23.4 |
| Route + load, 90th percentile | 7.06% | 23.6 |
| Route + load, 92nd percentile | 5.71% | 25.3 |

At practically the same promise length, the late rate falls by about 9%; adding under two days cuts it by about 26%. The gain is modest on its own, which is why the recommendation pairs it with the handoff and notification changes.

## Sizing the handoff fix

If late-handoff orders arrived late only as often as on-time-handoff orders on the same kind of route (same state or interstate), about 1,347 late orders (20.6% of all late orders) would not have been late. This is an association-based upper bound, not a causal estimate.

## Recommendations

| # | Change | Addresses | Owner | Requirement |
| --- | --- | --- | --- | --- |
| R1 | Route- and load-aware delivery estimate | Static promise, peaks | Logistics product | BR-01, FR-01 |
| R2 | Seller handoff alerts and a seller scorecard, starting with the 83-seller watchlist | Late handoffs | Seller operations | BR-02, FR-02 |
| R3 | Proactive "running late" notification when transit exceeds the route's normal range | Review damage | Customer experience | BR-03, FR-03 |
| R4 | Peak-season carrier capacity plan for November and February-March, with North/Northeast lanes first | Peak congestion, long routes | Logistics | BR-04, FR-04 |
| R5 | One governed delivery dashboard and an analyst copilot over the same metric definitions | Slow, inconsistent reporting | BI / Analytics | BR-05, FR-05, FR-06 |

## Caveats

- `is_late` compares the delivery date with the promised date; same-day deliveries count as on time.
- Order-level seller and region use the order's first item; 1.3% of orders have more than one seller.
- Effects are associations from observational data. R1 to R3 should launch behind an A/B test (see BRD section 9).
