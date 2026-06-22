## Decision Frameworks

### Forecast Method Selection by Demand Pattern

| Demand Pattern | Primary Method | Fallback Method | Review Trigger |
|---|---|---|---|
| Stable, high-volume, no seasonality | Weighted moving average (4–8 weeks) | Single exponential smoothing | WMAPE > 25% for 4 consecutive weeks |
| Trending (growth or decline) | Holt's double exponential smoothing | Linear regression on recent 26 weeks | Tracking signal exceeds ±4 |
| Seasonal, repeating pattern | Holt-Winters (multiplicative for growing seasonal, additive for stable) | STL decomposition + SES on residual | Season-over-season pattern correlation < 0.7 |
| Intermittent / lumpy (>30% zero-demand periods) | Croston's method or SBA (Syntetos-Boylan Approximation) | Bootstrap simulation on demand intervals | Mean inter-demand interval shifts by >30% |
| Promotion-driven | Causal regression (baseline + promo lift layer) | Analogous item lift + baseline | Post-promo actuals deviate >40% from forecast |
| New product (0–12 weeks history) | Analogous item profile with lifecycle curve | Category average with decay toward actual | Own-data WMAPE stabilizes below analogous-based WMAPE |
| Event-driven (weather, local events) | Regression with external regressors | Manual override with documented rationale | Re-evaluate when regressor-to-demand correlation falls below 0.6 or event-period forecast error rises >30% for 2 comparable events |

### Safety Stock Service Level Selection

| Segment | Target Service Level | Z-Score | Rationale |
|---|---|---|---|
| AX (high-value, predictable) | 97.5% | 1.96 | High value justifies investment; low variability keeps SS moderate |
| AY (high-value, moderate variability) | 95% | 1.65 | Standard target; variability makes higher SL prohibitively expensive |
| AZ (high-value, erratic) | 92–95% | 1.41–1.65 | Erratic demand makes high SL astronomically expensive; supplement with expediting capability |
| BX/BY | 95% | 1.65 | Standard target |
| BZ | 90% | 1.28 | Accept some stockout risk on mid-tier erratic items |
| CX/CY | 90–92% | 1.28–1.41 | Low value doesn't justify high SS investment |
| CZ | 85% | 1.04 | Candidate for discontinuation; minimal investment |

### Promotional Lift Decision Framework

1. **Is there historical lift data for this SKU-promo type combination?** → Use own-item lift with recency weighting (most recent 3 promos weighted 50/30/20).
2. **No own-item data but same category has been promoted?** → Use analogous item lift adjusted for price point and brand tier.
3. **Brand-new category or promo type?** → Use conservative category-average lift discounted 20%. Build in a wider safety stock buffer for the promo period.
4. **Cross-promoted with another category?** → Model the traffic driver separately from the cross-promo beneficiary. Apply cross-elasticity coefficient if available; default 0.15 lift for cross-category halo.
5. **Always model the post-promo dip.** Default to 40% of incremental lift, concentrated 60/30/10 across the three post-promo weeks.

### Markdown Timing Decision

| Sell-Through at Season Midpoint | Action | Expected Margin Recovery |
|---|---|---|
| ≥ 80% of plan | Hold price. Reorder cautiously if weeks of supply < 3. | Full margin |
| 60–79% of plan | Take 20–25% markdown. No reorder. | 70–80% of original margin |
| 40–59% of plan | Take 30–40% markdown immediately. Cancel any open POs. | 50–65% of original margin |
| < 40% of plan | Take 50%+ markdown. Explore liquidation channels. Flag buying error for post-mortem. | 30–45% of original margin |

### Slow-Mover Kill Decision

Evaluate quarterly. Flag for discontinuation when ALL of the following are true:
- Weeks of supply > 26 at current sell-through rate
- Last 13-week sales velocity < 50% of the item's first 13 weeks (lifecycle declining)
- No promotional activity planned in the next 8 weeks
- Item is not contractually obligated (planogram commitment, vendor agreement)
- Replacement or substitution SKU exists or category can absorb the gap

If flagged, initiate markdown at 30% off for 4 weeks. If still not moving, escalate to 50% off or liquidation. Set a hard exit date 8 weeks from first markdown. Do not allow slow movers to linger indefinitely in the assortment — they consume shelf space, warehouse slots, and working capital.
