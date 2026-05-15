# Chain Love API Schemas Repository

This repository contains **versioned, machine-readable API schemas** for blockchain APIs provided by [Chain.Love](https://chain.love) platform. It serves as the single source of truth for:

- Available methods and endpoints
- Backward compatibility guarantees
- Compute Units (CUs) costs per method
- Generated documentation and interactive API playgrounds

## Repository Semantics

- `<network>/json-rpc/` - JSON-RPC API schemas in **OpenRPC** format
- `<network>/rest-api/` - REST API schemas in **OpenAPI** format
- `openrpc-vN.json` / `openapi-vN.json` - full method snapshot for application method version `vN`
- `VERSION` - current release version of the schema bundle
- `CHANGELOG.md` - human-readable change history for release versions

Each `openrpc-vN.json` or `openapi-vN.json` file is a full snapshot, not a delta from the previous method version.
