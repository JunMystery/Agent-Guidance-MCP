## Key Edge Cases

Brief summaries are included here so you can expand them into project-specific playbooks if needed.

1. **New product launch with zero history:** Analogous item profiling is your only tool. Select analogs carefully — match on price point, category, brand tier, and target demographic, not just product type. Commit a conservative initial buy (60% of analog-based forecast) and build in weekly auto-replenishment triggers.

2. **Viral social media spike:** Demand jumps 500–2,000% with no warning. Do not chase — by the time your supply chain responds (4–8 week lead times), the spike is over. Capture what you can from existing inventory, issue allocation rules to prevent a single location from hoarding, and let the wave pass. Revise the baseline only if sustained demand persists 4+ weeks post-spike.

3. **Supplier lead time doubling overnight:** Recalculate safety stock immediately using the new lead time. If SS doubles, you likely cannot fill the gap from current inventory. Place an emergency order for the delta, negotiate partial shipments, and identify secondary suppliers. Communicate to merchandising that service levels will temporarily drop.

4. **Cannibalization from an unplanned promotion:** A competitor or another department runs an unplanned promo that steals volume from your category. Your forecast will over-project. Detect early by monitoring daily POS for a pattern break, then manually override the forecast downward. Defer incoming orders if possible.

5. **Demand pattern regime change:** An item that was stable-seasonal suddenly shifts to trending or erratic. Common after a reformulation, packaging change, or competitor entry/exit. The old model will fail silently. Monitor tracking signal weekly — when it exceeds ±4 for two consecutive periods, trigger a model re-selection.

6. **Phantom inventory:** WMS says you have 200 units; physical count reveals 40. Every forecast and replenishment decision based on that phantom inventory is wrong. Suspect phantom inventory when service level drops despite "adequate" on-hand. Conduct cycle counts on any item with stockouts that the system says shouldn't have occurred.

7. **Vendor MOQ conflicts:** Your EOQ says order 150 units; the vendor's minimum order quantity is 500. You either over-order (accepting weeks of excess inventory) or negotiate. Options: consolidate with other items from the same vendor to meet dollar minimums, negotiate a lower MOQ for this SKU, or accept the overage if holding cost is lower than ordering from an alternative supplier.

8. **Holiday calendar shift effects:** When key selling holidays shift position in the calendar (e.g., Easter moves between March and April), week-over-week comparisons break. Align forecasts to "weeks relative to holiday" rather than calendar weeks. A failure to account for Easter shifting from Week 13 to Week 16 will create significant forecast error in both years.
