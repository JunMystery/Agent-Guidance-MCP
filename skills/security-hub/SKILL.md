---
name: security-hub
description: Use for security review, vulnerability scanning, auth, secrets, OWASP, framework security, DeFi AMM security, LLM trading-agent security, and compliance-sensitive implementation tasks. Routes to focused security skills so agents can start with one domain call.
dependencies: [security-and-hardening, framework-security, regulated-security]
---

# Security Hub

Use this as the first security skill call. Load only the focused skill(s) needed for the task:

- General code security review, vulnerability research, bounty triage, automated scans, safety gates, and behavioral guardrails: `security-and-hardening`
- Framework-specific security configurations and controls (Django, Laravel, Spring Boot, Quarkus, Perl): `framework-security`
- Regulated compliance (HIPAA, healthcare PHI) and domain-specific risk systems (DeFi AMM, trading agent security, prediction markets, EVM token decimals): `regulated-security`

Prioritize concrete exploit paths, secret exposure, authz/authn boundaries, unsafe data handling, and regression tests for security fixes.
