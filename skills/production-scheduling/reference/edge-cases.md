## Key Edge Cases

Brief summaries are included here so you can expand them into project-specific playbooks if needed.

1. **Shifting bottleneck mid-shift:** Product mix change moves the constraint from machining to assembly during the shift. The schedule that was optimal at 6:00 AM is wrong by 10:00 AM. Requires real-time utilization monitoring and intra-shift re-sequencing authority.

2. **Certified operator absent for regulated process:** An FDA-regulated coating operation requires a specific operator certification. The only certified night-shift operator calls in sick. The line cannot legally run. Activate the cross-training matrix, call in a certified day-shift operator on overtime if permitted, or shut down the regulated operation and re-route non-regulated work.

3. **Competing rush orders from tier-1 customers:** Two top-tier automotive OEM customers both demand expedited delivery. Satisfying one delays the other. Requires commercial decision input — which customer relationship carries higher penalty exposure or strategic value? The scheduler identifies the tradeoff; management decides.

4. **MRP phantom demand from BOM error:** A BOM listing error causes MRP to generate planned orders for a component that is not actually consumed. The scheduler sees a work order with no real demand behind it. Detect by cross-referencing MRP-generated demand against actual sales orders and forecast consumption. Flag and hold — do not schedule phantom demand.

5. **Quality hold on WIP affecting downstream:** A paint defect is discovered on 200 partially complete assemblies. These were scheduled to feed the final assembly constraint tomorrow. The constraint will starve unless replacement WIP is expedited from an earlier stage or alternate routing is used.

6. **Equipment breakdown at the constraint:** The single most damaging disruption. Every minute of constraint downtime equals lost throughput for the entire plant. Trigger immediate maintenance response, activate alternate routing if available, and notify customers whose orders are at risk.

7. **Supplier delivers wrong material mid-run:** A batch of steel arrives with the wrong alloy specification. Jobs already kitted with this material cannot proceed. Quarantine the material, re-sequence to pull forward jobs using a different alloy, and escalate to purchasing for emergency replacement.

8. **Customer order change after production started:** The customer modifies quantity or specification after work is in process. Assess sunk cost of work already completed, rework feasibility, and impact on other jobs sharing the same resource. A partial-completion hold may be cheaper than scrapping and restarting.
