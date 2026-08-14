# Changelog

All notable changes to this test schema are documented in this file.

## [0.0.1] - 2026-08-14

### Added

- Added an Ethereum Beacon OpenAPI test fixture for disabled-operation behavior.
- Marked `GET /eth/v1/beacon/genesis` as disabled with `x-disabled: true`.
- Added explicit `false` and `null` variants to `GET /eth/v1/node/health` and `GET /eth/v1/config/spec`.
- Left all other operations without `x-disabled` to verify the default enabled behavior.
