# Chain Love API Schemas Repository

This repository contains **versioned, machine-readable API schemas** for blockchain APIs provided by [Chain.Love](https://chain.love) platform. It serves as the single source of truth for:

- Available methods and endpoints
- Backward compatibility guarantees
- Compute Units (CUs) costs per method
- Generated documentation and interactive API playgrounds

## Repository Semantics

- `<network>/json-rpc/` - JSON-RPC API schemas in **OpenRPC** format
- `<network>/rest/` - REST API schemas in **OpenAPI** format
- `VERSION` - current semantic version of the schema
- `CHANGELOG.md` - human-readable change history
- `_shared/` - global conventions and rules shared across all schemas
