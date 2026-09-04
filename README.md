# SciConnect v2

Clean implementation of SciConnect as a modular monolith:

- React frontend (next stage)
- FastAPI backend
- PostgreSQL database
- SQLAlchemy 2 and Alembic

The old .NET/Angular solution is not a dependency of this project.

## Domain idea

The central resource is an institution capability. An institution owns concrete
instrument units, employs researchers and offers concrete analyses. An offered
analysis can use one or more instruments belonging to the same institution, can
be performed by one or more of its researchers, and can support one or more
target microorganisms.

This lets the API answer strict combinations such as:

- institution + instrument
- institution + analysis
- analysis + instrument used for that analysis
- analysis + researcher who performs it
- institution + analysis + instrument + microorganism + researcher

## Run with Docker

Copy `.env.example` to `.env`, change the password, then run:

```bash
docker compose up --build
```

The API container runs `alembic upgrade head` and then loads demo data before
serving, so a first `up` against an empty volume already has something to
search. Seeding is a no-op once the catalog holds any data, so restarts and
rebuilds never touch what is already there.

The seed creates five fictional Serbian institutions with eleven concrete
instruments, seven researchers, ten institutional analysis offerings and six
microorganism targets, all wired together with explicit capability links.
Example domains and names use `example.org`; no seed record represents a real
institution or person.

To start with an empty database instead, set `APP_SEED_ON_STARTUP=false` in
`.env` (or the environment). The seed can always be run by hand:

```bash
docker compose exec api python -m app.seed
```

To get the demo data back after changing it, discard the volume and start over.
This deletes everything in the local database:

```bash
docker compose down -v && docker compose up --build
```

Open:

- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health
- React application: http://localhost:5173

Example strict combination search:

```text
GET /api/v1/capabilities/search?analysis_type_ids=1&instrument_type_ids=1&microorganism_ids=1&researcher_ids=1
```

Filters from different categories use `AND`. Multiple IDs inside one category
currently use `OR`.

## Adding data

The React application has an **Add & connect** tab, and the API exposes the same
operations: `POST` endpoints create institutions, instrument types, analysis
types, target organisms, researchers, institution instruments and institution
analysis offerings, and three link endpoints connect an analysis offering to an
instrument, a target organism or a researcher.

Relationships are never inferred. An analysis offering only becomes searchable
through an instrument, organism or researcher after the corresponding link is
created, and an offering can only be linked to instruments and researchers of
its own institution. See [docs/domain-model.md](docs/domain-model.md) for the
full endpoint list and error semantics.

These endpoints are currently unauthenticated, which is fine for local
development but must be placed behind administrator authentication before any
public deployment.
