# AI Agent Guidelines for GameBus Campaign Assistant

This repository contains a **Streamlit-based campaign inspection tool** for GameBus campaign exports. The current paper-release branch is intentionally narrower than the earlier MVP: it focuses on deterministic export-based checks, a simplified review UI, one assistant chat, optional local LLM support, guardrailed explanations, and a downloadable campaign-flow diagram.

These guidelines describe the current architecture. Do not reintroduce removed metadata, sidecar, workspace-readiness, patch-generation, or capability-gating workflows unless they are explicitly re-scoped in a future release.

## Big Picture Architecture

### Current Responsibilities

The codebase is organized around four responsibilities:

1. **UI Layer** (`src/campaign_assistant/ui/` and `src/campaign_assistant/app.py`)
   - Streamlit frontend code.
   - Provides the main pages: Overview, Findings, and Assistant.
   - Manages session state, uploaded/downloaded campaign files, prepared assistant questions, and UI navigation.
   - Does not implement checker logic or LLM policy logic directly.

2. **Checker and Result Normalization** (`src/campaign_assistant/checker/`)
   - Wraps the legacy GameBus campaign checker.
   - Runs selected deterministic export-based checks.
   - Normalizes raw checker output into a stable result dictionary.
   - Builds a `campaign_snapshot` used by the Overview, Assistant context, and flow diagram.

3. **Assistant Support Layer** (`src/campaign_assistant/agents/` and `src/campaign_assistant/llm/`)
   - Provides one user-facing Assistant chat.
   - Routes questions automatically between Campaign Support and Theory Support.
   - Uses optional LLM support through Ollama or a mock client.
   - Falls back to deterministic responses when LLM support is disabled or unavailable.
   - Uses fact-sheet and response-guard logic to prevent high-risk hallucinations.

4. **Diagram Generation** (`src/campaign_assistant/diagram/`)
   - Generates a dependency-free SVG campaign-flow diagram.
   - Uses campaign snapshot data: levels/challenges, visualizations, tasks, target points, and formal success/failure transitions.
   - Does not require Graphviz or any external system executable.

## Current Campaign Analysis Flow

```text
User uploads/selects a GameBus campaign export
    ↓
app.py triggers CampaignAnalysisCoordinator.analyze_campaign()
    ↓
checker.run_campaign_checks() runs selected deterministic checks
    ↓
checker.result_normalizer.normalize_analysis_result()
    ├─ normalizes summary/finding structures
    ├─ builds prioritized findings
    └─ builds campaign_snapshot
    ↓
result stored in Streamlit session state
    ↓
Rendered in UI pages:
    ├─ Overview: status, structure, priorities, optional flow diagram
    ├─ Findings: detailed checker findings and prepared assistant questions
    └─ Assistant: one guardrailed chat for findings, structure, improvements, and theory support
```

## Current Assistant Flow

```text
User asks a question in Assistant
    ↓
AssistantCoordinator.answer()
    ↓
IntentRouter.route()
    ├─ Campaign Support Agent for checker/finding/inspection questions
    └─ Theory Support Agent for BCT, COM-B, TTM, burden, adherence, engagement, and outcome questions
    ↓
build_llm_context() creates compact assistant context
build_fact_sheet() creates authoritative checker/export facts
    ↓
Selected support agent generates answer
    ↓
validate_agent_response() checks for unsafe contradictions or overclaims
    ↓
Final answer shown in the single Assistant chat
```

## Important Current Design Rules

### 1. Checker output is authoritative

The deterministic checker result is the source of truth for export-level issues. Assistant responses must not contradict:

- `total_issues`
- `failed_checks`
- `errored_checks`
- `issue_count_by_check`
- known prioritized findings

If the selected checks found zero issues, the Assistant must not say that the checker found problems, warnings, errors, or inconsistencies.

### 2. Export structure is descriptive, not evaluative

Counts such as numbers of waves, visualizations, levels/challenges, tasks, or transitions are descriptive facts. They are not automatically problems.

For example, the Assistant may say:

```text
The export contains 80 tasks.
```

It should not say:

```text
The campaign has a task-count issue.
```

unless this is supported by a deterministic checker finding.

### 3. Theory support is advisory

Theory-oriented answers must be framed as advisory reflection, not formal validation.

The Assistant must not infer formal TTM, COM-B, or BCT implementation from levels, waves, visualizations, or task counts alone. It may suggest possible theory-oriented review questions or design improvements.

### 4. No outcome claims from export alone

The Assistant must not claim that a campaign will cause weight loss, improve health outcomes, or be effective. Such claims require intervention-content review and empirical evaluation.

For outcome questions, use cautious language such as:

```text
The campaign export and checker output cannot determine whether the campaign will cause weight loss or other health outcomes.
```

### 5. LLM support is optional

The app must work when LLM support is unavailable. Ollama may improve answer quality, but the app should degrade gracefully to deterministic fallback responses.

## Key Current Modules

| Path | Purpose |
|------|---------|
| `src/campaign_assistant/app.py` | Main Streamlit entry point and page routing |
| `src/campaign_assistant/checker/wrapper.py` | Wrapper around the legacy GameBus checker |
| `src/campaign_assistant/checker/result_normalizer.py` | Normalizes checker output and builds paper-release result structures |
| `src/campaign_assistant/checker/campaign_snapshot.py` | Extracts campaign structure for Overview, Assistant, and diagram generation |
| `src/campaign_assistant/checker/schema.py` | Current check identifiers and default check set |
| `src/campaign_assistant/orchestration/coordinator.py` | Runs the current analysis pipeline |
| `src/campaign_assistant/ui/overview.py` | Overview page, status, priorities, campaign structure, flow diagram panel |
| `src/campaign_assistant/ui/findings.py` | Findings page and finding-specific assistant prompts |
| `src/campaign_assistant/ui/assistant_chat.py` | Single Assistant chat UI |
| `src/campaign_assistant/ui/check_picker.py` | Sidebar check selection UI |
| `src/campaign_assistant/agents/assistant_coordinator.py` | Coordinates assistant routing, answering, and response guarding |
| `src/campaign_assistant/agents/intent_router.py` | Routes user questions to the correct support agent |
| `src/campaign_assistant/agents/campaign_support_agent.py` | Explains checker findings and inspection steps |
| `src/campaign_assistant/agents/theory_support_agent.py` | Provides advisory behavior-change theory support |
| `src/campaign_assistant/agents/context_builder.py` | Builds compact LLM context from normalized results |
| `src/campaign_assistant/agents/fact_sheet.py` | Builds authoritative checker/export facts for response validation |
| `src/campaign_assistant/agents/response_guard.py` | Blocks high-risk hallucinations and unsupported claims |
| `src/campaign_assistant/agents/question_types.py` | Classifies outcome, BCT, TTM, COM-B, and design-quality questions |
| `src/campaign_assistant/llm/` | Ollama, mock, and LLM client factory code |
| `src/campaign_assistant/diagram/flow_diagram.py` | Dependency-free SVG campaign-flow diagram generator |
| `tests/` | Current paper-release test suite |

## Current Deterministic Checks

The current default checks are:

```python
SECRETS
SPELLCHECKER
REACHABILITY
CONSISTENCY
VISUALIZATIONINTERN
TARGETPOINTSREACHABLE
```

Use constants from `campaign_assistant.checker.schema` rather than hard-coded strings where possible.

Do not reintroduce old removed checks such as unreliable native/TTM structure checks unless they are redesigned and explicitly re-scoped.

## Removed / Out-of-Scope Workflows

The following were part of earlier prototypes or planning but are intentionally out of scope for the current paper-release branch:

- metadata sidecars;
- task-role metadata;
- workspace readiness;
- workspace bundles;
- capability-gated validators;
- old privacy/workspace diagnostics UI;
- patch generation;
- patched Excel drafts;
- metadata-dependent fix proposal generation;
- old multi-agent analysis pipeline with `PrivacyGuardian`, `CapabilityResolver`, `StructuralChangeAgent`, `TheoryGroundingAgent`, and `ContentFixerAgent`;
- old setup/workspace pages;
- formal theory-validation checks based on unreliable assumptions.

Do not add compatibility shims for these removed modules just to satisfy obsolete tests. The test suite should match the current paper-release scope.

## Running the App on Windows

```powershell
.venv\Scripts\activate
streamlit run src/campaign_assistant/app.py
```

The app opens in the browser at:

```text
http://localhost:8501
```

If a helper script exists, end users may also use:

```powershell
scripts\run_app.bat
```

## Optional Ollama Setup

The default local model is intended to be lightweight:

```powershell
ollama pull gemma3:1b
```

Then run the app normally:

```powershell
streamlit run src/campaign_assistant/app.py
```

Useful environment variables:

```powershell
$env:CAMPAIGN_ASSISTANT_LLM_ENABLED="false"
$env:CAMPAIGN_ASSISTANT_LLM_PROVIDER="ollama"
$env:CAMPAIGN_ASSISTANT_LLM_MODEL="gemma3:1b"
$env:CAMPAIGN_ASSISTANT_SHOW_ROUTING="false"
```

For tests, the mock LLM provider can be used:

```powershell
$env:CAMPAIGN_ASSISTANT_LLM_PROVIDER="mock"
$env:CAMPAIGN_ASSISTANT_MOCK_LLM_RESPONSE="Mock response."
```

## Running Tests

```powershell
pytest
```

The current tests are intentionally aligned with the paper-release scope. They cover imports, assistant routing, response guards, diagram generation, and key integration behavior.

Old tests from the previous MVP architecture should not be active in this branch.

## Legacy Checker Integration

The legacy checker remains isolated in:

```text
src/campaign_assistant/legacy/gamebus_campaign_checker.py
```

Use the wrapper instead of importing the legacy checker directly:

```python
from campaign_assistant.checker import run_campaign_checks

result = run_campaign_checks(
    file_path=file_path,
    checks=selected_checks,
    export_excel=False,
)
```

## Streamlit Session State Conventions

Streamlit reruns the script on widget interactions. Preserve important data in `st.session_state`, especially:

- current analysis result;
- selected page;
- assistant chat messages;
- prepared assistant question from Findings;
- generated flow diagram SVG.

Use stable keys for buttons, checkboxes, and generated diagram state. Avoid storing raw large temporary objects unless needed.

## Flow Diagram Conventions

The flow diagram is generated as SVG and should remain dependency-free.

Do not use Graphviz, because it requires a separate system executable and creates installation burden for campaign organizers.

Diagram semantics:

- boxes represent levels/challenges;
- tracks usually correspond to visualizations;
- disconnected progressions inside one visualization are shown as subtracks;
- task count and target points are shown in box subtitles when available;
- orange horizontal arrows represent direct success/standard transitions to the next displayed level;
- colored curves represent other transitions;
- dashed curves represent failure transitions.

The diagram is an inspection aid. It does not replace the campaign export.

## Common Pitfalls to Avoid

1. Reintroducing removed metadata/workspace/sidecar functionality into the paper-release branch.
2. Treating export structure counts as checker issues.
3. Letting the LLM contradict deterministic checker output.
4. Letting theory support claim formal TTM/COM-B/BCT alignment without explicit evidence.
5. Claiming weight-loss or health-effectiveness outcomes from export structure alone.
6. Using Graphviz or another system-level dependency for the diagram.
7. Rendering SVG with `st.image()`; use HTML/component rendering or download instead.
8. Adding old compatibility shims just to satisfy obsolete tests.
9. Importing the legacy checker directly instead of using the wrapper.
10. Hiding important assistant guardrail behavior inside UI-only code; keep policy logic centralized in `response_guard.py` and `fact_sheet.py`.

## Testing Strategy

Use `pytest` with focused tests for the current release scope:

- import smoke tests;
- intent routing tests;
- fact-sheet tests;
- response-guard tests;
- assistant integration guard tests;
- flow diagram tests;
- selected checker/normalizer tests if needed.

Avoid restoring the large obsolete test suite from the old MVP architecture unless those features are intentionally restored.

## Future Extension: Approved Design Context

A possible future Phase 7 may add optional uploaded campaign-design documents. If implemented, it should extend the fact-sheet system rather than bypass it.

Recommended future pattern:

```text
uploaded design documents
    ↓
text extraction / summary generation
    ↓
organizer review and approval
    ↓
approved design fact sheet
    ↓
assistant grounding context
```

Raw documents should not be passed directly into routine assistant prompts. Approved design facts should remain separate from checker facts and export facts.
