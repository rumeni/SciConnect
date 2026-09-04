# SciConnect domain model

## Product purpose

SciConnect helps a public visitor discover an institution that can perform a
specific piece of scientific work. Search results are institutions together
with the exact capabilities that matched the selected criteria.

The system must not infer that an analysis uses an instrument merely because
both exist at the same institution.

## Vocabulary

### Institution

An organization that owns instruments and offers analyses. Only an active
institution is visible in public search.

### Instrument type

A normalized catalog concept such as `Real-Time PCR System`. It is used as a
search filter.

### Institution instrument

A concrete instrument unit belonging to an institution. It can contain a
manufacturer, model, local display name, operating status and access notes.

### Analysis type

A normalized catalog concept such as `Real-Time PCR` or `Mass Spectrometry`.

### Institution analysis

A concrete service offered by one institution. Availability, turnaround time
and public description belong here, because they can differ between
institutions offering the same analysis type.

### Analysis instrument link

An explicit statement that an institution analysis uses a concrete institution
instrument. Both records must belong to the same institution. This invariant is
checked in the service layer and by composite PostgreSQL foreign keys.

### Analysis target

A microorganism that a concrete institution analysis can detect, identify or
otherwise process. This is not evidence that the institution owns a specimen
or strain collection.

### Researcher

A person employed by exactly one institution, with an optional title, contact
address, ORCID and free-text expertise. A researcher is a capability holder,
not a public user account: there is no authentication behind this record.

### Analysis researcher link

An explicit statement that a researcher performs a concrete institution
analysis, with the role `lead`, `contributor` or `contact`. As with
instruments, both records must belong to the same institution, and the
invariant is checked in the service layer and by composite PostgreSQL foreign
keys.

## Search semantics

Filters from different categories are combined with `AND`:

```text
analysis type AND instrument type AND microorganism AND researcher AND location
```

Multiple values in the same category are initially combined with `OR`.

An instrument-only search finds institutions owning an operational instrument
of the selected type. If an analysis filter or target filter is also present,
the selected instrument must be explicitly linked to the same matching
institution analysis.

A researcher filter behaves the same way. On its own it finds institutions
employing the selected active researcher; combined with an analysis or target
filter, the researcher must be explicitly linked to the same matching
institution analysis.

Unavailable or archived capabilities are excluded from public results, and so
are researchers who are not active.

## Important invariants

1. An institution analysis belongs to exactly one institution.
2. An institution instrument belongs to exactly one institution.
3. An analysis cannot use an instrument owned by another institution, and
   cannot be performed by a researcher of another institution.
4. An institution can have only one initial offering per analysis type. This
   can later be relaxed if variants of the same analysis become a real need.
5. Turnaround time, when present, must be positive.
6. Catalog names, institution slugs and researcher ORCIDs are unique.
7. Public search returns only active institutions and usable capabilities.
8. A researcher belongs to exactly one institution.

## Deliberately postponed concepts

- specimen and strain collections;
- pricing and currencies;
- accreditation and certifications;
- public user accounts;
- collaboration requests;
- administrator authentication and audit history;
- researcher affiliation history across several institutions;
- write authorization: the create and connect endpoints are currently open;
- `match all` behavior for multiple selections from one category.

These should be added only after their domain meaning and workflows are agreed,
without weakening the capability relationships above.

## Writing data

Every concept above can be created over the API, and the three capability
relationships can be connected explicitly:

```text
POST /api/v1/catalog/institutions
POST /api/v1/catalog/instrument-types
POST /api/v1/catalog/analysis-types
POST /api/v1/catalog/microorganisms
POST /api/v1/catalog/researchers
POST /api/v1/catalog/institution-instruments
POST /api/v1/catalog/institution-analyses

POST /api/v1/institution-analyses/{id}/instruments
POST /api/v1/institution-analyses/{id}/targets
POST /api/v1/institution-analyses/{id}/researchers
```

A write that references a missing record answers `404`, a duplicate identity or
repeated link answers `409`, and a link that would cross institutions answers
`400`. Nothing infers a relationship: an analysis becomes searchable through an
instrument, organism or researcher only after the matching link is created.
