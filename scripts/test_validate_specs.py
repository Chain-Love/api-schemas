import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validate_specs import escape_annotation, validate


RPC_ID = "a81a7cbc-68e0-44fc-b219-93d4e0b5e870"
REST_ID = "ca572f82-414c-4c47-843b-9d3dd943b7ad"
OTHER_ID = "e0cf62b9-48a6-405b-a367-4b77c5e2238b"


class ValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="api-spec-validation-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.rpc = {
            "openrpc": "1.2.6",
            "x-api-id": RPC_ID,
            "info": {"title": "Execution", "version": "0.0.1"},
            "methods": [{"name": "read", "x-cu-cost": 1}],
        }
        self.rest = {
            "openapi": "3.1.0",
            "x-api-id": REST_ID,
            "info": {"title": "Beacon", "version": "0.0.1"},
            "paths": {"/items/{id}": {"get": {"x-cu-cost": 1}}},
        }

    def write(self, path, document):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document), encoding="utf-8")
        return target

    def issues(self, base=None):
        _, issues = validate(self.root, base)
        return "\n".join(f"{issue.path}: {issue.message}" for issue in issues)

    def assert_valid(self, base=None):
        self.assertEqual(self.issues(base), "")

    def test_full_and_partial_layers_share_one_id(self):
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        updated = copy.deepcopy(self.rpc)
        updated["methods"] = [{"name": "write", "x-cu-cost": 2}]
        self.write("eth/json-rpc/openrpc-v2.json", updated)
        self.write("eth/rest-api/openapi-v1.json", self.rest)
        self.assert_valid()

    def test_price_override_can_repeat_a_method_in_another_version(self):
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        updated = copy.deepcopy(self.rpc)
        updated["methods"][0]["x-cu-cost"] = 2
        self.write("eth/json-rpc/openrpc-v2.json", updated)
        self.assert_valid()

    def test_uuid_format(self):
        for identity in [None, "", 4, "config-name", RPC_ID.upper(), RPC_ID.replace("-", ""),
                         "urn:uuid:" + RPC_ID, "00000000-0000-0000-0000-000000000000"]:
            with self.subTest(identity=identity):
                self.write("eth/json-rpc/openrpc-v1.json", {**self.rpc, "x-api-id": identity})
                self.assertIn("x-api-id must be", self.issues())
        missing = dict(self.rpc)
        del missing["x-api-id"]
        self.write("eth/json-rpc/openrpc-v1.json", missing)
        self.assertIn("x-api-id must be", self.issues())

    def test_id_collision_between_apis(self):
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.write("eth/rest-api/openapi-v1.json", {**self.rest, "x-api-id": RPC_ID})
        self.assertIn("already used by", self.issues())

    def test_id_disagreement_between_versions(self):
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.write("eth/json-rpc/openrpc-v2.json", {**self.rpc, "x-api-id": OTHER_ID})
        self.assertIn("same x-api-id", self.issues())

    def test_missing_and_nonconsecutive_versions(self):
        self.write("eth/json-rpc/openrpc-v2.json", self.rpc)
        self.assertIn("start at v1", self.issues())
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.write("eth/json-rpc/openrpc-v4.json", self.rpc)
        self.assertIn("without gaps", self.issues())

    def test_wrong_names_and_empty_catalog(self):
        self.assertIn("no API directories", self.issues())
        self.write("eth/json-rpc/openrpc-v01.json", self.rpc)
        self.assertIn("expected filename", self.issues())
        self.assertIn("no openrpc-vN.json", self.issues())

    def test_required_price_for_rpc_and_rest(self):
        self.rpc["methods"][0].pop("x-cu-cost")
        self.rest["paths"]["/items/{id}"]["get"].pop("x-cu-cost")
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.write("eth/rest-api/openapi-v1.json", self.rest)
        issues = self.issues()
        self.assertIn("read: required field x-cu-cost", issues)
        self.assertIn("GET /items/{id}: required field x-cu-cost", issues)

    def test_price_requires_a_nonnegative_integer_not_a_boolean(self):
        for cost in [-1, True, False, 1.5, "1", None]:
            with self.subTest(cost=cost):
                self.rpc["methods"][0]["x-cu-cost"] = cost
                self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
                self.assertIn("non-negative integer", self.issues())
        for cost in [0, 1]:
            self.rpc["methods"][0]["x-cu-cost"] = cost
            self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
            self.assert_valid()

    def test_disabled_keeps_runtime_null_and_omission_semantics(self):
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.assert_valid()
        for disabled in [True, False, None]:
            self.rpc["methods"][0]["x-disabled"] = disabled
            self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
            self.assert_valid()
        for disabled in [0, 1, "true", [], {}]:
            self.rpc["methods"][0]["x-disabled"] = disabled
            self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
            self.assertIn("x-disabled must be", self.issues())

    def test_duplicate_json_properties_at_any_depth(self):
        path = self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        raw = path.read_text()
        for original, replacement in [
            ('"x-cu-cost": 1', '"x-cu-cost": 1, "x-cu-cost": 2'),
            ('"openrpc": "1.2.6"', '"openrpc": "1.2.6", "openrpc": "1.2.6"'),
        ]:
            path.write_text(raw.replace(original, replacement))
            self.assertIn("duplicate JSON property", self.issues())

    def test_duplicate_methods_are_rejected_but_names_remain_case_sensitive(self):
        self.rpc["methods"].append(dict(self.rpc["methods"][0]))
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.assertIn("duplicate RPC method", self.issues())
        self.rpc["methods"][1]["name"] = "READ"
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.assert_valid()

    def test_invalid_json_shape_and_nonstandard_numbers(self):
        path = self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        raw = path.read_text()
        for value in ["NaN", "Infinity", "-Infinity"]:
            path.write_text(raw.replace('"x-cu-cost": 1', '"x-cu-cost": ' + value))
            self.assertIn("not a JSON number", self.issues())
        path.write_text("[]")
        self.assertIn("must be a JSON object", self.issues())
        path.write_text("{")
        self.assertTrue(self.issues())

    def test_rest_path_metadata_is_not_an_operation(self):
        self.rest["paths"]["/items/{id}"]["parameters"] = [{"name": "id", "in": "path"}]
        self.write("eth/rest-api/openapi-v1.json", self.rest)
        self.assert_valid()

    def test_optional_extension_types_do_not_infer_alias_or_auth_behavior(self):
        operation = self.rpc["methods"][0]
        operation.update({"x-alias-of": "External.Method", "x-auth": ["api-keyAuth"]})
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.assert_valid()
        operation.update({"x-alias-of": [], "x-auth": "api-keyAuth"})
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.assertIn("x-alias-of must be", self.issues())
        self.assertIn("x-auth must be", self.issues())

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True, stderr=subprocess.PIPE).strip()

    def baseline(self):
        # History is created only in this disposable test repository.
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Validator Test", "-c", "user.email=validator@example.invalid",
                 "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "baseline")
        return self.git("rev-parse", "HEAD")

    def test_first_id_assignment_is_allowed(self):
        original = dict(self.rpc)
        original.pop("x-api-id")
        self.write("eth/json-rpc/openrpc-v1.json", original)
        base = self.baseline()
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.assert_valid(base)

    def test_replacing_id_in_all_versions_is_rejected_against_base(self):
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.write("eth/json-rpc/openrpc-v2.json", self.rpc)
        base = self.baseline()
        for version in [1, 2]:
            self.write(f"eth/json-rpc/openrpc-v{version}.json", {**self.rpc, "x-api-id": OTHER_ID})
        self.assert_valid()  # Cross-file agreement alone cannot catch identity replacement.
        self.assertIn("existing x-api-id must not be changed", self.issues(base))

    def test_rename_preserves_id_but_deleting_api_identity_fails(self):
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.write("eth/rest-api/openapi-v1.json", self.rest)
        base = self.baseline()
        (self.root / "eth").rename(self.root / "renamed")
        self.assert_valid(base)
        (self.root / "renamed/json-rpc/openrpc-v1.json").unlink()
        (self.root / "renamed/json-rpc").rmdir()
        self.assertIn("existing API identity was removed", self.issues(base))

    def test_invalid_base_does_not_silently_skip_history_validation(self):
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        self.baseline()
        self.assertIn("cannot validate identity history", self.issues("nonexistent-ref"))

    def test_cli_reports_failures_as_github_annotations(self):
        self.rpc["methods"][0].pop("x-cu-cost")
        self.write("eth/json-rpc/openrpc-v1.json", self.rpc)
        command = [sys.executable, str(Path(__file__).with_name("validate_specs.py")), "--root", str(self.root)]
        result = subprocess.run(command, capture_output=True, text=True, env={**os.environ, "GITHUB_ACTIONS": "true"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("::error file=eth/json-rpc/openrpc-v1.json::read:", result.stdout)
        self.assertEqual(escape_annotation("line\n%text,field:", True), "line%0A%25text%2Cfield%3A")


if __name__ == "__main__":
    unittest.main()
