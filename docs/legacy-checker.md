# Legacy checker

GameBus Campaign Assistant wraps a GameBus campaign checker available at https://github.com/SergeAutexier/GameBusChecker rather than reimplementing all checking logic from scratch.

This document explains what the legacy checker is, why it is still used, and how it fits into the current project.

## What is the legacy checker?

The legacy checker is a Python implementation of campaign validation logic.

In this project, it is kept in:

```text
src/campaign_assistant/legacy/gamebus_campaign_checker.py
````

It contains the original logic for checking exported GameBus campaign Excel files.

## Why keep it?

The current app is meant to improve usability and release quality quickly, without rewriting validated checking logic.

Keeping the legacy checker has several advantages:

* preserves existing campaign validation behavior
* reduces risk of regressions
* allows the project to focus on:

  * better structure
  * a friendlier interface
  * clearer outputs
  * testing
  * future assistant features

## What does the new app add?

The modern wrapper around the legacy checker adds:

* a normalized result format
* issue prioritization
* optional Excel export from normalized issues
* chat-oriented explanations
* TTM explanations
* local web interface through Streamlit
* local settings and convenience features

## Current architecture

The current flow is:

1. a campaign Excel file is uploaded or downloaded
2. the wrapper loads the legacy checker
3. selected checks are executed
4. raw issues are converted into normalized `Issue` objects
5. issues are grouped, prioritized, and summarized
6. the UI displays them in a chat-style interface

## Where the wrapper lives

The main wrapper is implemented in:

```text
src/campaign_assistant/checker/wrapper.py
```

Supporting modules:

```text
src/campaign_assistant/checker/schema.py
src/campaign_assistant/checker/prioritization.py
src/campaign_assistant/checker/explainers.py
```

## Why the legacy checker is isolated

The legacy checker is intentionally kept in its own place to make the boundary clear:

* `legacy/` = earlier checking logic
* `checker/` = modern wrapper and normalized backend API
* `ui/` = Streamlit-facing presentation logic

This separation makes it easier to:

* test the wrapper without rewriting everything
* gradually replace pieces later if needed
* understand which behavior comes from old logic and which behavior is new

## Runtime patches

The wrapper currently applies a few compatibility/runtime patches to the legacy checker instead of modifying the legacy file directly.

This is done to:

* avoid changing the original checker logic unnecessarily
* keep the wrapper responsible for compatibility adjustments
* make later refactoring easier

These patches are defined in:

```text
src/campaign_assistant/checker/wrapper.py
```

## What should not depend directly on the legacy checker

New code should generally **not** import from `legacy/` directly.

Instead, new code should use:

```python
from campaign_assistant.checker import run_campaign_checks
```

or other public exports from the `campaign_assistant.checker` package.

This keeps the rest of the codebase independent from legacy implementation details.

## Future direction

The legacy checker may later be:

* partially replaced piece by piece,
* kept as long-term source-of-truth for some checks,
* or fully retired if the checking logic is reimplemented and validated.

For now, the project intentionally uses a **wrap-and-improve** strategy rather than a full rewrite.

## Summary

In short:

* the legacy checker remains the source of truth for current checking behavior
* the new project adds structure, packaging, tests, and a user-friendly interface
* the wrapper isolates old logic from the new application architecture
