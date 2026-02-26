# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added release governance with a single reproducible `make release-check` command.

### Changed
- Established SemVer and release documentation workflow for future versions.
- UI: eliminada cabecera tipo wizard en Solicitudes para ganar altura útil.

### Fixed
- Ajustada la validación preventiva de duplicados para ignorar la propia pendiente en edición y evitar falsos positivos por eco del formulario.
- Corregido el flujo de "Confirmar y generar PDF" para avisar claramente cuando no hay selección y registrar el intento.
- Botonería de pendientes actualizada: "Eliminar selección" pasa a estilo destructivo y el CTA cambia a "Actualizar pendiente" en modo edición.

## [0.1.0] - 2026-02-19

### Added
- Added architecture import rules gate to prevent forbidden cross-layer dependencies.
- Added unit tests for feature controllers and controller refactor coverage.
- Added correlation ID and structured observability events for sync operations.

### Changed
- Refactored the application layer to remove direct SQL dependencies.
- Extracted pure sync core logic from Sheets synchronization flow.
- Increased test coverage in sync normalization, use-case scenarios, and PDF builder.

### Fixed
- Improved error taxonomy by replacing broad exception handling with domain-specific errors.
- Stabilized CI quality gate by explicitly enforcing coverage baseline checks.
