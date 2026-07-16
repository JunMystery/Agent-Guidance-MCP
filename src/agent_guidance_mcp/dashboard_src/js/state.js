export let pollBackoff = 1000;

export function setBackoff(v) { pollBackoff = v; }
export function resetBackoff() { pollBackoff = 1000; }
