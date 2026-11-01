# User stories and acceptance criteria

Each story traces to a requirement in [BRD.md](BRD.md).

## US-01 Route-aware promised date (FR-01)

As a **customer**, I want a delivery date that reflects where the parcel is coming from, so that I can trust it.

```gherkin
Given a seller in SP and a customer in BA
And the SP->BA route has at least 30 delivered orders in the training data
When I reach checkout
Then the promised date equals the purchase date plus the route's p90 delivery days, rounded up
```

## US-02 Load-adjusted promised date in peak season (FR-01)

As a **logistics product manager**, I want promises to lengthen automatically when carriers are congested, so that peak months do not produce a wave of late orders.

```gherkin
Given the median delivery time of the last 14 days is 30% above the training median
When a customer reaches checkout
Then the route estimate is multiplied by 1.3 before rounding up
And when the recent median is at or below the training median, no adjustment is applied
```

## US-03 Handoff alert before the shipping limit (FR-02)

As a **seller**, I want a reminder before my shipping limit, so that I hand the parcel over in time.

```gherkin
Given an order whose shipping limit is in 24 hours
And the parcel has not been scanned by the carrier
When the hourly check runs
Then the seller receives one alert for that order
And the order appears in the seller-ops at-risk queue
```

## US-04 Seller handoff scorecard and watchlist (FR-02)

As a **seller operations lead**, I want a weekly ranking of sellers by late-handoff rate, so that I can coach the few sellers who cause most of the problem.

```gherkin
Given sellers with at least 30 delivered orders
When the weekly scorecard is published
Then sellers are ranked by late-handoff rate, highest first
And a seller above 15% for two consecutive weeks is added to the watchlist
```

## US-05 Proactive "running late" notice (FR-03)

As a **customer**, I want to know early if my order will be late, so that I can plan around it.

```gherkin
Given an order in transit
When elapsed transit time exceeds the route's 80th-percentile transit time
Then the customer receives an in-app and email notice with a revised date
And the notice is sent at most once per order
```

## US-06 Peak capacity forecast (FR-04)

As a **logistics manager**, I want a lane-level volume and transit forecast before each peak, so that I can book carrier capacity early.

```gherkin
Given it is the first week of September or January
When the forecast job runs
Then logistics receives expected orders and transit days by seller-state to customer-state lane for the next peak
And North and Northeast lanes are listed first
```

## US-07 Governed delivery KPIs (FR-05)

As an **analyst**, I want every delivery KPI defined once, so that my numbers match the dashboard.

```gherkin
Given the metric "late rate"
When it is shown in the dashboard, a report or a copilot answer
Then it is computed from the same SQL definition in the semantic layer
```

## US-08 Ask the copilot (FR-06)

As an **analyst or stakeholder**, I want to ask a question in plain English and get an answer with its source, so that I do not wait for a report.

```gherkin
Given the question "What is the seller handoff SLA?"
When I ask the copilot
Then it answers from the seller handling policy and cites the section

Given the question "Which regions get the most late deliveries?"
When I ask the copilot
Then it runs a read-only query, shows the table and the SQL, and summarises the result
```
