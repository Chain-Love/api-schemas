#!/usr/bin/env python3
"""Validate repository-specific API contracts using only the Python stdlib."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid


FORMATS = {"json-rpc": "openrpc", "rest-api": "openapi"}
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
SPEC_PATH = re.compile(r"^[^/]+/(json-rpc|rest-api)/(openrpc|openapi)-v[1-9][0-9]*\.json$")


@dataclass(frozen=True)
class Issue:
    path: str
    message: str


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON property {key!r}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"{value} is not a JSON number")


def parse_document(raw):
    document = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(document, dict):
        raise ValueError("specification must be a JSON object")
    return document


def valid_id(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        return False
    return parsed.int != 0 and str(parsed) == value


def validate_operation(operation, label, error):
    cost = operation.get("x-cu-cost")
    if "x-cu-cost" not in operation:
        error(f"{label}: required field x-cu-cost is missing")
    elif type(cost) is not int or cost < 0:
        error(f"{label}: x-cu-cost must be a non-negative integer")

    disabled = operation.get("x-disabled")
    if disabled is not None and type(disabled) is not bool:
        error(f"{label}: x-disabled must be true, false or null when provided")

    # These optional extensions are metadata, not method-policy identities.
    # Do not infer alias targets or authorization schemes from their values.
    if "x-alias-of" in operation:
        alias = operation["x-alias-of"]
        if not isinstance(alias, str) or not alias.strip():
            error(f"{label}: x-alias-of must be a non-empty string")
    if "x-auth" in operation:
        auth = operation["x-auth"]
        if not isinstance(auth, list) or any(not isinstance(v, str) or not v.strip() for v in auth):
            error(f"{label}: x-auth must be an array of non-empty strings")


def validate_methods(document, kind, error):
    format_key = FORMATS[kind]
    if not isinstance(document.get(format_key), str) or not document[format_key]:
        error(f"required field {format_key} must be a version string")
    if not isinstance(document.get("info"), dict):
        error("required field info must be an object")

    if kind == "json-rpc":
        methods = document.get("methods")
        if not isinstance(methods, list):
            error("required field methods must be an array")
            return
        seen = set()
        for index, method in enumerate(methods):
            if not isinstance(method, dict):
                error(f"methods[{index}] must be an object")
                continue
            name = method.get("name")
            if not isinstance(name, str) or not name.strip():
                error(f"methods[{index}].name must be a non-empty string")
                continue
            if name in seen:
                error(f"duplicate RPC method {name!r} in the same version")
            seen.add(name)
            validate_operation(method, name, error)
    else:
        paths = document.get("paths")
        if not isinstance(paths, dict):
            error("required field paths must be an object")
            return
        for path, item in paths.items():
            if not isinstance(item, dict):
                error(f"paths[{path!r}] must be an object")
                continue
            for verb, operation in item.items():
                if verb not in HTTP_METHODS:
                    continue
                label = f"{verb.upper()} {path}"
                if not isinstance(operation, dict):
                    error(f"{label}: operation must be an object")
                    continue
                validate_operation(operation, label, error)


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "git command failed")
    return result.stdout


def check_history(root, base_ref, api_ids, errors):
    # Resolve to a commit first so a caller-supplied ref is never treated as an option.
    base = git(root, "rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}").strip()
    paths = git(root, "ls-tree", "-r", "--name-only", "-z", base).split("\0")
    previous = defaultdict(set)
    for path in paths:
        if not SPEC_PATH.fullmatch(path):
            continue
        document = parse_document(git(root, "show", f"{base}:{path}"))
        identity = document.get("x-api-id")
        # The initial rollout adds IDs to older specifications without this field.
        if "x-api-id" not in document:
            continue
        if not valid_id(identity):
            errors.append(Issue(path, "base revision contains an invalid x-api-id"))
            continue
        previous[str(Path(path).parent)].add(identity)

    current_ids = set().union(*api_ids.values()) if api_ids else set()
    for api, old_ids in previous.items():
        if api in api_ids:
            if api_ids[api] != old_ids:
                errors.append(Issue(api, "existing x-api-id must not be changed or removed"))
        elif not old_ids.issubset(current_ids):
            errors.append(Issue(api, "existing API identity was removed; preserve its x-api-id when moving an API"))


def validate(root, base_ref=None):
    errors = []
    api_ids = defaultdict(set)
    owners = {}
    count = 0
    directories = sorted(p for kind in FORMATS for p in root.glob(f"*/{kind}") if p.is_dir())
    if not directories:
        errors.append(Issue(".", "no API directories found"))

    for directory in directories:
        api = directory.relative_to(root).as_posix()
        kind = directory.name
        api_ids[api]  # Keep an entry even when all IDs are invalid or missing.
        pattern = re.compile(rf"{FORMATS[kind]}-v([1-9][0-9]*)\.json")
        versions = []
        for path in sorted(directory.glob("*.json")):
            relative = path.relative_to(root).as_posix()
            error = lambda message, file=relative: errors.append(Issue(file, message))
            match = pattern.fullmatch(path.name)
            if not match:
                error(f"expected filename {FORMATS[kind]}-vN.json with a positive version number")
                continue
            versions.append(int(match.group(1)))
            count += 1
            try:
                document = parse_document(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                error(str(exc))
                continue
            identity = document.get("x-api-id")
            if not valid_id(identity):
                error("x-api-id must be a non-zero UUID in lowercase hyphenated form")
            else:
                api_ids[api].add(identity)
                owner = owners.setdefault(identity, api)
                if owner != api:
                    error(f"x-api-id {identity} is already used by {owner}")
            validate_methods(document, kind, error)

        if not versions:
            errors.append(Issue(api, f"no {FORMATS[kind]}-vN.json specifications found"))
        elif any(actual != expected for expected, actual in enumerate(sorted(versions), 1)):
            errors.append(Issue(api, "method versions must start at v1 and be consecutive without gaps"))
        if len(api_ids[api]) > 1:
            errors.append(Issue(api, "all method versions of one API must have the same x-api-id"))

    if base_ref:
        try:
            check_history(root, base_ref, api_ids, errors)
        except (OSError, ValueError) as exc:
            errors.append(Issue(".", f"cannot validate identity history against {base_ref!r}: {exc}"))
    return count, errors


def escape_annotation(value, property_value=False):
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return value.replace(",", "%2C").replace(":", "%3A") if property_value else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base-ref", help="Git base revision used to check immutable API IDs")
    args = parser.parse_args()
    count, errors = validate(args.root.resolve(), args.base_ref)
    for issue in errors:
        if os.getenv("GITHUB_ACTIONS") == "true":
            print(f"::error file={escape_annotation(issue.path, True)}::{escape_annotation(issue.message)}")
        else:
            print(f"{issue.path}: {issue.message}", file=sys.stderr)
    if errors:
        print(f"Validation failed: {len(errors)} error(s) in {count} specification file(s).", file=sys.stderr)
        return 1
    print(f"Validated {count} specification file(s): API identities, versions and method metadata are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
