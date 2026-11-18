# Changelog

All notable changes to this schema are documented in this file.

The format is based on [Keep a ChangeLog](https://keepachangelog.com/) and follows [Semantic Versioning](https://semver.org/)

## [0.0.5] - 2026-11-18

### Added

- Added missing Lotus v1.39.1 gateway methods: `Filecoin.ChainGetFinalizedTipSet`, `Filecoin.EthBaseFee`, `Filecoin.EthGetBlockReceipts`, `Filecoin.EthGetTransactionByBlockHashAndIndex`, `Filecoin.EthGetTransactionByBlockNumberAndIndex`, `Filecoin.EthTraceFilter`, `Filecoin.F3GetCertificate`, `Filecoin.F3GetLatestCertificate`, `Filecoin.F3GetPowerTableByInstance`, `Filecoin.StateGetNetworkParams`, `Filecoin.StateGetRandomnessDigestFromBeacon`.
- Added the corresponding Ethereum RPC aliases.

### Changed

- Reduced all method costs above 200 credits to 200 credits.

## [0.0.4] - 2026-09-28

### Added

- Added a stable root-level `x-api-id` UUID to identify this API independently of configuration names for per-key method permissions.

## [0.0.3] - 2026-08-20

### Added

- Added eth_getBlockReceipts and Filecoin.ChainNotify.

## [0.0.2] - 2026-05-15

### Changed

- Added versioned v1 spec release asset.

## [0.0.1] - 2026-02-13

### Added

- Initial version of the spec
