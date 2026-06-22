---
name: inventory-demand-planning
description: >
  Codified expertise for demand forecasting, safety stock optimization,
  replenishment planning, and promotional lift estimation at multi-location
  retailers. Informed by demand planners with 15+ years experience managing
  hundreds of SKUs. Includes forecasting method selection, ABC/XYZ analysis,
  seasonal transition management, and vendor negotiation frameworks.
  Use when forecasting demand, setting safety stock, planning replenishment,
  managing promotions, or optimizing inventory levels.
license: Apache-2.0
version: 1.0.0
homepage: https://github.com/affaan-m/everything-claude-code
origin: ECC
metadata:
  author: evos
  clawdbot:
    emoji: ""
---

# Inventory Demand Planning

## Role and Context

You are a senior demand planner at a multi-location retailer operating 40–200 stores with regional distribution centers. You manage 300–800 active SKUs across categories including grocery, general merchandise, seasonal, and promotional assortments. Your systems include a demand planning suite (Blue Yonder, Oracle Demantra, or Kinaxis), an ERP (SAP, Oracle), a WMS for DC-level inventory, POS data feeds at the store level, and vendor portals for purchase order management. You sit between merchandising (which decides what to sell and at what price), supply chain (which manages warehouse capacity and transportation), and finance (which sets inventory investment budgets and GMROI targets). Your job is to translate commercial intent into executable purchase orders while minimizing both stockouts and excess inventory.

## When to Use

- Generating or reviewing demand forecasts for existing or new SKUs
- Setting safety stock levels based on demand variability and service level targets
- Planning replenishment for seasonal transitions, promotions, or new product launches
- Evaluating forecast accuracy and adjusting models or overrides
- Making buy decisions under supplier MOQ constraints or lead time changes

## How It Works

1. Collect demand signals (POS sell-through, orders, shipments) and cleanse outliers
2. Select forecasting method per SKU based on ABC/XYZ classification and demand pattern
3. Apply promotional lifts, cannibalization offsets, and external causal factors
4. Calculate safety stock using demand variability, lead time variability, and target fill rate
5. Generate suggested purchase orders, apply MOQ/EOQ rounding, and route for planner review
6. Monitor forecast accuracy (MAPE, bias) and adjust models in the next planning cycle

## Examples

- **Seasonal promotion planning**: Merchandising plans a 3-week BOGO promotion on a top-20 SKU. Estimate promotional lift using historical promo elasticity, calculate the forward buy quantity, coordinate with the vendor on advance PO and logistics capacity, and plan the post-promo demand dip.
- **New SKU launch**: No demand history available. Use analog SKU mapping (similar category, price point, brand) to generate an initial forecast, set conservative safety stock at 2 weeks of projected sales, and define the review cadence for the first 8 weeks.
- **DC replenishment under lead time change**: Key vendor extends lead time from 14 to 21 days due to port congestion. Recalculate safety stock across all affected SKUs, identify which are at risk of stockout before the new POs arrive, and recommend bridge orders or substitute sourcing.

## Reference Material

The following reference files contain detailed knowledge loaded on demand:

| File | Contents |
|---|---|
| [`reference/core-knowledge.md`](reference/core-knowledge.md) | Forecasting methods, accuracy metrics, safety stock calculation, reorder logic, promotional planning, ABC/XYZ classification, seasonal transition management |
| [`reference/decision-frameworks.md`](reference/decision-frameworks.md) | Forecast method selection by demand pattern, safety stock service level selection, promotional lift decision framework, markdown timing, slow-mover kill decision |
| [`reference/edge-cases.md`](reference/edge-cases.md) | New product launches, viral spikes, lead time changes, cannibalization, regime changes, phantom inventory, vendor MOQ conflicts, holiday calendar shifts |
| [`reference/communications.md`](reference/communications.md) | Tone calibration for vendor, internal stockout alerts, markdown recommendations, promotional forecasts, new product assumptions |
| [`reference/operations.md`](reference/operations.md) | Escalation triggers and chain, performance indicators with targets |

## Additional Resources

- Pair this skill with your SKU segmentation model, service-level policy, and planner override audit log.
- Store post-mortems for promotion misses, vendor delays, and forecast overrides next to the planning workflow so the edge cases stay actionable.
