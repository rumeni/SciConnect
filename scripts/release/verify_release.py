#!/usr/bin/env python3
"""Refuse deploys that are not an exact successful main-branch CI commit.

Requires only Python stdlib, git, and the workflow's read-only GITHUB_TOKEN.
Checking the commit before checkout/build prevents approving a guessed tag or
an untested PR head. We deliberately require a successful *push* CI run.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request


def valid_sha(sha: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", sha))


def verified_run(runs: list[dict], sha: str) -> bool:
    return any(
        r.get("head_sha") == sha
        and r.get("head_branch") == "main"
        and r.get("event") == "push"
        and r.get("status") == "completed"
        and r.get("conclusion") == "success"
        for r in runs
    )


def check_ancestry(sha: str) -> None:
    subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"], check=True,
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "origin/main"], check=True,
    )



def check_release_contract(sha: str) -> None:
    """Refuse old application images that would auto-migrate on restart.

    A green CI SHA from before the release migration guard is NOT safe to
    deploy with this workflow, because its image ignores APP_RUN_MIGRATIONS.
    """
    entrypoint = subprocess.run(
        ["git", "show", f"{sha}:backend/docker-entrypoint.sh"],
        check=True, text=True, capture_output=True,
    ).stdout
    overlay = subprocess.run(
        ["git", "show", f"{sha}:compose.release.yaml"],
        check=True, text=True, capture_output=True,
    ).stdout
    if "APP_RUN_MIGRATIONS:-true" not in entrypoint:
        raise ValueError("Selected API image predates explicit migration gating")
    if 'APP_RUN_MIGRATIONS: "false"' not in overlay:
        raise ValueError("Selected release overlay does not disable startup migrations")


def get_ci_runs(repo: str, sha: str, token: str) -> list[dict]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository name")
    query = urllib.parse.urlencode({"head_sha": sha, "event": "push", "per_page": 100})
    url = f"https://api.github.com/repos/{repo}/actions/workflows/ci.yml/runs?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SciConnect-safe-release",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    return data["workflow_runs"]


def main() -> int:
    sha = sys.argv[1] if len(sys.argv) == 2 else ""
    if not valid_sha(sha):
        print("ERROR: release SHA must be 40 lowercase hexadecimal characters", file=sys.stderr)
        return 1
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        print("ERROR: dispatch the release workflow only from main", file=sys.stderr)
        return 1
    if not os.environ.get("GH_TOKEN") or not os.environ.get("GITHUB_REPOSITORY"):
        print("ERROR: GitHub read-only token/repository not available", file=sys.stderr)
        return 1
    try:
        check_ancestry(sha)
        check_release_contract(sha)
        runs = get_ci_runs(os.environ["GITHUB_REPOSITORY"], sha, os.environ["GH_TOKEN"])
        if not verified_run(runs, sha):
            raise ValueError("No completed successful main push CI run for this exact SHA")
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: release verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Verified main commit with successful CI: {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
