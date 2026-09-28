# Changelog

All notable changes to this test schema are documented in this file.

## [0.0.2] - 2026-09-28

### Added

- Added a stable root-level `x-api-id` UUID to identify this API independently of configuration names for per-key method permissions.

## [0.0.1] - 2026-08-14

### Added

- Added an Ethereum OpenRPC test fixture for disabled-method behavior.
- Marked `eth_blockNumber` as disabled with `x-disabled: true`.
- Added explicit `false` and `null` variants to `eth_call` and `eth_chainId`.
- Left all other methods without `x-disabled` to verify the default enabled behavior.
