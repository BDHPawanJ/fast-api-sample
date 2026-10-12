"""Domain layer: business entities and rules.

Nothing in this package may import SQLAlchemy, FastAPI, or Pydantic. Persistence
is handled by repositories in ``app.adapters``, which map ORM rows to and from
these plain objects.
"""
