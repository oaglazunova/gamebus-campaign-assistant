# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2023-03-22

### Added

* Added a simplified three-page workflow: Overview, Findings, and Assistant.
* Added a single Assistant chat for all user communication.
* Added automatic routing between Campaign Support and Theory Support.
* Added optional local LLM support through Ollama.
* Added mock LLM support for testing.
* Added deterministic fallback behavior when LLM support is disabled or unavailable.
* Added fact-sheet based grounding for assistant responses.
* Added response guardrails against hallucinated checker findings and unsupported outcome claims.
* Added advisory behavior-change theory support.
* Added downloadable SVG campaign flow diagram.
* Added release-focused tests.

### Changed

* Simplified the UI to reduce clutter.
* Reworked the Assistant around checker/export facts as the source of truth.
* Reframed theory support as advisory reflection rather than formal validation.
* Changed the flow diagram to use formal success/failure transition information from the campaign export.
* Replaced the old broad test suite with tests aligned to the scope.

### Removed

* Removed legacy TTM/native TTM checks that were not universally applicable.
* Removed obsolete tests targeting removed MVP functionality.


## [0.1.0] - Initial public release (MVP)

### Added
- Local Streamlit-based web interface for checking GameBus campaign Excel exports
- Chat-style presentation of checker results
- Optional Excel export of normalized issues
- TTM explanation support in the assistant
- Windows helper scripts:
  - `scripts/install_windows.bat`
  - `scripts/run_app.bat`
- Beginner-friendly documentation:
  - `README.md`
  - `docs/user-guide.md`
  - `docs/installation-windows.md`
  - `docs/legacy-checker.md`
  - `docs/ttm-checks.md`
- Initial automated tests for:
  - downloader
  - checker wrapper
  - storage
  - explainers
  - prioritization
  - UI chat helpers

### Changed
- Refactored the repository into a `src/` layout
- Split application logic into clearer modules:
  - `checker/`
  - `ui/`
  - `legacy/`
- Isolated the legacy checker behind a normalized wrapper API
- Improved Windows usability for non-technical users

### Notes
- This version is focused on checking exported campaign files
- Direct campaign editing in GameBus is not supported yet
- Content generation, campaign comparison, and simulation are planned for later phases