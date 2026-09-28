# Chain Love API Schemas Repository

This repository contains **versioned, machine-readable API schemas** for blockchain APIs provided by [Chain.Love](https://chain.love) platform. It serves as the single source of truth for:

- Available methods and endpoints
- Backward compatibility guarantees
- Compute Units (CUs) costs per method
- Generated documentation and interactive API playgrounds

## Repository Semantics

- `<network>/json-rpc/` - JSON-RPC API schemas in **OpenRPC** format
- `<network>/rest-api/` - REST API schemas in **OpenAPI** format
- `openrpc-vN.json` / `openapi-vN.json` - method pricing layer for application method version `vN`
- `VERSION` - current release version of the schema bundle
- `CHANGELOG.md` - human-readable change history for release versions

Each `openrpc-vN.json` or `openapi-vN.json` file may be either a full snapshot or a partial override layer.
When resolving a method for version `vN`, consumers must search from `vN` down to `v1` and use the first matching method definition.
Omitting a method from a newer file therefore means inheritance, not removal.

## Validation

Run the repository contract checks with Python 3.9+ (no extra packages required):

```sh
python3 scripts/validate_specs.py
python3 scripts/validate_specs.py --base-ref origin/main
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

The validator checks the entire catalog, including unchanged APIs, for:

- A required root-level `x-api-id`: a non-zero, lowercase, hyphenated UUID.
- Different IDs for different APIs; the same ID for every method version of one API.
- Immutable existing IDs when `--base-ref` is supplied. Initial assignment to a
  spec without an ID is allowed; changing an existing ID or dropping it is not.
  Moving an API directory is allowed when its ID is preserved.
- Consecutive `openrpc-vN.json` / `openapi-vN.json` files starting at `v1`.
- Valid JSON without duplicate properties or non-JSON numeric constants, and
  unique RPC method names within each file. Method names remain case-sensitive.
- Required integer `x-cu-cost >= 0` on every explicitly defined RPC method or
  REST operation. Boolean, fractional, string, missing and null costs are errors.
- Optional `x-disabled` values of `true`, `false` or `null`. Omission and `null`
  retain the runtime's enabled-by-default behavior.
- Optional `x-alias-of` as a non-empty string and `x-auth` as an array of non-empty
  strings. Alias target existence and authorization semantics are not inferred.

Partial method layers remain supported. A newer file may omit inherited methods,
and may redefine a method already present in an earlier version. Each explicitly
defined operation still supplies its own price. Release `VERSION`, `info.version`
and method layer `vN` are separate concepts; they need not have matching numbers.

PR checks run the validator and its tests independently of the existing release
metadata checks and Redocly lint. Identity history is compared with the PR base
commit against the checked-out merge result. Changes to CI or documentation alone
do not require an API version bump or cause empty API detection to fail.

The release workflow validates the entire catalog against the preceding main
commit before any release is published. Its release job depends on successful
validation; no validation failures are downgraded to warnings. Existing Redocly
structural and reference checks remain in the PR workflow.

Errors identify the file and method/field and appear as GitHub Actions annotations.
For example, a method without a price reports:

```text
arbitrum/json-rpc/openrpc-v1.json: eth_maxPriorityFeePerGas: required field x-cu-cost is missing
```

That price is currently missing in the repository and must be agreed and added
before validation can pass. The validator does not assign prices automatically.
