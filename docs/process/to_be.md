# To-be process: order to delivery

Three checkpoints are added: a route- and load-aware promise at checkout (FR-01), a handoff alert before the shipping limit (FR-02), and a running-late notice during transit (FR-03).

```mermaid
flowchart LR
    subgraph Customer
        A[Places order] --> B[Sees route- and load-aware date]
        N[Gets running-late notice with revised date]
        L[Receives parcel] --> M[Leaves review]
    end
    subgraph Marketplace
        P[(Delivery-estimate service)] --> B
        C[Approves payment] --> D[Sets shipping limit]
        Q{Scanned 24h before limit?}
        R{Transit above route p80?}
        S[Weekly seller scorecard and watchlist]
    end
    subgraph Seller
        E[Prepares parcel] --> F[Hands to carrier]
        T[Receives handoff alert]
    end
    subgraph Carrier
        G[Transit]
        H[Delivers]
    end
    A --> P
    B --> C
    D --> E
    D --> Q
    Q -- no --> T --> F
    Q -- yes --> F
    F --> G
    F --> S
    G --> R
    R -- yes --> N
    R -- no --> H
    N --> H
    H --> L
```

**What changes**

| Checkpoint | Owner | Requirement | Target |
| --- | --- | --- | --- |
| Route- and load-aware promise | Logistics product | FR-01 | Late rate 5.0% or lower at no more than 25.0 promised days |
| Handoff alert, scorecard, watchlist | Seller operations | FR-02 | Late handoffs 5.0% or lower |
| Running-late notice | Customer experience | FR-03 | Late-order review score 3.0 or higher |
