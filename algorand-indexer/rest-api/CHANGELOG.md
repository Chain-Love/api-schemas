# Changelog

All notable changes to this schema are documented in this file.

The format is based on [Keep a ChangeLog](https://keepachangelog.com/) and follows [Semantic Versioning](https://semver.org/)

## [0.0.5] - 2026-08-11

### Removed

- Removed v2 and v3 specs as they were for testing.

## [0.0.4] - 2026-06-04

### Added

- Added partial v3 method pricing layer for version inheritance testing.
- Added `GET /v2/accounts/{account-id}/pending-transactions` at 3 CU in method version v3.
- Added `GET /v2/applications/{application-id}/state` at 5 CU in method version v3.

### Changed

- Changed `GET /v2/accounts/{account-id}` cost from 4 CU to 8 CU in method version v3.
- Changed `GET /v2/transactions` cost from 1 CU to 6 CU in method version v3.

## [0.0.3] - 2026-06-01

### Changed

- Added partial v2 method pricing layer for version inheritance testing.
- Changed `GET /v2/accounts/{account-id}` cost from 1 CU to 4 CU in method version v2.

## [0.0.2] - 2026-05-15

### Changed

- Added versioned v1 spec release asset.

## [0.0.1] - 2026-02-12

### Added

- Initial version of the spec
