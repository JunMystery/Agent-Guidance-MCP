"""Reasoning framework templates and task classifier."""


REASONING_FRAMEWORKS: dict[str, dict[str, object]] = {
    "decision": {
        "skills": ("council", "doubt-driven-development"),
        "framework": (
            "## Four-Voice Council\n\n"
            "1. **The Optimist**: What's the best case? Why does this make sense?\n"
            "2. **The Skeptic**: What's the worst case? What could go wrong?\n"
            "3. **The Pragmatist**: What's the effort? Is this reversible?\n"
            "4. **The Architect**: How does this fit the larger system?\n\n"
            "## Decision Matrix\n\n"
            "| Option | Pros | Cons | Risk | Effort |\n"
            "|--------|------|------|------|--------|\n"
            "| A | | | | |\n"
            "| B | | | | |\n"
        ),
        "questions": (
            "What is the worst-case outcome?",
            "Is this decision reversible?",
            "What would I do if this fails?",
            "Am I solving the actual problem or a symptom?",
        ),
    },
    "bug": {
        "skills": ("debugging-and-error-recovery",),
        "framework": (
            "## Systematic Root-Cause Debugging\n\n"
            "1. **Reproduce**: Can I reliably trigger the error?\n"
            "2. **Isolate**: What is the minimal reproduction case?\n"
            "3. **Hypothesize**: What is my theory for the cause?\n"
            "4. **Test**: How can I prove or disprove the hypothesis?\n"
            "5. **Verify**: After the fix, does the original case pass?\n"
        ),
        "questions": (
            "What changed recently?",
            "What is the minimal reproduction?",
            "Is this a symptom or the root cause?",
            "Are there related errors in logs?",
        ),
    },
    "architecture": {
        "skills": ("architecture-decision-records", "api-design"),
        "framework": (
            "## Architecture Decision Record (ADR)\n\n"
            "**Context**: What is the problem? What are the constraints?\n"
            "**Decision**: What did we decide?\n"
            "**Status**: Proposed | Accepted | Deprecated\n"
            "**Consequences**: What follows?\n\n"
            "## Tradeoff Matrix\n\n"
            "| Criterion | Option A | Option B | Option C |\n"
            "|-----------|----------|----------|----------|\n"
            "| Complexity | | | |\n"
            "| Scalability | | | |\n"
            "| Maintainability | | | |\n"
            "| Team familiarity | | | |\n"
        ),
        "questions": (
            "What are the hard constraints?",
            "What is the blast radius of this change?",
            "Is this over-engineered for the current need?",
            "How does this evolve as the system grows?",
        ),
    },
    "security": {
        "skills": ("security-review",),
        "framework": (
            "## Threat Model\n\n"
            "1. **Assets**: What are we protecting?\n"
            "2. **Attack Surface**: Where can an attacker reach?\n"
            "3. **Threats**: What can go wrong?\n"
            "4. **Mitigations**: How do we defend?\n"
            "5. **Residual Risk**: What remains after mitigations?\n"
        ),
        "questions": (
            "What is the attack surface?",
            "Where are the auth boundaries?",
            "What data is exposed if this is compromised?",
            "Are there secrets in the code or logs?",
        ),
    },
    "performance": {
        "skills": ("performance-optimization", "backend-patterns"),
        "framework": (
            "## Performance Optimization Loop\n\n"
            "1. **Measure**: What is the baseline metric?\n"
            "2. **Diagnose**: Where is the bottleneck?\n"
            "3. **Optimize**: What is the smallest change with biggest impact?\n"
            "4. **Verify**: Did the metric improve?\n"
            "5. **Repeat**: Move to the next bottleneck\n"
        ),
        "questions": (
            "Where exactly is the bottleneck?",
            "What is the current baseline metric?",
            "How will I measure improvement?",
            "Is this premature optimization?",
        ),
    },
    "general": {
        "skills": ("karpathy-principles",),
        "framework": (
            "## Karpathy Coding Principles\n\n"
            "1. **Verify before trusting**: Never assume code works. Run it.\n"
            "2. **Small steps, verify each**: Make one change, test, repeat.\n"
            "3. **Read the error**: Errors contain the answer. Read carefully.\n"
            "4. **Don't guess**: If unsure, search, read, or ask.\n"
            "5. **Simplicity wins**: Prefer the simplest solution that works.\n"
            "6. **Context matters**: Understand the surrounding code before changing.\n"
        ),
        "questions": (
            "Did I verify this works by running it?",
            "Am I guessing or have I confirmed?",
            "Is this the simplest approach that works?",
            "Did I read the surrounding context?",
        ),
    },
}


REASONING_KEYWORDS: dict[str, set[str]] = {
    "decision": {
        "should", "which", "vs", "versus", "tradeoff", "trade-off", "choose",
        "better", "best", "compare", "alternative", "alternatives", "option",
        "decision", "decide", "pick", "select",
    },
    "bug": {
        "bug", "fail", "failing", "failed", "error", "errors", "broken",
        "crash", "crashed", "crashing", "exception", "traceback", "unexpected",
        "wrong", "incorrect", "issue", "problem", "regression",
    },
    "architecture": {
        "architecture", "design", "structure", "structural", "refactor",
        "refactoring", "pattern", "patterns", "module", "modules", "layer",
        "layers", "component", "components", "system", "systems", "schema",
        "migrate", "migration", "dependency", "coupling",
    },
    "security": {
        "security", "secure", "auth", "authentication", "authorization",
        "vulnerability", "vulnerable", "attack", "exploit", "secret",
        "secrets", "token", "tokens", "password", "encryption", "csrf",
        "xss", "injection", "owasp", "compliance", "breach",
    },
    "performance": {
        "performance", "slow", "slowness", "fast", "faster", "speed",
        "optimize", "optimization", "bottleneck", "latency", "throughput",
        "memory", "cpu", "cache", "caching", "scale", "scaling", "benchmark",
    },
}


def classify_reasoning_type(task: str) -> str:
    """Classify a task string into a reasoning framework type."""
    task_lower = task.lower()
    words = set()
    for word in task_lower.split():
        cleaned = word.strip(".,:;()[]{}\"'!?-").lower()
        if cleaned:
            words.add(cleaned)

    best_type = "general"
    best_score = 0
    for rtype, keywords in REASONING_KEYWORDS.items():
        score = len(words & keywords)
        if score > best_score:
            best_score = score
            best_type = rtype

    return best_type


def get_reasoning_framework(task: str) -> dict[str, object]:
    """Return the reasoning framework for a given task."""
    rtype = classify_reasoning_type(task)
    framework = REASONING_FRAMEWORKS.get(rtype, REASONING_FRAMEWORKS["general"])
    return {
        "task": task,
        "framework_type": rtype,
        "skills_to_invoke": list(framework["skills"]),
        "framework": framework["framework"],
        "key_questions": list(framework["questions"]),
        "reasoning_skill_uris": [
            f"standards://skill/{s}" for s in framework["skills"]
        ],
    }
