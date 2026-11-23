import pytest
from fastapi.testclient import TestClient

from app.modules.catalog.service import slugify


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Institute of Virology", "institute-of-virology"),
        ("Čačak", "cacak"),
        ("Đurđevdan", "djurdjevdan"),
        ("Žitište Šabac Ćuprija", "zitiste-sabac-cuprija"),
        ("Универзитет у Београду", "univerzitet-u-beogradu"),
        ("ЉУБЉАНА Њујорк Џеп", "ljubljana-njujork-dzep"),
        ("Ђурђевдан", "djurdjevdan"),
        ("Институт за вирусологију", "institut-za-virusologiju"),
        ("Institut „Torlak” – Beograd", "institut-torlak-beograd"),
        ("Novi Sad / Нови Сад", "novi-sad-novi-sad"),
        ("  Faculté   de Médecine  ", "faculte-de-medecine"),
        ("", "institution"),
        ("—…—", "institution"),
        ("北京大学", "institution"),
    ],
)
def test_slugify_transliterates_serbian_and_strips_diacritics(name: str, expected: str) -> None:
    assert slugify(name) == expected


def test_cyrillic_and_latin_spellings_share_a_slug() -> None:
    assert slugify("Ниш") == slugify("Niš") == "nis"
    assert slugify("Ђорђе Јовановић") == slugify("Đorđe Jovanović") == "djordje-jovanovic"


def _post_institution(client: TestClient, payload: dict):
    return client.post(
        "/api/v1/catalog/institutions",
        json={"city": "Belgrade", "country": "Serbia", **payload},
    )


def test_distinct_cyrillic_names_get_distinct_slugs(client: TestClient) -> None:
    first = _post_institution(client, {"name": "Универзитет у Београду"})
    second = _post_institution(client, {"name": "Институт за вирусологију"})
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["slug"] == "univerzitet-u-beogradu"
    assert second.json()["slug"] == "institut-za-virusologiju"


def test_cyrillic_name_conflicts_with_its_latin_spelling(client: TestClient) -> None:
    assert _post_institution(client, {"name": "Универзитет у Нишу"}).status_code == 201
    assert _post_institution(client, {"name": "Univerzitet u Nišu"}).status_code == 409


def test_an_explicit_slug_is_kept_as_given(client: TestClient) -> None:
    response = _post_institution(client, {"name": "Универзитет у Крагујевцу", "slug": "unikg"})
    assert response.status_code == 201, response.text
    assert response.json()["slug"] == "unikg"
