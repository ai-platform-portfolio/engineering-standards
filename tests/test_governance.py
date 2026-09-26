import base64
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_governance import api, audit, documentation_findings, pages, render, ruleset


class GovernanceTest(unittest.TestCase):
    def setUp(self):
        self.contract = {
            "organization": "example", "code_owner": "owner", "checks_app_id": 15368,
            "repositories": {"platform": {"checks": ["quality", "plan-required"]}},
        }
        self.live = ruleset(self.contract["repositories"]["platform"], 15368)
        self.responses = {
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
        self.readme = render([{"repository": "platform", "visibility": "public", "branch": "main",
                               "checks": ["quality", "plan-required"], "findings": []}])

    def run_audit(self):
        return audit(self.contract, self.readme, lambda path: copy.deepcopy(self.responses[path]))[0]

    def test_live_controls_match_documentation(self):
        self.assertEqual(self.run_audit()["status"], "pass")

    def test_disabled_untargeted_bypassed_or_weakened_rules_fail(self):
        changes = [
            lambda r: r.update(enforcement="disabled"),
            lambda r: r["conditions"]["ref_name"].update(include=[]),
            lambda r: r["conditions"]["ref_name"].update(exclude=["refs/heads/main"]),
            lambda r: r.update(bypass_actors=[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]),
            lambda r: r["rules"].pop(0),
            lambda r: r["rules"][2]["parameters"].update(required_approving_review_count=0),
            lambda r: r["rules"][2]["parameters"].update(dismiss_stale_reviews_on_push=False),
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

    def test_inventory_additions_and_missing_repositories_fail(self):
        for listing in ([], [{"name": "platform"}, {"name": "new-project"}]):
            self.responses["orgs/example/repos?type=all&per_page=100&page=1"] = listing
            self.assertIn("inventory changed", " ".join(self.run_audit()["findings"]))

    def test_owner_coverage_cannot_be_narrowed(self):
        self.responses["repos/example/platform/contents/.github/CODEOWNERS?ref=main"]["content"] = (
            base64.b64encode(b"*.py @owner\n").decode()
        )
        self.assertEqual(self.run_audit()["status"], "fail")

    def test_stale_readme_and_duplicate_markers_fail(self):
        for text in (self.readme.replace("public", "private"), self.readme + self.readme, "No table"):
            with self.subTest(text=text):
                self.assertTrue(documentation_findings(text, self.readme))

    def test_api_failure_is_not_compliance(self):
        def unavailable(path):
            if path.endswith("/rulesets/7"):
                raise RuntimeError("GitHub read failed: ruleset")
            return self.responses[path]
        report, _ = audit(self.contract, self.readme, unavailable)
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

    def test_checked_in_contract_and_readme_agree(self):
        root = Path(__file__).resolve().parents[1]
        contract = json.loads((root / "governance/repositories.json").read_text())
        rows = [{"repository": name, "visibility": "public", "branch": "main",
                 "checks": spec["checks"], "findings": []} for name, spec in contract["repositories"].items()]
        self.assertEqual(documentation_findings((root / "README.md").read_text(), render(rows)), [])


if __name__ == "__main__":
    unittest.main()
