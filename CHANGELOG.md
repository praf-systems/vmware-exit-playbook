# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-17

### Added

- Project documentation: README with pipeline diagram, architecture and stage contracts, decision framework, build-vs-buy map and field traps.
- ADR 0001 (schema-driven stages) and ADR 0002 (rules infer four of the 7Rs).
- Stage 1, inventory: RVTools CSV/XLSX parser with version-aware column mapping, unit normalization, edge-case flags and schema validation.
- Stage 2, classify: ordered 7R rules engine with owner tags, environment inference, confidence and review flags.
- Synthetic sample data covering current and legacy RVTools formats.
- CI on Python 3.10 to 3.13: lint, unit and schema tests, and an end-to-end run.
- Dependabot updates for GitHub Actions and Python dependencies.
