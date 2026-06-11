# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2026-06-11

### Added
- Restored optional **TTM structure** check for HW8 long-term campaign progression logic; disabled by default because it is campaign-specific.
- Added detailed Assistant explanations for deterministic checks.
- Added behavior-change theory support improvements, including framework clarification and **Self-Determination Theory (SDT)** support.
- Added `.env`-based LLM configuration for changing local Ollama models without editing source code.

### Changed
- Disabled **Spellchecker** by default and clarified that it is German-only.
- Shortened check hover hints and moved detailed explanations to the Assistant.
- Improved Overview layout: Next steps now appears after the diagram in a highlighted Streamlit box.
- Added Overview/Assistant explanation for prioritization.
- Renamed **Unspecified** severity to **No severity**.
- Improved visualization-internals findings by showing names beside IDs.
- Improved Assistant quick-button answers for summaries, campaign structure, prioritization, and highest-priority findings.
- Improved prepared finding explanations with clearer “What this means” text and better formatting.
- Cleaned checker execution by running native checker implementations directly from workbook tables.
- Added safer workbook table loading and sheet-name normalization in checker execution.
- Aligned issue priority sorting with the documented severity plus active-wave priority model.

### Fixed
- Fixed incorrect or overly generic Assistant responses for prepared finding questions.
- Fixed cases where check explanations or prioritization explanations were blocked by the response guard.
- Fixed short follow-up questions such as “and consistency?”.
- Fixed weak LLM replies such as “Okay” by falling back to deterministic guidance.
- Fixed COM-B and broad theory-grounding follow-up handling.
- Fixed a reachability-check failure caused by an incompatible terminal-level helper call.
- Fixed optional spellchecker behavior so a missing `language_tool_python` dependency no longer breaks checker execution.
- Aligned `visualizationintern` severity with checker metadata.
- Improved visualization label comparison to reduce false mismatches caused by formatting differences.

### Tests
- Added/updated tests for TTM structure, check defaults, Assistant quick answers, theory support, response guard behavior, and weak LLM response handling.


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
  - `docs/user_guide.md`
  - `docs/installation_windows.md`
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