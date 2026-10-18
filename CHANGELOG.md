# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.2] - 2026-10-17

### Added

- Stage 1 reads the RVTools `vSnapshot` and `vCD` sheets and flags VMs with snapshots (`snapshot`) or mounted media (`connected_media`), which make migrations fail. Automatic for `.xlsx`; `--snapshots` and `--cd` for CSV exports.
- Field note 02: running HCX over a long program.
- ADR 0003 (size service meshes from data volume), ADR 0004 (design the destination for growth) and ADR 0005 (agree a temporary RPO for the migration period).
- Twelve new traps from the field.

### Changed

- Inventory schema 1.1: two new flags and a record of which extra sheets were read and how many rows matched.
- Stage 5 is now "readiness and wave planning"; readiness checks are on the v0.3 roadmap.
- Known limitations now state that the pipeline assumes VLAN-backed networks.

### Removed

- A stray scratch file, `.gitignore.additions`.

## [0.1.1] - 2026-10-17

### Added

- Field notes: how to get a trustworthy inventory with RVTools or PowerCLI, and what to avoid.
- `scripts/export-inventory.ps1`: PowerCLI export in a format stage 1 already understands, with a sample and a test.
- Known limitations section in the README.

### Changed

- Sample data now uses neutral, made-up application names.
- README background rewritten as the story behind the project.

## [0.1.0] - 2026-10-17

### Added

- Project documentation: README with pipeline diagram, architecture and stage contracts, decision framework, build-vs-buy map and field traps.
- ADR 0001 (schema-driven stages) and ADR 0002 (rules infer four of the 7Rs).
- Stage 1, inventory: RVTools CSV/XLSX parser with version-aware column mapping, unit normalization, edge-case flags and schema validation.
- Stage 2, classify: ordered 7R rules engine with owner tags, environment inference, confidence and review flags.
- Synthetic sample data covering current and legacy RVTools formats.
- CI on Python 3.10 to 3.13: lint, unit and schema tests, and an end-to-end run.
- Dependabot updates for GitHub Actions and Python dependencies.
