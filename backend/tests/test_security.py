"""What the public internet is and is not allowed to do."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import ADMIN_TOKEN_HEADER, token_is_valid

# One payload per shape of write, so the gate is proved on every kind of route
# rather than only on the first one in the file.
WRITES = [
    ("POST", "/api/v1/catalog/instrument-types", {"name": "Mass spectrometer"}),
    ("POST", "/api/v1/catalog/analysis-types", {"name": "Sequencing"}),
    ("POST", "/api/v1/catalog/microorganisms", {"scientific_name": "E. coli"}),
    ("POST", "/api/v1/catalog/institutions", {"name": "Institute", "city": "Novi Sad"}),
    ("DELETE", "/api/v1/catalog/institutions/1", None),
    ("DELETE", "/api/v1/catalog/researchers/1", None),
    ("DELETE", "/api/v1/institution-analyses/1/instruments/1", None),
]


def _send(client: TestClient, method: str, path: str, payload, **kwargs):
    return client.request(method, path, json=payload, **kwargs)


@pytest.mark.parametrize(("method", "path", "payload"), WRITES)
def test_a_write_without_the_token_is_refused(
    client: TestClient, admin_token: str, method: str, path: str, payload
) -> None:
    response = _send(client, method, path, payload)

    assert response.status_code == 401
    assert ADMIN_TOKEN_HEADER.lower() in response.text.lower()


@pytest.mark.parametrize(("method", "path", "payload"), WRITES)
def test_a_write_with_the_wrong_token_is_refused(
    client: TestClient, admin_token: str, method: str, path: str, payload
) -> None:
    response = _send(
        client, method, path, payload, headers={ADMIN_TOKEN_HEADER: "not-the-token"}
    )

    assert response.status_code == 401


def test_the_right_token_is_let_through(client: TestClient, admin_token: str) -> None:
    response = client.post(
        "/api/v1/catalog/instrument-types",
        json={"name": "Mass spectrometer"},
        headers={ADMIN_TOKEN_HEADER: admin_token},
    )

    assert response.status_code == 201, response.text


def test_a_bearer_token_is_accepted_too(client: TestClient, admin_token: str) -> None:
    """So curl and CI do not need a project-specific header."""
    response = client.post(
        "/api/v1/catalog/analysis-types",
        json={"name": "Sequencing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201, response.text


def test_reading_never_needs_a_token(client: TestClient, admin_token: str) -> None:
    """The catalog is public; only changing it is not."""
    for path in (
        "/api/v1/catalog/institutions",
        "/api/v1/catalog/instrument-types",
        "/api/v1/map/institutions",
        "/api/v1/health",
    ):
        assert client.get(path).status_code == 200, path


def test_writes_are_open_when_no_token_is_configured(client: TestClient) -> None:
    """Local development stays frictionless. Production cannot reach this state:
    `Settings` refuses to load without a token there."""
    response = client.post(
        "/api/v1/catalog/microorganisms", json={"scientific_name": "E. coli"}
    )

    assert response.status_code == 201, response.text


def test_token_comparison_rejects_a_prefix() -> None:
    """A guess that is a prefix of the real token must not count as a match."""
    assert token_is_valid("secret", "secret")
    assert not token_is_valid("secr", "secret")
    assert not token_is_valid("secret-and-more", "secret")
    assert not token_is_valid(None, "secret")
    assert not token_is_valid("secret", "")


def test_security_headers_are_on_every_reply(client: TestClient) -> None:
    headers = client.get("/api/v1/catalog/institutions").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "server" not in headers


def test_security_headers_are_on_a_refusal_too(
    client: TestClient, admin_token: str
) -> None:
    """A 401 is still a response a browser will act on."""
    headers = client.post(
        "/api/v1/catalog/microorganisms", json={"scientific_name": "x"}
    ).headers

    assert headers["X-Content-Type-Options"] == "nosniff"


def test_hsts_is_sent_only_where_it_belongs(client: TestClient, monkeypatch) -> None:
    from app.core.config import settings

    assert "Strict-Transport-Security" not in client.get("/api/v1/health").headers

    monkeypatch.setattr(settings, "hsts_enabled", True)
    headers = client.get("/api/v1/health").headers

    assert headers["Strict-Transport-Security"].startswith("max-age=31536000")


def test_an_oversized_body_is_refused_before_it_is_read(
    client: TestClient, monkeypatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_body_bytes", 100)

    response = client.post(
        "/api/v1/catalog/instrument-types", json={"name": "x" * 500}
    )

    assert response.status_code == 413


class TestProductionConfiguration:
    """The checks that stop an unsafe deployment from starting at all."""

    SAFE = {
        "app_env": "production",
        "admin_token": "a" * 48,
        "cors_origins": ["https://sciconnect.rs"],
        "allowed_hosts": ["sciconnect.rs", "api.sciconnect.rs"],
        "database_url": "postgresql+psycopg://u:p@db:5432/sciconnect",
    }

    def test_a_safe_production_configuration_loads(self) -> None:
        config = Settings(**self.SAFE)

        assert config.is_production
        assert config.writes_require_a_token
        # Docs and HSTS follow the environment without being named.
        assert not config.serve_docs
        assert config.send_hsts

    @pytest.mark.parametrize(
        ("field", "value", "expected_message"),
        [
            ("admin_token", "", "APP_ADMIN_TOKEN is not set"),
            ("admin_token", "short", "shorter than 32"),
            ("cors_origins", ["*"], "APP_CORS_ORIGINS"),
            ("cors_origins", [], "APP_CORS_ORIGINS"),
            ("cors_origins", ["http://sciconnect.rs"], "plain-HTTP"),
            ("allowed_hosts", ["*"], "APP_ALLOWED_HOSTS"),
            ("database_url", "sqlite+pysqlite:///./app.db", "SQLite"),
        ],
    )
    def test_an_unsafe_production_configuration_is_refused(
        self, field: str, value, expected_message: str
    ) -> None:
        with pytest.raises(ValueError, match=expected_message):
            Settings(**{**self.SAFE, field: value})

    def test_the_same_values_are_fine_in_development(self) -> None:
        """None of this is a hole on a laptop, and refusing it there would only
        make the checks something people switch off."""
        config = Settings(
            app_env="development",
            admin_token="",
            cors_origins=["http://localhost:5173"],
            allowed_hosts=["*"],
            database_url="sqlite+pysqlite:///:memory:",
        )

        assert not config.is_production
        assert config.serve_docs
        assert not config.send_hsts

    def test_a_loopback_origin_is_allowed_over_plain_http(self) -> None:
        """An SSH tunnel to the server is a legitimate production origin."""
        config = Settings(**{**self.SAFE, "cors_origins": ["http://localhost:5173"]})

        assert "http://localhost:5173" in config.cors_origins


class TestCheckingAnAdminKey:
    """What the sign-in screen asks before it shows the admin workspace."""

    PATH = "/api/v1/auth/check"

    def test_the_right_key_is_confirmed(self, client: TestClient, admin_token: str) -> None:
        response = client.post(self.PATH, headers={ADMIN_TOKEN_HEADER: admin_token})

        assert response.status_code == 200
        assert response.json() == {"role": "admin", "key_required": True}

    @pytest.mark.parametrize("headers", [{}, {ADMIN_TOKEN_HEADER: "wrong"}])
    def test_a_missing_or_wrong_key_is_refused(
        self, client: TestClient, admin_token: str, headers: dict[str, str]
    ) -> None:
        assert client.post(self.PATH, headers=headers).status_code == 401

    def test_guessing_is_limited_more_tightly_than_writing(
        self, client: TestClient, admin_token: str, limited
    ) -> None:
        """Every attempt is a guess at the secret, right or wrong."""
        limited(rate_limit_auth="3/minute", rate_limit_write="100/minute")

        codes = [
            client.post(self.PATH, headers={ADMIN_TOKEN_HEADER: f"guess-{n}"}).status_code
            for n in range(3)
        ]
        # Out of guesses: even the right key has to wait, or the limit could be
        # probed for which attempts were close.
        blocked = client.post(self.PATH, headers={ADMIN_TOKEN_HEADER: admin_token})

        assert codes == [401, 401, 401]
        assert blocked.status_code == 429

    def test_the_guess_budget_is_separate_from_the_write_budget(
        self, client: TestClient, admin_token: str, limited
    ) -> None:
        limited(rate_limit_auth="1/minute", rate_limit_write="100/minute")
        client.post(self.PATH, headers={ADMIN_TOKEN_HEADER: "wrong"})

        response = client.post(
            "/api/v1/catalog/instrument-types",
            json={"name": "Still writable"},
            headers={ADMIN_TOKEN_HEADER: admin_token},
        )

        assert response.status_code == 201

    def test_a_server_without_a_key_says_so(self, client: TestClient) -> None:
        """Development: the page can tell the visitor no key is needed."""
        response = client.post(self.PATH)

        assert response.json() == {"role": "admin", "key_required": False}
