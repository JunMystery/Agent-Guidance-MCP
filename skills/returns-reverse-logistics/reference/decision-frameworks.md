# Decision Frameworks

## Disposition Routing by Category and Condition

| Category | Grade A | Grade B | Grade C | Grade D |
|---|---|---|---|---|
| Consumer Electronics | Restock (test first) | Open box / Renewed | Refurb if ROI > 40%, else liquidate | Parts harvest or e-waste |
| Apparel | Restock if tags on | Repackage / outlet | Liquidate by weight | Textile recycling |
| Home & Furniture | Restock | Open box with discount | Liquidate (local, avoid shipping) | Donate or destroy |
| Health & Beauty | Restock if sealed | Destroy (regulation) | Destroy | Destroy |
| Books & Media | Restock | Restock (discount) | Liquidate | Recycle |
| Sporting Goods | Restock | Open box | Refurb if cost < 25% value | Parts or donate |
| Toys & Games | Restock if sealed | Open box | Liquidate | Donate (if safety-compliant) |

## Fraud Scoring Model

Score each return 0-100. Flag for review at 65+, hold refund at 80+:

| Signal | Points | Notes |
|---|---|---|
| Return rate > 30% (rolling 12 mo) | +15 | Adjusted for category norms |
| Item returned within 48 hours of delivery | +5 | Could be legitimate bracket shopping |
| High-value electronics, serial number mismatch | +40 | Near-certain swap fraud |
| Return reason changed between initiation and receipt | +10 | Inconsistency flag |
| Multiple returns same week | +10 | Cumulative with rate signal |
| Return from address different from shipping address | +10 | Gift returns excluded |
| Product weight differs > 5% from expected | +25 | Swap or missing components |
| Customer account < 30 days old | +10 | New account risk |
| No-receipt return | +15 | Higher risk of receipt fraud |
| Item in category with high shrink rate | +5 | Electronics, cosmetics, designer apparel |

## Vendor Recovery ROI

Pursue vendor recovery when: `(Expected credit × probability of collection) > (Labor cost + shipping cost + relationship cost)`. Rules of thumb:

- Claims > $500: Always pursue. The math works even at 50% collection probability.
- Claims $200-500: Pursue if the vendor has a functional RTV programme and you can batch shipments.
- Claims < $200: Batch until threshold is met, or offset against next PO. Do not ship individual units.
- Overseas vendors: Increase minimum threshold to $1,000. Add 30% to expected processing time.

## Return Policy Exception Logic

When a return falls outside standard policy, evaluate in this order:

1. **Is the product defective?** If yes, accept regardless of window or condition. Defective products are the company's problem, not the customer's.
2. **Is this a high-value customer?** (Top 10% by LTV) If yes, accept with standard refund. The retention math almost always favours the exception.
3. **Is the request reasonable to a neutral observer?** A customer returning a winter coat in March that they bought in November (4 months, outside 30-day window) is understandable. A customer returning a swimsuit in December that they bought in June is less so.
4. **What is the disposition outcome?** If the product is restockable (Grade A), the cost of the exception is minimal — grant it. If it's Grade C or worse, the exception costs real margin.
5. **Does granting create a precedent risk?** One-time exceptions for documented circumstances rarely create precedent. Publicised exceptions (social media complaints) always do.
