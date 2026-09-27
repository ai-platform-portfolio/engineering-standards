import base64
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_governance import api, audit, canonical_timestamp, capture_baseline, pages, repository_policy, ruleset


class GovernanceTest(unittest.TestCase):
    def setUp(self):
        self.contract = {
            "organization": "example", "code_owner": "owner", "checks_app_id": 15368,
            "defaults": {"checks": ["quality"]},
            "repositories": {"platform": {"checks": ["quality", "plan-required"]}},
        }
        self.live = ruleset(self.contract["repositories"]["platform"], 15368)
        self.live.update(id=7, updated_at="2026-09-26T22:00:00.000Z")
        self.baseline = {"verified_by": "owner", "rulesets": {"platform": {
            "ruleset_id": 7, "updated_at": canonical_timestamp(self.live["updated_at"]), "bypass_actors": [],
        }}}
        self.responses = {
            "user": {"login": "owner"},
            "orgs/example/repos?type=all&per_page=100&page=1": [{"name": "platform"}],
            "repos/example/platform": {"visibility": "public", "default_branch": "main", "archived": False},
            "repos/example/platform/rulesets?per_page=100&page=1": [{"name": "main", "id": 7}],
            "repos/example/platform/rulesets/7": self.live,
            "repos/example/platform/rules/branches/main": [
                {"type": item["type"], "ruleset_id": 7} for item in self.live["rules"]
            ],
            "repos/example/platform/contents/.github/CODEOWNERS?ref=main": {
                "content": base64.b64encode(b"* @owner\n").decode(),
            },
        }
    def run_audit(self):
        return audit(self.contract, lambda path: copy.deepcopy(self.responses[path]), self.baseline)[0]

    def test_live_controls_match_policy(self):
        self.assertEqual(self.run_audit()["status"], "pass")

    def test_read_only_response_uses_only_the_exact_owner_verified_version(self):
        del self.live["bypass_actors"]
        self.assertEqual(self.run_audit()["status"], "pass")
        self.live["updated_at"] = "2026-09-26T22:00:01.000Z"
        self.assertEqual(self.run_audit()["status"], "fail")

    def test_owner_and_ci_timezone_representations_match_without_losing_precision(self):
        self.live["updated_at"] = "2026-09-26T23:00:00.000+01:00"
        del self.live["bypass_actors"]
        self.assertEqual(self.run_audit()["status"], "pass")
        self.live["updated_at"] = "2026-09-26T22:00:00.001Z"
        self.assertEqual(self.run_audit()["status"], "fail")
        with self.assertRaisesRegex(ValueError, "timezone"):
            canonical_timestamp("2026-09-26T22:00:00")

    def test_missing_untrusted_or_recreated_baseline_fails(self):
        for change in (lambda b: b.update(verified_by="another-user"),
                       lambda b: b.update(rulesets={}),
                       lambda b: b["rulesets"]["platform"].update(ruleset_id=8)):
            baseline = copy.deepcopy(self.baseline)
            change(baseline)
            report, _ = audit(self.contract, self.responses.__getitem__, baseline)
            self.assertEqual(report["status"], "fail")

    def test_owner_can_capture_only_complete_correct_rulesets(self):
        self.assertEqual(capture_baseline(self.contract, self.responses.__getitem__), self.baseline)
        del self.live["bypass_actors"]
        with self.assertRaisesRegex(ValueError, "unverified"):
            capture_baseline(self.contract, self.responses.__getitem__)

    def test_capture_rejects_bypass_actors_and_other_accounts(self):
        self.live["bypass_actors"] = [{"actor_type": "OrganizationAdmin", "bypass_mode": "always"}]
        with self.assertRaisesRegex(ValueError, "unverified"):
            capture_baseline(self.contract, self.responses.__getitem__)
        self.responses["user"] = {"login": "another-user"}
        with self.assertRaisesRegex(ValueError, "configured owner"):
            capture_baseline(self.contract, self.responses.__getitem__)

    def test_disabled_untargeted_bypassed_or_weakened_rules_fail(self):
        changes = [
            lambda r: r.update(enforcement="disabled"),
            lambda r: r["conditions"]["ref_name"].update(include=[]),
            lambda r: r["conditions"]["ref_name"].update(exclude=["refs/heads/main"]),
            lambda r: r.update(bypass_actors=[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]),
            lambda r: r["rules"].pop(0),
            lambda r: r["rules"][2]["parameters"].update(required_approving_review_count=0),
            lambda r: r["rules"][2]["parameters"].update(dismiss_stale_reviews_on_push=True),
            lambda r: r["rules"][2]["parameters"].update(require_code_owner_review=False),
            lambda r: r["rules"][3]["parameters"].update(strict_required_status_checks_policy=False),
            lambda r: r["rules"][3]["parameters"]["required_status_checks"].pop(),
            lambda r: r["rules"][3]["parameters"]["required_status_checks"].append({"context": "unexpected", "integration_id": 15368}),
            lambda r: r["rules"][3]["parameters"]["required_status_checks"][0].update(integration_id=None),
        ]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                changed = copy.deepcopy(self.live)
                change(changed)
                self.responses["repos/example/platform/rulesets/7"] = changed
                self.assertEqual(self.run_audit()["status"], "fail")

    def test_rules_must_be_effective_on_main(self):
        self.responses["repos/example/platform/rules/branches/main"] = []
        self.assertIn("not effective", " ".join(self.run_audit()["findings"]))

    def test_missing_or_duplicate_main_rulesets_fail(self):
        for listing in ([], [{"name": "main", "id": 7}, {"name": "main", "id": 8}]):
            self.responses["repos/example/platform/rulesets?per_page=100&page=1"] = listing
            self.assertEqual(self.run_audit()["status"], "fail")

    def test_repository_visibility_default_branch_and_archive_drift_fail(self):
        for field, value in (("visibility", "private"), ("default_branch", "develop"), ("archived", True)):
            with self.subTest(field=field):
                original = copy.deepcopy(self.responses["repos/example/platform"])
                self.responses["repos/example/platform"][field] = value
                self.assertEqual(self.run_audit()["status"], "fail")
                self.responses["repos/example/platform"] = original

    def add_repository(self):
        self.responses["orgs/example/repos?type=all&per_page=100&page=1"].append({"name": "new-project"})
        for path, value in list(self.responses.items()):
            if path.startswith("repos/example/platform"):
                self.responses[path.replace("/platform", "/new-project")] = copy.deepcopy(value)
        live = ruleset(self.contract["defaults"], 15368)
        live.update(id=7, updated_at=self.live["updated_at"])
        self.responses["repos/example/new-project/rulesets/7"] = live

    def test_new_repository_uses_defaults_and_appears_in_report_without_inventory_edit(self):
        self.add_repository()
        baseline = capture_baseline(self.contract, self.responses.__getitem__)
        report, table = audit(self.contract, self.responses.__getitem__, baseline)
        self.assertEqual(report["status"], "pass")
        self.assertEqual([row["repository"] for row in report["repositories"]], ["new-project", "platform"])
        self.assertEqual(report["repositories"][0]["checks"], ["quality"])
        self.assertEqual(report["repositories"][1]["checks"], ["quality", "plan-required"])
        self.assertIn("`new-project`", table)
        self.assertNotIn("new-project", self.contract["repositories"])

    def test_new_repository_fails_for_missing_controls_and_baseline(self):
        self.add_repository()
        report = self.run_audit()
        self.assertEqual(report["status"], "fail")
        self.assertIn("new-project: ruleset version lacks", " ".join(report["findings"]))
        self.responses["repos/example/new-project/rulesets?per_page=100&page=1"] = []
        report = self.run_audit()
        self.assertEqual(report["findings"], ["new-project: expected exactly one main ruleset"])
        del self.responses["repos/example/new-project/contents/.github/CODEOWNERS?ref=main"]
        report = self.run_audit()
        self.assertEqual(len(report["findings"]), 2)
        self.assertIn("cannot verify CODEOWNERS", report["findings"][1])
        self.assertEqual(report["repositories"][0]["visibility"], "public")

    def test_configured_repository_cannot_disappear_from_audit(self):
        self.responses["orgs/example/repos?type=all&per_page=100&page=1"] = []
        del self.responses["repos/example/platform"]
        report = self.run_audit()
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["repositories"][0]["repository"], "platform")

    def test_owner_coverage_cannot_be_narrowed(self):
        self.responses["repos/example/platform/contents/.github/CODEOWNERS?ref=main"]["content"] = (
            base64.b64encode(b"*.py @owner\n").decode()
        )
        self.assertEqual(self.run_audit()["status"], "fail")

    def test_api_failure_is_not_compliance(self):
        def unavailable(path):
            if path.endswith("/rulesets/7"):
                raise RuntimeError("GitHub read failed: ruleset")
            return self.responses[path]
        report, _ = audit(self.contract, unavailable)
        self.assertEqual(report["status"], "fail")
        self.assertIn("GitHub read failed", " ".join(report["findings"]))

    def test_http_failure_does_not_print_authentication_details(self):
        with patch("audit_governance.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = "secret authentication data"
            with self.assertRaisesRegex(RuntimeError, "verify access") as error:
                api("repos/example/platform")
            self.assertNotIn("secret", str(error.exception))

    def test_pagination_includes_every_repository(self):
        calls = []
        def fetch(path):
            calls.append(path)
            return [{"name": str(i)} for i in range(100)] if path.endswith("&page=1") else [{"name": "last"}]
        self.assertEqual(len(pages("orgs/example/repos?type=all", fetch)), 101)
        self.assertEqual(len(calls), 2)

    def test_checked_in_default_and_terraform_override(self):
        root = Path(__file__).resolve().parents[1]
        contract = json.loads((root / "governance/repositories.json").read_text())
        self.assertEqual(repository_policy(contract, "new-project"), {"checks": ["quality"]})
        self.assertIn("infrastructure-plan-required", repository_policy(contract, "terraform-modules")["checks"])


if __name__ == "__main__":
    unittest.main()
