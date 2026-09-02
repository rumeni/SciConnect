# SciConnect v2

Clean implementation of SciConnect as a modular monolith:

- React frontend (next stage)
- FastAPI backend
- PostgreSQL database
- SQLAlchemy 2 and Alembic

The old .NET/Angular solution is not a dependency of this project.

## Domain idea

The central resource is an institution capability. An institution owns concrete
instrument units and offers concrete analyses. An offered analysis can use one
or more instruments belonging to the same institution and can support one or
more target microorganisms.

This lets the API answer strict combinations such as:

- institution + instrument
- institution + analysis
- analysis + instrument used for that analysis
- institution + analysis + instrument + microorganism

## Run with Docker

Copy `.env.example` to `.env`, change the password, then run:

```bash
docker compose up --build
```

Create demo data once the API container is running:

```bash
docker compose exec api python -m app.seed
```

The seed is idempotent and creates five fictional Serbian institutions with
eleven concrete instruments, ten institutional analysis offerings and six
microorganism targets. Example domains use `example.org`; no seed record
represents a real institution.

Open:

- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health
- React application: http://localhost:5173

Example strict combination search:

```text
GET /api/v1/capabilities/search?analysis_type_ids=1&instrument_type_ids=1&microorganism_ids=1
```

Filters from different categories use `AND`. Multiple IDs inside one category
currently use `OR`.
