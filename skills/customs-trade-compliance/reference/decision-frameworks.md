# Decision Frameworks

### Classification Decision Logic

When classifying a product, follow this sequence without shortcuts. Convert it into an internal decision tree before automating any tariff-classification workflow.

1. **Identify the good precisely.** Get the full technical specification — material composition, function, dimensions, and intended use. Never classify from a product name alone.
2. **Determine the Section and Chapter.** Use the Section and Chapter notes to confirm or exclude. Chapter notes override heading text.
3. **Apply GRI 1.** Read the heading terms literally. If only one heading covers the good, classification is decided.
4. **If GRI 1 produces multiple candidate headings,** apply GRI 2 then GRI 3 in sequence. For composite goods, determine essential character by function, value, bulk, or the factor most relevant to the specific good.
5. **Validate at the subheading level.** Apply GRI 6. Check subheading notes. Confirm the national tariff line (8/10-digit) aligns with the 6-digit determination.
6. **Check for binding rulings.** Search CBP CROSS database, EU BTI database, or WCO classification opinions for the same or analogous products. Existing rulings are persuasive even if not directly binding.
7. **Document the rationale.** Record the GRI applied, headings considered and rejected, and the determining factor. This documentation is your defence in an audit.

### FTA Qualification Analysis

1. **Identify applicable FTAs** based on origin and destination countries.
2. **Determine the product-specific rule of origin.** Look up the HS heading in the relevant FTA's annex. Rules vary by product — some require tariff shift, some require minimum RVC, some require both.
3. **Trace all non-originating materials** through the bill of materials. Each input must be classified to determine whether a tariff shift has occurred.
4. **Calculate RVC if required.** Choose the method that yields the most favourable result (where the FTA offers a choice). Verify all cost data with the supplier.
5. **Apply cumulation rules.** USMCA allows accumulation across the US, Mexico, and Canada. EU-UK TCA allows bilateral cumulation. RCEP allows diagonal cumulation among all 15 parties.
6. **Prepare the certification.** USMCA certifications must include nine prescribed data elements. EUR.1 requires Chamber of Commerce or customs authority endorsement. Retain supporting documentation for 5 years (USMCA) or 4 years (EU).

### Valuation Method Selection

Customs valuation follows the WTO Agreement on Customs Valuation (based on GATT Article VII). Methods are applied in hierarchical order — you only proceed to the next method when the prior method cannot be applied:

1. **Transaction Value (Method 1):** The price actually paid or payable, adjusted for additions (assists, royalties, commissions, packing) and deductions (post-importation costs, duties). This is used for ~90% of entries. Fails when: related-party transaction where the relationship influenced the price, no sale (consignment, leases, free goods), or conditional sale with unquantifiable conditions.
2. **Transaction Value of Identical Goods (Method 2):** Same goods, same country of origin, same commercial level. Rarely available because "identical" is strictly defined.
3. **Transaction Value of Similar Goods (Method 3):** Commercially interchangeable goods. Broader than Method 2 but still requires same country of origin.
4. **Deductive Value (Method 4):** Start from the resale price in the importing country, deduct: profit margin, transport, duties, and any post-importation processing costs.
5. **Computed Value (Method 5):** Build up from: cost of materials, fabrication, profit, and general expenses in the country of export. Only available if the exporter cooperates with cost data.
6. **Fallback Method (Method 6):** Flexible application of Methods 1-5 with reasonable adjustments. Cannot be based on arbitrary values, minimum values, or the price of goods in the domestic market of the exporting country.

### Screening Hit Assessment

When a restricted party screening tool returns a match, do not block the transaction automatically or clear it without investigation. Follow this protocol:

1. **Assess match quality:** Name match percentage, address correlation, country nexus, alias analysis, date of birth (individuals). Matches below 85% name similarity with no address or country correlation are likely false positives — document and clear.
2. **Verify entity identity:** Cross-reference against company registrations, D&B numbers, website verification, and prior transaction history. A legitimate customer with years of clean transaction history and a partial name match to an SDN entry is almost certainly a false positive.
3. **Check list specifics:** SDN hits require OFAC licence to proceed. Entity List hits require BIS licence with a presumption of denial. Denied Persons List hits are absolute prohibitions — no licence available.
4. **Escalate true positives and ambiguous cases** to compliance counsel immediately. Never proceed with a transaction while a screening hit is unresolved.
5. **Document everything.** Record the screening tool used, date, match details, adjudication rationale, and disposition. Retain for 5 years minimum.
