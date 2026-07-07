# Security Policy

This repository is a public demo and reference implementation for governed execution and receipt verification.

Do not submit secrets, private keys, production credentials, tokens, customer data, tunnel configuration, or undisclosed vulnerability material through public issues or pull requests.

## Supported scope

**In scope:**

- Public demo code
- Receipt and verifier behavior
- Documentation boundary errors
- Examples that could mislead users into unsafe operation

**Out of scope:**

- Attempts to access private WitnessOps infrastructure
- Production deployment assumptions
- Secret ingestion through public GitHub
- Claims that the demo is a production authority surface

## Reporting

For security-sensitive reports, use the maintainer's private contact path rather than public issues.

Do not open public issues containing credentials, private keys, customer data, or live infrastructure details.

## Boundary

This repository is **not**:

- A production secret-ingest path
- A public signer service
- A remote shell service
- A production promotion authority

Executor receipts prove governed execution was recorded. They do not prove correctness, merge safety, deployment authorization, or absence of defects. See [docs/architecture.md](docs/architecture.md) and [docs/operators.md](docs/operators.md).