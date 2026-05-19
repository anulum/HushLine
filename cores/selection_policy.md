# Core Selection Policy

To prevent runtime mix-up, each deployment package must declare one explicit active
core:

- `ACTIVE_CORE=core-go`  (reference)
- `ACTIVE_CORE=core-rust`
- `ACTIVE_CORE=core-python`
- `ACTIVE_CORE=core-node`

Rules:

- one and only one `ACTIVE_CORE` value is allowed
- build pipelines must fail if multiple core outputs are emitted
- evidence logs must include the active core value per release
