---
name: ito-prediction-market-ops
description: Unified prediction-market and Itô basket operations, covering read-only market intelligence, probability research, non-advisory basket comparisons, trade planning, and oracle data ingestion.
origin: community
---

# Itô & Prediction Market Operations

Use this skill for all prediction-market workflows, venue research, basket comparisons, and trade planning on Itô or similar event-probability platforms.

> [!WARNING]
> This skill is for read-only analysis and non-advisory research. Do not provide investment advice, recommend active positions, or attempt to execute live trades.

## Core Workflows

### 1. Market Intelligence & Oracle Research
- **Venue Research**: Inspect contract details, volume, underliers, open interest, and event rules.
- **Oracle Signals**: Analyze market-implied probabilities as data inputs for decision intelligence or dashboards. Combine with source-grounded news to draft briefings.

### 2. Basket & Portfolio Comparisons
- **Gap Analysis**: Compare prediction-market baskets against portfolios, watchlist, or a specific research thesis.
- **Evidence-First Verification**: Query and cite authoritative public sources regarding underlying event outcomes rather than guessing.

### 3. Non-Advisory Trade Planning
- **Prerequisites Worksheet**: Document the specific contract conditions, order prerequisites, limits, and manual execution steps without placing trades.
- **Risk Mapping**: Identify hedging opportunities or conflicting events across subnets or venues.

---

## References

For specialized sub-modules, refer to these local guides:
- **Itô Basket Comparison Details**: `references/ito-basket-compare.md`
- **Itô Data Atlas and Schema**: `references/ito-data-atlas.md`
- **Itô Venues & Rules**: `references/ito-market-intelligence.md`
- **Itô Trade Planner Template**: `references/ito-trade-planner.md`
- **Prediction Market Probabilities**: `references/prediction-market-oracle.md`

## Verification Checklist

- [ ] All analysis is read-only, non-advisory, and carries a clear financial disclaimer
- [ ] Underlying contract rules and resolution conditions are explicitly cited
- [ ] No private keys, keys, or credentials are used or requested
