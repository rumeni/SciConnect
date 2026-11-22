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
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "release"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


@pytest.mark.parametrize(
    "name",
    ["remote_deploy.sh", "remote_rollback.sh", "restore_drill.sh", "remote_session.sh"],
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
    assert "bash -s --" not in workflow
    assert "RELEASE_OK $SHA" in workflow
    assert "selected-release" in workflow
    assert "timeout-minutes: 120" in workflow
    assert "SECONDS + 85 * 60" in workflow
    assert "remote_session.sh" in workflow
    assert "ServerAliveInterval=30" in workflow
    session = (SCRIPTS / "remote_session.sh").read_text()
    assert "nohup setsid" in session
    assert "check_logind_policy" in session
    assert "elif report_finished" in session
    assert 'ln -s "$HOME/.docker/cli-plugins"' in session
    assert "bash -s --" not in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
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
    assert "build: !reset null" in config
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




def test_backup_reads_complete_archive_and_smoke_checks_deployed_images() -> None:
    deploy = (SCRIPTS / "remote_deploy.sh").read_text()
    rollback = (SCRIPTS / "remote_rollback.sh").read_text()
    assert "exec -T db pg_restore -f /dev/null" in deploy
    assert "pg_restore --list" not in deploy.split("exec -T db pg_restore -f /dev/null")[1]
    assert "body[\"migration\"]==sys.argv[1]" in deploy
    assert "docker inspect --format '{{.Config.Image}}'" in deploy
    assert "docker inspect --format '{{.Config.Image}}'" in rollback
    assert 'docker image inspect "$api_image"' in rollback
    # A repeated SHA with different rebuild digests must preserve the
    # immediately preceding known-good image pair.
    assert '"$current_sha" != "$sha"' in deploy
    assert '"$current_api_image" != "$api_image"' in deploy
    assert '"$current_frontend_image" != "$frontend_image"' in deploy



@pytest.mark.parametrize("exit_code", [0, 9])
def test_detached_release_survives_launcher_exit_and_cleans_credentials(
    tmp_path: pathlib.Path, exit_code: int
) -> None:
    """Run the real launcher/worker in isolation; emulate only docker login.

    The launcher exits before the delayed release completes. A remote SSH
    disconnect cannot swallow the remaining script or forge a successful job.
    """
    sha = "a" * 40
    attempt = f"1234-{exit_code + 1}"
    release = tmp_path / "SciConnect" / "releases" / sha
    scripts = release / "scripts" / "release"
    scripts.mkdir(parents=True)
    session = SCRIPTS / "remote_session.sh"
    (scripts / session.name).write_text(session.read_text())
    (release / "compose.release.yaml").write_text("services: {}\n")
    (scripts / "remote_deploy.sh").write_text(
        "#!/bin/bash\nsleep 0.4\n"
        + (f"echo 'RELEASE_OK {sha}'\n" if exit_code == 0 else "")
        + f"exit {exit_code}\n"
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = compose ] && [ \"$2\" = version ]; then exit 0; fi\n"
        "test \"$1\" = login || exit 42\n"
        "test -n \"$DOCKER_CONFIG\" || exit 43\n"
        "cat > \"$DOCKER_CONFIG/config.json\"\n"
    )
    fake_docker.chmod(0o755)
    fake_logind = fake_bin / "systemd-analyze"
    fake_logind.write_text(
        "#!/bin/sh\n"
        "test \"$1\" = cat-config || exit 40\n"
        "printf 'KillUserProcesses=no\\n'\n"
    )
    fake_logind.chmod(0o755)
    env = {
        **os.environ, "HOME": str(tmp_path),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }
    api = "ghcr.io/example/api@sha256:" + "a" * 64
    frontend = "ghcr.io/example/frontend@sha256:" + "b" * 64
    started = subprocess.run(
        ["bash", str(session), "start", sha, attempt, api, frontend, "operator"],
        input="temporary-read-only-token",
        capture_output=True, text=True, env=env, timeout=10,
    )
    assert started.returncode == 0, started.stderr
    assert started.stdout.strip() == f"RELEASE_STARTED {sha} {attempt}"

    status = ""
    for _ in range(60):
        checked = subprocess.run(
            ["bash", str(session), "status", sha, attempt],
            capture_output=True, text=True, env=env, timeout=10,
        )
        assert checked.returncode == 0, checked.stderr
        status = checked.stdout.strip()
        if status != f"RELEASE_RUNNING {sha} {attempt}":
            break
        time.sleep(0.1)

    expected = "RELEASE_OK" if exit_code == 0 else "RELEASE_FAILED"
    assert status == f"{expected} {sha} {attempt}"
    attempt_folder = tmp_path / "SciConnect" / "release-state" / "deploy-attempts" / attempt
    assert (attempt_folder / "exit-code").read_text().strip() == str(exit_code)
    assert not (attempt_folder / "docker-auth").exists()
    assert not (tmp_path / ".docker" / "config.json").exists()


def test_status_rechecks_exit_code_if_worker_finishes_during_pid_probe(
    tmp_path: pathlib.Path,
) -> None:
    """Reproduce the old TOCTOU race deterministically, without timing guesses."""
    sha = "a" * 40
    attempt = "321-4"
    folder = tmp_path / "SciConnect" / "release-state" / "deploy-attempts" / attempt
    folder.mkdir(parents=True)
    (folder / "worker.pid").write_text("99999999\\n")
    bash_env = tmp_path / "bash_env.sh"
    bash_env.write_text(
        "kill() {\\n"
        '  printf "0\\\\n" > "$SC_TEST_FOLDER/exit-code"\\n'
        f'  printf "RELEASE_OK {sha}\\\\n" > "$SC_TEST_FOLDER/release.log"\\n'
        "  return 1\\n"
        "}\\n"
    )
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "BASH_ENV": str(bash_env),
        "SC_TEST_FOLDER": str(folder),
    }
    result = subprocess.run(
        ["bash", str(SCRIPTS / "remote_session.sh"), "status", sha, attempt],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"RELEASE_OK {sha} {attempt}"


def test_logind_killuserprocesses_yes_refuses_release_before_creating_auth(
    tmp_path: pathlib.Path,
) -> None:
    sha = "a" * 40
    attempt = "453-2"
    release = tmp_path / "SciConnect" / "releases" / sha
    scripts = release / "scripts" / "release"
    scripts.mkdir(parents=True)
    (scripts / "remote_deploy.sh").write_text("#!/bin/bash\\nexit 0\\n")
    (release / "compose.release.yaml").write_text("services: {}\\n")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    check = fake_bin / "systemd-analyze"
    check.write_text("#!/bin/sh\\nprintf 'KillUserProcesses=yes\\\\n'\\n")
    check.chmod(0o755)
    env = {
        **os.environ, "HOME": str(tmp_path),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }
    api = "ghcr.io/example/api@sha256:" + "a" * 64
    frontend = "ghcr.io/example/frontend@sha256:" + "b" * 64
    result = subprocess.run(
        ["bash", str(SCRIPTS / "remote_session.sh"),
         "start", sha, attempt, api, frontend, "operator"],
        input="dummy", capture_output=True, text=True, env=env, timeout=10,
    )
    assert result.returncode != 0
    assert "KillUserProcesses=yes" in result.stderr
    assert not (tmp_path / "SciConnect" / "release-state").exists()


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
