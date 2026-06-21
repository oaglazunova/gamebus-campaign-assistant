# Changelog

All notable changes to this project will be documented in this file.

## [0.2.4] - 2026-06-14
### Added

- Added a text-vs-points consistency check that flags tasks where participant-facing text mentions a different point value than the exported task points setting.
- Added a duplicate task names check that reports reused task names only when the duplicated tasks have meaningfully different settings.

### Changed

- New campaign-quality checks are enabled by default because they are directly actionable in GameBus Studio and do not duplicate existing Studio validation.


## [0.2.3] - 2026-06-14

### Fixed

* Fixed existing native checkers so they correctly handle comma-separated `visualizations` references, such as `2002, 2007, 2008`.
* Normalized internal ID handling across existing checkers so numeric and string Excel IDs are compared consistently.
* Fixed structural checks that could previously false-pass by evaluating zero matching challenge-visualization links.
* Fixed reachability, consistency, visualization-internal, target-points, secrets, and TTM checks to resolve challenge and visualization references more reliably.
* Fixed TTM successor lookup so both `success_next` and `failure_next` references are normalized before lookup.
* Fixed visualization-internal checking so challenges belonging to multiple visualizations are handled correctly.

### Changed

* Reachability now treats cyclic/support visualizations, such as Tips/Info/Support views in English, Dutch, German, and Portuguese, as non-progression content where terminal levels are not expected.
* Consistency and TTM checks now apply progression-specific rules only to progression visualizations, avoiding false issues for cyclic/support views.
* Target-points reachability now reports a clearer message when reachable points cannot be computed because required challenge or task values are missing or invalid.
* Checker metadata and tests were updated to reflect normalized string IDs and the revised progression/support visualization behavior.


## [0.2.2] - 2026-06-13

### Changed

* Improved Assistant quick actions so campaign-level suggested prompts use deterministic responses instead of relying on the local LLM.
* Renamed the quick action from “Explain the highest-priority finding” to “Explain the highest-priority findings”.
* Updated highest-priority finding explanations to group repeated issue types, so duplicate findings such as repeated secret-copy issues are explained once with an example.
* Improved follow-up handling so quick actions that focus the top finding update the selected finding used by later questions such as “How do I fix this?”.
* Improved mixed priority/fix follow-ups so questions such as “Why should I inspect this first and how do I fix it?” can include both the prioritization rationale and deterministic GameBus Studio guidance.
* Improved theory-support routing so short framework questions such as TTM, COM-B, BCT, and SDT use cautious deterministic responses instead of weak local LLM output.
* Improved TTM follow-up handling when the user provides explicit stage-mapping context, treating it as user-provided design context rather than as evidence from the export.
* Strengthened weak LLM response filtering to reject meta non-answers such as “I’m ready to help” or “please provide more details”.

### Fixed

* Fixed a bug where “How do I fix this?” could refer to an older selected finding instead of the finding shown by the latest Assistant quick action.
* Fixed acknowledgement handling so short replies such as “ok” are answered deterministically instead of being routed to the unknown-answer fallback.
* Fixed Assistant import/formatting regressions caused by mixed tabs and spaces in `app.py`.

### Tests

* Added regression tests for deterministic quick actions, grouped highest-priority finding explanations, selected-finding focus updates, acknowledgement routing, mixed priority/fix questions, and safer theory-agent routing.
* Expanded Assistant interaction tests to cover conversation-history propagation and answer-source metadata.


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