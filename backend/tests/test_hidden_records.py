"""Drafts and archived records are for the admin, not for every visitor.

A guest who asks for one by id, or finds it by name, is answered as if it did
not exist; the same request carrying the admin key sees it with its status.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import ADMIN_TOKEN_HEADER
from app.modules.catalog.models import Institution, Researcher


@pytest.fixture
def records(db: Session) -> dict[str, int]:
    public = Institution(name="Open Institute", slug="open", city="Nis", country="Serbia")
    draft = Institution(
        name="Draft Institute",
        slug="draft",
        city="Nis",
        country="Serbia",
        status="draft",
        contact_email="draft@example.org",
    )
    db.add_all([public, draft])
    db.flush()
    archived_person = Researcher(
        institution_id=public.id,
        full_name="Archived Person",
        email="gone@example.org",
        status="archived",
    )
    draft_person = Researcher(
        institution_id=draft.id, full_name="Drafted Person", email="new@example.org"
    )
    db.add_all([archived_person, draft_person])
    db.commit()
    return {
        "public": public.id,
        "draft": draft.id,
        "archived_person": archived_person.id,
        "draft_person": draft_person.id,
    }


HIDDEN = [
    ("/catalog/institutions/{}", "draft"),
    ("/catalog/researchers/{}", "archived_person"),
    ("/catalog/researchers/{}", "draft_person"),
]


@pytest.mark.parametrize(("path", "record"), HIDDEN)
def test_a_guest_gets_404_for_a_hidden_record(
    client: TestClient, admin_token: str, records, path: str, record: str
) -> None:
    response = client.get(f"/api/v1{path.format(records[record])}")

    assert response.status_code == 404


@pytest.mark.parametrize(("path", "record"), HIDDEN)
def test_an_admin_still_sees_it(
    client: TestClient, admin_token: str, records, path: str, record: str
) -> None:
    for headers in ({ADMIN_TOKEN_HEADER: admin_token}, {"Authorization": f"Bearer {admin_token}"}):
        response = client.get(f"/api/v1{path.format(records[record])}", headers=headers)
        assert response.status_code == 200


def test_a_wrong_key_is_a_guest(client: TestClient, admin_token: str, records) -> None:
    response = client.get(
        f"/api/v1/catalog/institutions/{records['draft']}",
        headers={ADMIN_TOKEN_HEADER: "wrong"},
    )

    assert response.status_code == 404


def test_a_public_record_is_open_to_a_guest(
    client: TestClient, admin_token: str, records
) -> None:
    assert client.get(f"/api/v1/catalog/institutions/{records['public']}").status_code == 200


def test_search_shows_a_guest_only_what_they_could_open(
    client: TestClient, admin_token: str, records
) -> None:
    def labels(**headers: str) -> set[str]:
        response = client.get("/api/v1/search?q=e", headers=headers)
        return {item["label"] for item in response.json()["items"]}

    guest = labels()
    admin = labels(Authorization=f"Bearer {admin_token}")

    assert guest == {"Open Institute"}
    assert {"Draft Institute", "Archived Person", "Drafted Person"} <= admin


def test_without_a_configured_key_everyone_is_admin(client: TestClient, records) -> None:
    """Development with no key: the gate is open for reads as it is for writes."""
    assert client.get(f"/api/v1/catalog/institutions/{records['draft']}").status_code == 200
