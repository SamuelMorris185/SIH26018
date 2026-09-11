# Database Migrations — SIH26018

Database schema migrations are managed via **Alembic**.

## Generating Migrations
To generate a new migration after modifying models in `backend/app/models/`:

```bash
cd backend
alembic revision --autogenerate -m "Describe change"
```

## Applying Migrations
To apply pending migrations to your PostgreSQL database:

```bash
cd backend
alembic upgrade head
```
