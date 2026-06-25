---
name: backend-hub
description: Use for backend, API, database, server-side architecture, framework patterns, service boundaries, migrations, and Python, Django, FastAPI, Java/Spring/Quarkus, Node/Nest, Laravel, Go, Rust, .NET, or database tasks. Routes to focused backend skills so agents can start with one domain call.
dependencies: [backend-core, backend-frameworks, data-platforms, api-integrations, android-clean-architecture, django-celery, jpa-patterns, kotlin-coroutines-flows, kotlin-exposed-patterns, swift-actor-persistence, swift-concurrency-6-2]
---

# Backend Hub

Use this as the first backend skill call. Load only the focused skill(s) needed for the task:

- General backend architecture, API contract design, error handling, hexagonal boundaries, deployment, or Flox setup: `backend-core`
- Framework-specific implementation (FastAPI, Django, NestJS, Laravel, Spring Boot, Quarkus, Go, Rust, Python, .NET, Kotlin, C++, etc.): `backend-frameworks`
- Database migrations, performance optimization, caching strategies (Postgres, MySQL, Redis, Prisma, ClickHouse), latency-critical services, or content-hash caching: `data-platforms`
- External API connectors, MCP servers, cryptography integrations (Keccak), and payment orchestration / x402 endpoints: `api-integrations`

Keep specialized domain patterns separate:
- Android clean architecture: `android-clean-architecture`
- Django async/jobs: `django-celery`
- Java/JVM persistence: `jpa-patterns`
- Kotlin coroutines, flows, or Exposed persistence: `kotlin-coroutines-flows`, `kotlin-exposed-patterns`
- Swift persistence: `swift-actor-persistence`, `swift-concurrency-6-2`
- MLE workflows and RecSys pipelines: `mle-workflow`, `pytorch-patterns`, `recsys-pipeline-architect`
- Healthcare and domain backend workflows: `healthcare-emr-patterns`, `healthcare-cdss-patterns`

Start with contracts, data ownership, failure modes, and test boundaries before changing implementation details.
