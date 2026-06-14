# User Guide

This guide explains how to use **GameBus Campaign Assistant** to inspect a GameBus campaign Excel export.

## What this app is for

GameBus Campaign Assistant helps campaign organizers review a campaign configuration exported from GameBus.

It can help you:

* upload or download a campaign Excel export;
* run export-based campaign checks;
* see which checks passed or failed;
* inspect detected findings;
* ask one assistant chat about findings, campaign structure, possible improvements, or behavior-change theory;
* generate a simple campaign flow diagram;
* optionally download generated outputs such as reports or diagrams when available.

The app supports campaign review. It does **not** edit campaigns directly in GameBus.

---

## What you need before starting

You need either:

* a GameBus campaign Excel export (`.xlsx`), or
* valid GameBus credentials if the download option is available in your version.

The safest workflow is:

1. export the campaign from GameBus manually;
2. save the `.xlsx` file on your computer;
3. upload it in the app.

---

## Starting the app

### If you received the Windows scripts

1. Open the project folder.
2. Double-click `scripts/run_app.bat`.
3. Wait for the browser to open.

### If you start it manually

Open a terminal in the project folder and run:

```powershell
streamlit run src/campaign_assistant/app.py
```

The app should open in your browser at `http://localhost:8501`.

---

## Checking a campaign

### Option 1 — Upload a campaign Excel file

This is the easiest and most reliable method.

1. Open the app.
2. In the sidebar, choose **Upload Excel file**.
3. Select your campaign `.xlsx` file.
4. Choose the checks you want to run.
5. Click **Analyze campaign**.

### Option 2 — Download from GameBus

If this feature is available in your version:

1. Open the app.
2. In the sidebar, choose **Download from GameBus**.
3. Enter your credentials and campaign abbreviation.
4. Click **Analyze campaign**.

If downloading does not work, export the campaign manually and use file upload instead.

---

## Understanding the pages

After analysis, the app has three main pages:

### Overview

The Overview page shows:

* campaign structure summary;
* number of detected issues;
* failed and passed checks;
* high-priority findings;
* optional campaign flow diagram.

The flow diagram can be created from the exported campaign structure. It shows levels/challenges, transitions, and progression paths as an SVG diagram.

### Findings

The Findings page shows detected issues in more detail.

Use this page to inspect:

* which check produced the finding;
* how severe the finding is;
* where in the campaign it appears;
* what should be reviewed.

Some findings have an **Ask Assistant about this** button. This prepares a question for the Assistant page.

### Assistant

The Assistant page contains one chat window.

You can ask questions such as:

```text
What should I inspect first?
Which checks failed?
Explain this finding.
Is this campaign too complicated?
What BCTs could be considered?
Does this campaign follow TTM?
Will this help people lose weight?
```

The Assistant automatically routes questions to the relevant support mode. You do not need to choose an agent manually.

---

## Checks

The current default checks are:

* `secrets`
* `reachability`
* `consistency`
* `visualizationintern`
* `targetpointsreachable`

The check picker also includes optional checks:

* `spellchecker` — German-only spellchecking, disabled by default because it can be slow on some machines;
* `ttm` — HW8-specific progression review, disabled by default because it is not a universal theory-validation check.

The checker output is the source of truth for detected export-level issues.

If the selected checks find zero issues, this means only that no issues were detected by those checks. It does **not** prove that the campaign is optimal, theory-aligned, or effective.

---

## Behavior-change theory questions

The Assistant can provide advisory theory-oriented support.

For example, it can discuss:

* possible BCTs to consider;
* COM-B-related design questions;
* TTM-related design questions;
* participant burden;
* adherence and engagement considerations.

However, the app does **not** formally validate theory alignment from the export alone.

For example:

* progression through levels does not automatically prove TTM alignment;
* points or rewards do not automatically prove BCT implementation;
* task counts do not automatically prove that a campaign is too complex;
* a campaign export cannot prove weight-loss or health outcomes.

Effectiveness requires intervention-content review and empirical evaluation.

---

## LLM support

The Assistant can use a local Ollama model if configured.

If Ollama is unavailable, the app still works. In that case, the Assistant uses deterministic fallback responses.

If you see a message saying that Ollama is unavailable, check that Ollama is running and that the selected model has been pulled, for example:

```powershell
ollama serve
ollama pull gemma3:1b
```

---

## Campaign flow diagram

The Overview page can generate a simple SVG diagram from the campaign export.

The diagram shows:

* levels/challenges as boxes;
* tracks based on visualizations;
* success/standard transitions;
* failure transitions;
* task counts and target points when available.

You can:

* create the diagram;
* download it as SVG;
* open it in a new browser tab.

The diagram is intended as a readable overview, not as a complete replacement for checking the Excel export.

---

## Common problems

### The app does not start

Check that:

* Python is installed;
* dependencies are installed;
* you started the correct script or command.

### Upload does nothing

Check that the file is:

* a GameBus campaign export;
* an `.xlsx` file;
* not open in another program.

### Download from GameBus fails

Possible causes:

* wrong credentials;
* expired session;
* network or server problem;
* incorrect campaign abbreviation.

If this happens, export the campaign manually and upload the file.

### The Assistant gives only basic answers

LLM support may be disabled or unavailable. The app still works, but answers will be more limited.

### I do not understand a finding

Try asking:

```text
Explain this finding.
What should I inspect first?
Which checks failed?
What does this issue mean?
```

---

## Current limitations

This version does not:

* edit campaigns directly in GameBus;
* upload corrected files back into GameBus;
* compare two campaign files;
* generate new campaign content;
* formally validate behavior-change theory alignment.

It is mainly a user-friendly interface for export-based campaign inspection, explanation support, advisory theory reflection, and campaign-flow visualization.

---

## Need more help?

Also check:

* `README.md`
* `CHANGELOG.md`
* `AGENTS.md`
