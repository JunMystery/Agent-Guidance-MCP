export let pollBackoff = 1000;

export function setBackoff(v) { pollBackoff = v; }
export function resetBackoff() { pollBackoff = 1000; }

// Latest datasets, retained client-side so sort/filter re-renders without refetch.
export const store = {
  recent_actions: [],
  tool_breakdown: [],
};
