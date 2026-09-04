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

## After changing dependencies

`node_modules` is a named volume, so it shadows whatever the image installed and
survives a rebuild. The frontend container therefore runs `npm install` on start,
which picks up anything added to `package.json`. After changing dependencies,
rebuild and recreate the container so that runs:

```bash
docker compose up -d --build frontend
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

Each filter only lists values that still match the other choices, so a
combination cannot be assembled that returns nothing. Selecting a researcher,
for example, narrows the institution list to the one that employs them and the
target organism list to the organisms their analyses detect. A filter with
nothing left to offer is disabled rather than silently empty.

## Exploring the results

Every name shown in a search result opens a detail view: the institution, each
instrument, each analysis offering, each target organism and each researcher.
The panel lists what that record is connected to, and those connections are
themselves clickable, so an instrument leads to the analyses that use it, an
analysis to its institution, organisms and researchers, and a researcher back
to their institution. `Back` walks the trail in reverse. A selected filter has
a `View details` link that opens the same view for the filtered entity.

An institution shows a zoomable map of its location, drawn with
[Leaflet](https://leafletjs.com) over OpenStreetMap tiles.

The position comes from the institution's street address. The address is looked
up once, when the institution is created, using OpenStreetMap's
[Nominatim](https://nominatim.openstreetmap.org) service, and the resulting
coordinates are stored on the record. Nothing is geocoded when the catalog is
browsed. An address that cannot be found still creates the institution; the form
says so, and the detail view shows a note instead of an empty map.

This means two outbound dependencies at runtime: map tiles from
`tile.openstreetmap.org` in the browser, and address lookups to
`nominatim.openstreetmap.org` from the API when an institution is created.
Everything else works offline against the local API. Set
`APP_GEOCODING_ENABLED=false` to skip lookups entirely. Nominatim's usage policy
asks for an identifying `User-Agent` and limits request rates, so set
`APP_GEOCODING_USER_AGENT` to your own deployment before using the public
service in earnest, or point `APP_GEOCODING_URL` at your own instance.

Seeded institutions carry invented street addresses and hardcoded coordinates,
so seeding never needs the network.

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
