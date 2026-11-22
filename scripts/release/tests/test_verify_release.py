"""Offline, deterministic tests for the GitHub release verification gate."""
import importlib.util
import pathlib
import subprocess
import unittest
from unittest.mock import patch

PATH = pathlib.Path(__file__).resolve().parents[1] / "verify_release.py"
spec = importlib.util.spec_from_file_location("verify_release", PATH)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
SHA = "a" * 40


class VerifyReleaseTests(unittest.TestCase):
    def test_refuses_abbreviated_nonhex_or_uppercase_sha(self):
        for candidate in ["abc", "g" * 40, "A" * 40, SHA + "0", ""]:
            self.assertFalse(release.valid_sha(candidate))
        self.assertTrue(release.valid_sha(SHA))

    def test_requires_successful_push_of_exact_main_sha(self):
        good = dict(
            head_sha=SHA, head_branch="main", event="push",
            status="completed", conclusion="success",
        )
        self.assertTrue(release.verified_run([good], SHA))
        for change in [
            {"head_sha": "b" * 40},
            {"head_branch": "feature"},
            {"event": "pull_request"},
            {"status": "in_progress"},
            {"conclusion": "failure"},
        ]:
            self.assertFalse(release.verified_run([{**good, **change}], SHA))
        self.assertFalse(release.verified_run([], SHA))

    @patch.object(release.subprocess, "run")
    def test_checks_commit_object_and_main_ancestry(self, run):
        release.check_ancestry(SHA)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], [
            "git", "cat-file", "-e", f"{SHA}^{{commit}}",
        ])
        self.assertEqual(run.call_args_list[1].args[0], [
            "git", "merge-base", "--is-ancestor", SHA, "origin/main",
        ])
        self.assertTrue(all(x.kwargs["check"] for x in run.call_args_list))

    @patch.object(release.subprocess, "run")
    def test_selected_image_must_support_external_migration_gate(self, run):
        from subprocess import CompletedProcess

        run.side_effect = [
            CompletedProcess([], 0, 'case "${APP_RUN_MIGRATIONS:-true}" in'),
            CompletedProcess([], 0, 'APP_RUN_MIGRATIONS: "false"'),
        ]
        release.check_release_contract(SHA)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], [
            "git", "show", f"{SHA}:backend/docker-entrypoint.sh",
        ])
        self.assertEqual(run.call_args_list[1].args[0], [
            "git", "show", f"{SHA}:compose.release.yaml",
        ])

    @patch.object(release.subprocess, "run")
    def test_old_ci_green_image_without_migration_gate_is_rejected(self, run):
        from subprocess import CompletedProcess

        run.side_effect = [
            CompletedProcess([], 0, "alembic upgrade head"),
            CompletedProcess([], 0, 'APP_RUN_MIGRATIONS: "false"'),
        ]
        with self.assertRaisesRegex(ValueError, "predates"):
            release.check_release_contract(SHA)

    @patch.object(release.subprocess, "run")
    def test_non_ancestor_is_fatal(self, run):
        run.side_effect = subprocess.CalledProcessError(1, "git")
        with self.assertRaises(subprocess.CalledProcessError):
            release.check_ancestry(SHA)


if __name__ == "__main__":
    unittest.main()
