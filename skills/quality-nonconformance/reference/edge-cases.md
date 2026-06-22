# Key Edge Cases

These are situations where the obvious approach is wrong. Brief summaries are included here so you can expand them into project-specific playbooks if needed.

1. **Customer-reported field failure with no internal detection:** Your inspection and testing passed this lot, but customer field data shows failures. The instinct is to question the customer's data — resist it. Check whether your inspection plan covers the actual failure mode. Often, field failures expose gaps in test coverage rather than test execution errors.

2. **Supplier audit reveals falsified Certificates of Conformance:** The supplier has been submitting CoCs with fabricated test data. Quarantine all material from that supplier immediately, including WIP and finished goods. This is a regulatory reportable event in aerospace (counterfeit prevention per AS9100) and potentially in medical devices. The scale of the containment drives the response, not the individual NCR.

3. **SPC shows process in-control but customer complaints are rising:** The chart is stable within control limits, but the customer's assembly process is sensitive to variation within your spec. Your process is "capable" by the numbers but not capable enough. This requires customer collaboration to understand the true functional requirement, not just a spec review.

4. **Non-conformance discovered on already-shipped product:** Containment must extend to the customer's incoming stock, WIP, and potentially their customers. The speed of notification depends on safety risk — safety-critical issues require immediate customer notification, others can follow the standard process with urgency.

5. **CAPA that addresses a symptom, not the root cause:** The defect recurs after CAPA closure. Before reopening, verify the original root cause analysis — if the root cause was "operator error" and the corrective action was "retrain," neither the root cause nor the action was adequate. Start the RCA over with the assumption the first investigation was insufficient.

6. **Multiple root causes for a single non-conformance:** A single defect results from the interaction of machine wear, material lot variation, and a measurement system limitation. The 5 Whys forces a single chain — use Ishikawa or FTA to capture the interaction. Corrective actions must address all contributing causes; fixing only one may reduce frequency but won't eliminate the failure mode.

7. **Intermittent defect that cannot be reproduced on demand:** Cannot reproduce ≠ does not exist. Increase sample size and monitoring frequency. Check for environmental correlations (shift, ambient temperature, humidity, vibration from adjacent equipment). Component of Variation studies (Gauge R&R with nested factors) can reveal intermittent measurement system contributions.

8. **Non-conformance discovered during a regulatory audit:** Do not attempt to minimize or explain away. Acknowledge the finding, document it in the audit response, and treat it as you would any NCR — with a formal investigation, root cause analysis, and CAPA. Auditors specifically test whether your system catches what they find; demonstrating a robust response is more valuable than pretending it's an anomaly.
