## Decision Frameworks

### Job Priority Sequencing

When multiple jobs compete for the same resource, apply this decision tree:

1. **Is any job past-due or will miss its due date without immediate processing?** → Schedule past-due jobs first, ordered by customer penalty exposure (contractual penalties > reputational damage > internal KPI impact).
2. **Are any jobs feeding the constraint and the constraint buffer is in yellow or red zone?** → Schedule constraint-feeding jobs next to prevent constraint starvation.
3. **Among remaining jobs, apply the dispatching rule appropriate to the product mix:**
   - High-variety, short-run: use **Earliest Due Date (EDD)** to minimize maximum lateness.
   - Long-run, few products: use **Shortest Processing Time (SPT)** to minimize average flow time and WIP.
   - Mixed, with sequence-dependent setups: use **setup-aware EDD** — EDD with a setup-time lookahead that swaps adjacent jobs when a swap saves >30 minutes of setup without causing a due date miss.
4. **Tie-breaker:** Higher customer tier wins. If same tier, higher margin job wins.

### Changeover Sequence Optimization

1. **Build the setup matrix:** For each pair of products (A→B, B→A, A→C, etc.), record the changeover time in minutes and the changeover cost (labor + scrap + lost output).
2. **Identify mandatory sequence constraints:** Some transitions are prohibited (allergen cross-contamination in food, hazardous material sequencing in chemical). These are hard constraints, not optimizable.
3. **Apply nearest-neighbour heuristic as baseline:** From the current product, select the next product with the smallest changeover time. This gives a feasible starting sequence.
4. **Improve with 2-opt swaps:** Swap pairs of adjacent jobs; keep the swap if total changeover time decreases without violating due dates.
5. **Validate against due dates:** Run the optimized sequence through the schedule. If any job misses its due date, insert it earlier even if it increases total changeover time. Due date compliance trumps changeover optimization.

### Disruption Re-Sequencing

When a disruption invalidates the current schedule:

1. **Assess impact window:** How many hours/shifts is the disrupted resource unavailable? Is it the constraint?
2. **Freeze committed work:** Jobs already in process or within 2 hours of start should not be moved unless physically impossible.
3. **Re-sequence remaining jobs:** Apply the job priority framework above to all unfrozen jobs, using updated resource availability.
4. **Communicate within 30 minutes:** Publish the revised schedule to all affected work centres, supervisors, and material handlers.
5. **Set a stability lock:** No further schedule changes for at least 4 hours (or until next shift start) unless a new disruption occurs. Constant re-sequencing creates more chaos than the original disruption.

### Bottleneck Identification

1. **Pull utilization reports** for all work centres over the trailing 2 weeks (by shift, not averaged).
2. **Rank by utilization ratio** (load hours / available hours). The top work centre is the suspected constraint.
3. **Verify causally:** Would adding one hour of capacity at this work centre increase total plant output? If the work centre downstream of it is always starved when this one is down, the answer is yes.
4. **Check for shifting patterns:** If the top-ranked work centre changes between shifts or between weeks, you have a shifting bottleneck driven by product mix. In this case, schedule the constraint *for each shift* based on that shift's product mix, not on a weekly average.
5. **Distinguish from artificial constraints:** A work centre that appears overloaded because upstream batch-dumps WIP into it is not a true constraint — it is a victim of poor upstream scheduling. Fix the upstream release rate before adding capacity to the victim.
