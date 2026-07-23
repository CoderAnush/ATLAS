# Services (Bounded Contexts)

Modular monolith contexts. Each folder is a **microservice candidate**.

Rules:
- Depend across contexts only via application APIs or events.
- Keep domain logic free of FastAPI/Celery imports.
- Logical DB schema per context.

See `ARCHITECTURE.md` and `idea.md`.
