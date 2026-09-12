Alembic migrations directory for the backend.

Usage:

1. Install alembic in your environment (already in requirements.txt).
2. To create a new migration (autogenerate):

   cd backend
   alembic -c alembic.ini revision --autogenerate -m "create initial tables"

3. To apply migrations:

   alembic -c alembic.ini upgrade head

If you use Docker Compose, set the `DATABASE_URL` env var to point to the
Postgres container or adjust `alembic.ini` accordingly.
