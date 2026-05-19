# Hushline Go Core

This is the canonical Go reference core boundary.

Planned layout:

- `src/` — command and engine implementation (to be migrated from root `cmd/` and `internal/`).
- `go.mod` — explicit module definition for this core.
- `build.sh` — local build script.

Build command (placeholder):

```bash
cd core-go
go build ./...
```

This folder is currently scaffold-only until migration is approved.
