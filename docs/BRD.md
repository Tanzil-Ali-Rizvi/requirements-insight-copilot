# Business Requirements Document: On-Time Delivery Programme

| Field | Value |
| --- | --- |
| Document owner | Business Systems Analyst |
| Sponsor | Head of Operations |
| Version | 1.0 |
| Status | Approved for design |
| Evidence | [findings.md](findings.md), Olist data Oct 2016 to Aug 2018 |

## 1. Background

The marketplace connects about 3,000 sellers with customers across Brazil. Sellers hand parcels to a carrier by a shipping limit; the carrier delivers to the customer by a promised date shown at checkout. 6.8% of delivered orders arrive after that date, and late orders score 2.27 review stars against 4.29.

## 2. Problem statement

Late deliveries damage customer reviews and put BRL 1.15M of order value at risk, and today nobody sees a late order coming: the promised date ignores current carrier load, seller handoffs are not monitored, and customers learn about delays only when the parcel fails to arrive.

## 3. Objectives and success metrics

| ID | Objective | Metric | Baseline | Target (6 months after launch) |
| --- | --- | --- | --- | --- |
| OBJ-1 | Fewer late deliveries | Late rate (delivered after promised date) | 6.8% | 5.0% or lower |
| OBJ-2 | Fewer late seller handoffs | Share of orders handed to carrier after the shipping limit | 9.0% | 5.0% or lower |
| OBJ-3 | Protect reviews when delays happen | Average review score of late orders | 2.27 | 3.0 or higher |
| OBJ-4 | Keep the promise competitive | Average promised days | 24.4 | No more than 25.0 |
| OBJ-5 | One version of the truth | Delivery KPIs served from the governed metric layer | 0 | 100% |

## 4. Scope

**In scope:** delivery-date estimation at checkout; seller handoff monitoring and scorecard; proactive late notifications; peak-season carrier capacity planning; a governed delivery dashboard and analyst copilot.

**Out of scope:** changing carriers or contracts; warehouse or fulfilment-centre operations; pricing and freight fees; seller onboarding.

## 5. Stakeholders (RACI)

| Activity | Head of Ops | Logistics product | Seller ops | Customer experience | BI / Analytics | Data engineering |
| --- | --- | --- | --- | --- | --- | --- |
| Approve the delivery-estimate model | A | R | I | C | C | C |
| Seller handoff SLA and scorecard | A | C | R | I | C | I |
| Customer late notifications | I | C | I | A/R | C | C |
| Peak capacity plan | A | R | C | I | C | I |
| Metric definitions and dashboard | I | C | C | C | A/R | R |

R = responsible, A = accountable, C = consulted, I = informed. Changes to the delivery-estimate model need Head of Operations approval.

## 6. Current state (as-is)

See [process/as_is.md](process/as_is.md). The promised date is set once at checkout from a static estimate. The seller ships within the shipping limit (median 6 days after approval) with no reminder. Nobody tracks the parcel against its route's normal transit time. The customer contacts support after the promised date passes.

## 7. Business requirements

| ID | Requirement | Priority | Evidence |
| --- | --- | --- | --- |
| BR-01 | The promised date must reflect the route (seller state to customer state) and current carrier load. | Must | Peak months hold 48.3% of late orders; promise is 11.9 days early on average |
| BR-02 | Seller operations must see, before the deadline, which orders are at risk of a late handoff, and track each seller's handoff performance. | Must | Late handoff raises late risk 3.9x; 83 sellers cause half of late handoffs |
| BR-03 | Customers must be told before the promised date when their order is likely to be late. | Must | 62.4% of late orders get 1-2 stars |
| BR-04 | Logistics must plan carrier capacity for known peaks, prioritising North and Northeast lanes. | Should | Northeast late rate 12.7% vs 5.9% South |
| BR-05 | Every delivery KPI must come from one governed definition, available to analysts in a dashboard and by plain-English question. | Should | Reporting today is manual and inconsistent |

## 8. Functional requirements

| ID | Requirement | Traces to |
| --- | --- | --- |
| FR-01 | The checkout service calls a delivery-estimate service that returns the promised date as the p90 delivery time of the order's route (at least 30 orders, else customer state, else national), scaled by a load factor from the last 14 days of deliveries. The model is retrained monthly. | BR-01 |
| FR-02 | 24 hours before an order's shipping limit, if the parcel has not been handed to the carrier, the system alerts the seller and the seller-ops queue. A weekly scorecard ranks sellers by late-handoff rate (minimum 30 orders). Sellers above 15% for two consecutive weeks are placed on a watchlist. | BR-02 |
| FR-03 | When an order's elapsed transit exceeds the route's 80th-percentile transit time, the customer receives an in-app and email notice with a revised date. | BR-03 |
| FR-04 | Each September and January, logistics receives a capacity forecast by lane for the next peak, based on the prior year's volume and transit by month. | BR-04 |
| FR-05 | Delivery KPIs (late rate, handoff rate, transit days, review impact) are defined once in a semantic layer and reused by the dashboard, reports and copilot. | BR-05 |
| FR-06 | Analysts can ask the copilot questions about requirements, policies and delivery data; answers cite the document section or show the SQL and data used. | BR-05 |

## 9. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-01 | The delivery-estimate service responds in under 200 ms at the 95th percentile. |
| NFR-02 | The copilot can run read-only queries only; it cannot write data, read files or reach the network. |
| NFR-03 | The copilot works without a paid AI service (offline mode) and can use any OpenAI-compatible model when configured. |
| NFR-04 | No customer personal data or review text is exposed in the analytics warehouse. |
| NFR-05 | R1 to R3 launch behind an A/B test with at least 4 weeks of data before full rollout. |

## 10. Assumptions and constraints

- Carrier transit data is available within 24 hours of each scan.
- Shipping limits remain set per order by the existing seller agreement.
- Historical data covers Oct 2016 to Aug 2018; behaviour may have shifted since.

## 11. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Longer promises reduce checkout conversion | Revenue loss | Cap average promised days at 25.0 (OBJ-4); A/B test |
| Alert fatigue among sellers | Alerts ignored | One alert per order; watchlist only after two weeks above threshold |
| Load factor overreacts to a short spike | Promises jump | 14-day window; factor applied only when above 1.0 |
| Observational analysis overstates effects | Targets missed | Treat sizing as upper bounds; validate in A/B tests |

## 12. Traceability

| Finding | Business req. | Functional req. | User stories |
| --- | --- | --- | --- |
| Peak months, static promise | BR-01 | FR-01 | US-01, US-02 |
| Late handoffs, seller concentration | BR-02 | FR-02 | US-03, US-04 |
| Review damage | BR-03 | FR-03 | US-05 |
| North / Northeast lanes | BR-04 | FR-04 | US-06 |
| Inconsistent reporting | BR-05 | FR-05, FR-06 | US-07, US-08 |
