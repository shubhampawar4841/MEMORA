# Nerva — deferred production work (Phase G)

Intentionally **not implemented** yet. Ship RAG quality, eval, docs, chat,
streaming, and hybrid search first.

When ready, tackle in this order:

1. Authentication and per-user document isolation
2. PostgreSQL for document + conversation metadata
3. Object storage for original PDFs (S3 / R2 / GCS)
4. Hosted vector database if local Chroma is no longer enough
5. Rate limiting on upload / ask
6. Structured logging + error monitoring (e.g. Sentry)
7. Background PDF ingestion workers

Do not start Phase G while evaluation scores are still unmeasured or weak.
