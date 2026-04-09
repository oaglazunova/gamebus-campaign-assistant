# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - Initial public release

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