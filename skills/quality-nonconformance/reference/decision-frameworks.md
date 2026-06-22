# Decision Frameworks

### NCR Disposition Decision Logic

Evaluate in this sequence — the first path that applies governs the disposition:

1. **Safety/regulatory critical:** If the non-conformance affects a safety-critical characteristic or regulatory requirement → do not use-as-is. Rework if possible to full conformance, otherwise scrap. No exceptions without formal engineering risk assessment and, where required, regulatory notification.
2. **Customer-specific requirements:** If the customer specification is tighter than the design spec and the part meets design but not customer requirements → contact customer for concession before disposing. Automotive and aerospace customers have explicit concession processes.
3. **Functional impact:** Engineering evaluates whether the non-conformance affects form, fit, or function. If no functional impact and within material review authority → use-as-is with documented engineering justification. If functional impact exists → rework or scrap.
4. **Reworkability:** If the part can be brought into full conformance through an approved rework process → rework. Verify rework cost vs. replacement cost. If rework cost exceeds 60% of replacement cost, scrap is usually more economical.
5. **Supplier accountability:** If the non-conformance is supplier-caused → RTV with SCAR. Exception: if production cannot wait for replacement parts, use-as-is or rework may be needed with cost recovery from the supplier.

### RCA Method Selection

- **Single-event, simple causal chain:** 5 Whys. Budget: 1-2 hours.
- **Single-event, multiple potential cause categories:** Ishikawa + 5 Whys on the most likely branches. Budget: 4-8 hours.
- **Recurring issue, process-related:** 8D with full team. Budget: 20-40 hours across D0-D8.
- **Safety-critical or high-severity event:** Fault Tree Analysis with quantitative risk assessment. Budget: 40-80 hours. Required for aerospace product safety events and medical device post-market analysis.
- **Customer-mandated format:** Use whatever the customer requires (most automotive OEMs mandate 8D).

### CAPA Effectiveness Verification

Before closing any CAPA, verify:

1. **Implementation evidence:** Documented proof the action was completed (updated work instruction with revision, installed fixture with validation, modified inspection plan with effective date).
2. **Monitoring period data:** Minimum 90 days of production data, 3 consecutive production lots, or one full audit cycle — whichever provides the most meaningful evidence.
3. **Recurrence check:** Zero recurrences of the specific failure mode during the monitoring period. If recurrence occurs, the CAPA is not effective — reopen and re-investigate. Do not close and open a new CAPA for the same issue.
4. **Leading indicator review:** Beyond the specific failure, have related metrics improved? (e.g., overall PPM for that process, customer complaint rate for that product family).

### Inspection Level Adjustment

| Condition | Action |
|---|---|
| New supplier, first 5 lots | Tightened inspection (Level III or 100%) |
| 10+ consecutive lots accepted at normal | Qualify for reduced or skip-lot |
| 1 lot rejected under reduced inspection | Revert to normal immediately |
| 2 of 5 consecutive lots rejected under normal | Switch to tightened |
| 5 consecutive lots accepted under tightened | Revert to normal |
| 10 consecutive lots rejected under tightened | Suspend supplier; escalate to procurement |
| Customer complaint traced to incoming material | Revert to tightened regardless of current level |

### Supplier Corrective Action Escalation

| Stage | Trigger | Action | Timeline |
|---|---|---|---|
| Level 1: SCAR issued | Single significant NC or 3+ minor NCs in 90 days | Formal SCAR requiring 8D response | 10 days for response, 30 for implementation |
| Level 2: Supplier on watch | SCAR not responded to in time, or corrective action not effective | Increased inspection, supplier on probation, procurement notified | 60 days to demonstrate improvement |
| Level 3: Controlled shipping | Continued quality failures during watch period | Supplier must submit inspection data with each shipment; or third-party sort at supplier's expense | 90 days to demonstrate sustained improvement |
| Level 4: New source qualification | No improvement under controlled shipping | Initiate alternate supplier qualification; reduce business allocation | Qualification timeline (3-12 months depending on industry) |
| Level 5: ASL removal | Failure to improve or unwillingness to invest | Formal removal from Approved Supplier List; transition all parts | Complete transition before final PO |
