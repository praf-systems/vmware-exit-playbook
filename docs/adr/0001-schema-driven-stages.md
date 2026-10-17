# ADR 0001: Schema-driven pipeline stages

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

Migration programs combine data from many tools: inventory exports, firewall rule sets, dependency maps and cost models. Formats differ between tools and between versions of the same tool. Scripts written against one export usually break on the next.

## Decision

Split the playbook into independent stages. Each stage reads and writes a versioned JSON Schema, validates its input before processing and fails with a clear error when validation fails.

## Consequences

- **Positive:** stages can be tested alone, replaced by commercial tools through a mapping, and reused with any dataset that matches the schema.
- **Negative:** every new data source needs a mapping layer, and schema changes need versioning.
- **Mitigation:** keep mappings in `config/`, and version schemas so older runs remain readable.
