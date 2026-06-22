# Core Knowledge

## Returns Policy Logic

Every return starts with policy evaluation. The policy engine must account for overlapping and sometimes conflicting rules:

- **Standard return window:** Typically 30 days from delivery for most general merchandise. Electronics often 15 days. Perishables non-returnable. Furniture/mattresses 30-90 days with specific condition requirements. Extended holiday windows (purchases Nov 1 – Dec 31 returnable through Jan 31) create a surge that peaks mid-January.
- **Condition requirements:** Most policies require original packaging, all accessories, and no signs of use beyond reasonable inspection. "Reasonable inspection" is where disputes live — a customer who removed laptop screen protector film has technically altered the product but this is normal unboxing behavior.
- **Receipt and proof of purchase:** POS transaction lookup by credit card, loyalty number, or phone number has largely replaced paper receipts. Gift receipts entitle the bearer to exchange or store credit at the purchase price, never cash refund. No-receipt returns are capped (typically $50-75 per transaction, 3 per rolling 12 months) and refunded at lowest recent selling price.
- **Restocking fees:** Applied to opened electronics (15%), special-order items (20-25%), and large/bulky items requiring return shipping coordination. Waived for defective products or fulfilment errors. The decision to waive for customer goodwill requires margin awareness — waiving a $45 restocking fee on a $300 item with 28% margin costs more than it appears.
- **Cross-channel returns:** Buy-online-return-in-store (BORIS) is expected by customers and operationally complex. Online prices may differ from store prices. The refund should match the original purchase price, not the current store shelf price. Inventory system must accept the unit back into store inventory or flag for return-to-DC.
- **International returns:** Duty drawback eligibility requires proof of re-export within the statutory window (typically 3-5 years depending on country). Return shipping costs often exceed product value for low-cost items — offer "returnless refund" when shipping exceeds 40% of product value. Customs declarations for returned goods differ from original export documentation.
- **Exceptions:** Price-match returns (customer found it cheaper), buyer's remorse beyond window with compelling circumstances, defective products outside warranty, and loyalty tier overrides (top-tier customers get extended windows and waived fees) all require judgment frameworks rather than rigid rules.

## Inspection and Grading

Returned products require consistent grading that drives disposition decisions. Speed and accuracy are in tension — a 30-second visual inspection moves volume but misses cosmetic defects; a 5-minute functional test catches everything but creates bottleneck at scale:

- **Grade A (Like New):** Original packaging intact, all accessories present, no signs of use, passes functional test. Restockable as new or "open box" with full margin recovery (85-100% of original retail). Target inspection time: 45-90 seconds.
- **Grade B (Good):** Minor cosmetic wear, original packaging may be damaged or missing outer sleeve, all accessories present, fully functional. Restockable as "open box" or "renewed" at 60-80% of retail. May need repackaging ($2-5 per unit). Target inspection time: 90-180 seconds.
- **Grade C (Fair):** Visible wear, scratches, or minor damage. Missing accessories that cost <10% of unit value. Functional but cosmetically impaired. Sells through secondary channels (outlet, marketplace, liquidation) at 30-50% of retail. Refurbishment possible if cost < 20% of recovered value.
- **Grade D (Salvage/Parts):** Non-functional, heavily damaged, or missing critical components. Salvageable for parts or materials recovery at 5-15% of retail. If parts recovery isn't viable, route to recycling or destruction.

Grading standards vary by category. Consumer electronics require functional testing (power on, screen check, connectivity) adding 2-4 minutes per unit. Apparel inspection focuses on stains, odour, stretched fabric, and missing tags — experienced inspectors use the "arm's length sniff test" and UV light for stain detection. Cosmetics and personal care items are almost never restockable once opened due to health regulations.

## Disposition Decision Trees

Disposition is where returns either recover value or destroy margin. The routing decision is economics-driven:

- **Restock as new:** Only Grade A with complete packaging. Product must pass any required functional/safety testing. Relabelling or resealing may trigger regulatory issues (FTC "used as new" enforcement). Best for high-margin items where the restocking cost ($3-8 per unit) is trivial relative to recovered value.
- **Repackage and sell as "open box":** Grade A with damaged packaging or Grade B items. Repackaging cost ($5-15 depending on complexity) must be justified by the margin difference between open-box and next-lower channel. Electronics and small appliances are the sweet spot.
- **Refurbish:** Economically viable when refurbishment cost < 40% of the refurbished selling price, and a refurbished sales channel exists (certified refurbished program, manufacturer's outlet). Common for premium electronics, power tools, and small appliances. Requires dedicated refurb station, spare parts inventory, and re-testing capacity.
- **Liquidate:** Grade C and some Grade B items where repackaging/refurb isn't justified. Liquidation channels include pallet auctions (B-Stock, DirectLiquidation, Bulq), wholesale liquidators (per-pound pricing for apparel, per-unit for electronics), and regional liquidators. Recovery rates: 5-20% of retail. Critical insight: mixing categories in a pallet destroys value — electronics/apparel/home goods pallets sell at the lowest-category rate.
- **Donate:** Tax-deductible at fair market value (FMV). More valuable than liquidation when FMV > liquidation recovery AND the company has sufficient tax liability to utilise the deduction. Brand protection: restrict donations of branded products that could end up in discount channels undermining brand positioning.
- **Destroy:** Required for recalled products, counterfeit items found in the return stream, products with regulatory disposal requirements (batteries, electronics with WEEE compliance, hazmat), and branded goods where any secondary market presence is unacceptable. Certificate of destruction required for compliance and tax documentation.

## Fraud Detection

Return fraud costs US retailers $24B+ annually. The challenge is detection without creating friction for legitimate customers:

- **Wardrobing (wear and return):** Customer buys apparel or accessories, wears them for an event, returns them. Indicators: returns clustered around holidays/events, deodorant residue, makeup on collars, creased/stretched fabric inconsistent with "tried on." Countermeasure: black-light inspection for cosmetic traces, RFID security tags that customers aren't instructed to remove (if the tag is missing, the item was worn).
- **Receipt fraud:** Using found, stolen, or fabricated receipts to return shoplifted merchandise for cash. Declining as digital receipt lookup replaces paper, but still occurs. Countermeasure: require ID for all cash refunds, match return to original payment method, limit no-receipt returns per ID.
- **Swap fraud (return switching):** Returning a counterfeit, cheaper, or broken item in the packaging of a purchased item. Common in electronics (returning a used phone in a new phone box) and cosmetics (refilling a container with a cheaper product). Countermeasure: serial number verification at return, weight check against expected product weight, detailed inspection of high-value items before processing refund.
- **Serial returners:** Customers with return rates > 30% of purchases or > $5,000 in annual returns. Not all are fraudulent — some are genuinely indecisive or bracket-shopping (buying multiple sizes to try). Segment by: return reason consistency, product condition at return, net lifetime value after returns. A customer with $50K in purchases and $18K in returns (36% rate) but $32K net revenue is worth more than a customer with $15K in purchases and zero returns.
- **Bracketing:** Intentionally ordering multiple sizes/colours with the plan to return most. Legitimate shopping behavior that becomes costly at scale. Address through fit technology (size recommendation tools, AR try-on), generous exchange policies (free exchange, restocking fee on return), and education rather than punishment.
- **Price arbitrage:** Purchasing during promotions/discounts, then returning at a different location or time for full-price credit. Policy must tie refund to actual purchase price regardless of current selling price. Cross-channel returns are the primary vector.
- **Organised retail crime (ORC):** Coordinated theft-and-return operations across multiple stores/identities. Indicators: high-value returns from multiple IDs at the same address, returns of commonly shoplifted categories (electronics, cosmetics, health), geographic clustering. Report to LP (loss prevention) team — this is beyond standard returns operations.

## Vendor Recovery

Not all returns are the customer's fault. Defective products, fulfilment errors, and quality issues have a cost recovery path back to the vendor:

- **Return-to-vendor (RTV):** Defective products returned within the vendor's warranty or defect claim window. Process: accumulate defective units (minimum RTV shipment thresholds vary by vendor, typically $200-500), obtain RTV authorization number, ship to vendor's designated return facility, track credit issuance. Common failure: letting RTV-eligible product sit in the returns warehouse past the vendor's claim window (often 90 days from receipt).
- **Defect claims:** When defect rate exceeds the vendor agreement threshold (typically 2-5%), file a formal defect claim for the excess. Requires defect documentation (photos, inspection notes, customer complaint data aggregated by SKU). Vendors will challenge — your data quality determines your recovery.
- **Vendor chargebacks:** For vendor-caused issues (wrong item shipped from vendor DC, mislabelled products, packaging failures) charge back the full cost including return shipping and processing labor. Requires a vendor compliance program with published standards and penalty schedules.
- **Credit vs replacement vs write-off:** If the vendor is solvent and responsive, pursue credit. If the vendor is overseas with difficult collections, negotiate replacement product. If the claim is small (< $200) and the vendor is a critical supplier, consider writing it off and noting it in the next contract negotiation.

## Warranty Management

Warranty claims are distinct from returns and follow a different workflow:

- **Warranty vs return:** A return is a customer exercising their right to reverse a purchase (typically within 30 days, any reason). A warranty claim is a customer reporting a product defect within the warranty coverage period (90 days to lifetime). Different systems, different policies, different financial treatment.
- **Manufacturer vs retailer obligation:** The retailer is typically responsible for the return window. The manufacturer is responsible for the warranty period. Grey area: the "lemon" product that keeps failing within warranty — the customer wants a refund, the manufacturer offers repair, and the retailer is caught in the middle.
- **Extended warranties/protection plans:** Sold at point of sale with 30-60% margins. Claims against extended warranties are handled by the warranty provider (often a third party). Retailer's role is facilitating the claim, not processing it. Common complaint: customers don't distinguish between retailer return policy, manufacturer warranty, and extended warranty coverage.
