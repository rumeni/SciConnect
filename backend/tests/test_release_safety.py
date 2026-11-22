"""Offline safeguards for the operator-only production release workflow.

These tests run in the existing backend CI, before the new workflow is merged
onto main and can be triggered manually.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "release"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


@pytest.mark.parametrize(
    "name",
    ["remote_deploy.sh", "remote_rollback.sh", "restore_drill.sh"],
)
def test_release_scripts_are_valid_bash(name: str) -> None:
    subprocess.run(["bash", "-n", str(SCRIPTS / name)], check=True)


def test_existing_entrypoint_remains_valid_posix_shell() -> None:
    subprocess.run(["sh", "-n", str(ROOT / "backend/docker-entrypoint.sh")], check=True)


def test_verification_gate_has_offline_regression_tests() -> None:
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(SCRIPTS / "tests")],
        cwd=ROOT,
        check=True,
    )


def test_workflow_requires_manual_dispatch_approval_and_opt_in() -> None:
    workflow = WORKFLOW.read_text()
    assert re.search(r"(?m)^on:\s*\n\s+workflow_dispatch:", workflow)
    assert not re.search(r"(?m)^\s+(push|pull_request|schedule):", workflow)
    assert "SCICONNECT_CD_ENABLED" in workflow
    assert "environment: production" in workflow
    assert "python3 scripts/release/verify_release.py" in workflow
    assert "needs.verify.outputs.sha" in workflow
    assert "dry_run" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "sha256:" in workflow
    # Production-only credentials must not be handed to the verification job.
    verify, deploy = workflow.split("\n  deploy:", 1)
    assert "DEPLOY_SSH_PRIVATE_KEY" not in verify
    assert "GHCR_READ_TOKEN" not in verify
    assert "DEPLOY_SSH_PRIVATE_KEY" in deploy


def test_release_overlay_never_migrates_on_regular_api_restart() -> None:
    config = (ROOT / "compose.release.yaml").read_text()
    assert 'APP_RUN_MIGRATIONS: "false"' in config
    assert "SCICONNECT_API_IMAGE" in config
    assert "SCICONNECT_FRONTEND_IMAGE" in config
    entrypoint = (ROOT / "backend/docker-entrypoint.sh").read_text()
    assert "APP_RUN_MIGRATIONS:-true" in entrypoint



def test_release_never_auto_pulls_mutable_database_or_proxy_tags() -> None:
    for name in ("remote_deploy.sh", "remote_rollback.sh"):
        script = (SCRIPTS / name).read_text()
        assert '"${compose[@]}" pull api frontend' in script
        assert '"${compose[@]}" up -d --no-build --pull never' in script
        assert "--pull always" not in script



def test_prod_compose_override_is_valid_when_docker_is_installed() -> None:
    if not shutil.which("docker"):
        pytest.skip("Docker is not installed in this test environment")
    check = subprocess.run(
        ["docker", "compose", "version"], capture_output=True, text=True,
    )
    if check.returncode != 0:
        pytest.skip("Docker Compose plugin not installed")
    environment = {
        **os.environ,
        "SITE_DOMAIN": "example.org",
        "POSTGRES_DB": "ci_db",
        "POSTGRES_USER": "ci_user",
        "POSTGRES_PASSWORD": "test-password",
        "APP_ADMIN_TOKEN": "x" * 48,
        "SCICONNECT_API_IMAGE": "ghcr.io/example/api@sha256:" + "a" * 64,
        "SCICONNECT_FRONTEND_IMAGE": "ghcr.io/example/frontend@sha256:" + "b" * 64,
    }
    result = subprocess.run(
        [
            "docker", "compose", "-f", "compose.prod.yaml", "-f",
            "compose.release.yaml", "config", "--quiet",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
