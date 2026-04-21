# AI Agent Guidelines for GameBus Campaign Assistant

This is a **Streamlit-based analysis tool** that wraps a legacy GameBus campaign checker and presents results in a chat-style interface. AI agents should understand the layered architecture and specific conventions used here.

## Big Picture Architecture

### Layered Structure: Three Key Responsibilities

The codebase has a distinct **separation of concerns** across three layers:

1. **UI Layer** (`src/campaign_assistant/ui/`)
   - Streamlit frontend code
   - Manages session state, chat interaction, and user workflows
   - Key file: `app.py` orchestrates tab switching (Chat vs Editor)
   - Does NOT contain business logic

2. **Orchestration Layer** (`src/campaign_assistant/orchestration/`)
   - `CampaignAnalysisCoordinator` runs a fixed pipeline of 5 agents sequentially
   - Pipeline: `PrivacyGuardian` → `CapabilityResolver` → `StructuralChangeAgent` → `TheoryGroundingAgent` → `ContentFixerAgent`
   - Creates/reuses `Workspace` objects to persist campaign state across reruns
   - Each agent receives `AgentContext` (immutable request data) and updates `context.shared` (mutable result accumulator)

3. **Core Components** (checker, workspace, agents)
   - `checker/wrapper.py`: Wraps legacy campaign checker; converts raw issues to normalized `Issue` objects
   - `workspace/`: Creates persistent directories per campaign to store metadata, snapshots, profiles
   - `agents/`: Individual agents that run sequentially during orchestration

### The Campaign Analysis Flow

```
User uploads/downloads campaign file
    ↓
app.py → run_analysis() in ui/actions.py
    ↓
CampaignAnalysisCoordinator.analyze_campaign()
    ├→ Agent 1: PrivacyGuardian (validates data access policy)
    ├→ Agent 2: CapabilityResolver (loads metadata, analysis profiles)
    ├→ Agent 3: StructuralChangeAgent (runs legacy checker, normalizes issues)
    ├→ Agent 4: TheoryGroundingAgent (maps issues to TTM/intervention theory)
    ├→ Agent 5: ContentFixerAgent (generates fix proposals)
    ↓
Result stored in: st.session_state.result (dict with keys: issues, summary, theory_grounding, fix_proposals, etc.)
    ↓
Rendered in UI tabs: Chat (chat-based Q&A) or Editor (structured issue panel views)
```

## Critical Developer Workflows

### Running the App (Windows)

Two ways to start:
```powershell
# Option 1: Automated script (recommended for end-users)
scripts/run_app.bat

# Option 2: Manual
.venv\Scripts\activate
streamlit run src/campaign_assistant/app.py
```

The app opens in the browser at `http://localhost:8501`.

### Running Tests

```powershell
pytest                    # Run all tests
pytest -xvs              # Verbose, stop on first failure
pytest tests/agents/     # Run only agent tests
```

Tests live alongside source code (e.g., `tests/agents/` mirrors `src/campaign_assistant/agents/`). Use `conftest.py` for shared fixtures.

### Install Development Mode

```powershell
pip install -e .[dev]  # Installs with dev dependencies (pytest, pytest-mock)
```

## Project-Specific Conventions

### 1. Error Handling in Agents

All agents inherit from `BaseAgent` and return `AgentResponse`:
```python
@dataclass
class AgentResponse:
    agent_name: str
    success: bool
    summary: str
    payload: dict[str, Any]
    warnings: list[str]
```

If an agent fails (`success=False`), the coordinator raises `RuntimeError` and halts the pipeline. **Always set `success=True` only when your agent completed without critical errors.**

### 2. Shared State Pattern

Agents communicate via `context.shared` (a mutable dict), NOT by modifying context directly:
```python
# In an agent:
context.shared["my_result"] = {...}  # ✓ Correct
context.analysis_profile = {}         # ✗ Wrong (context is immutable)
```

The coordinator merges agent results into the final `result` dict:
```python
result["theory_grounding"] = context.shared.get("theory_grounding", {})
result["fix_proposals"] = context.shared.get("fix_proposals", {})
```

### 3. Workspace Persistence

`Workspace` objects are created once per campaign and reused across multiple analyses:
- Located at: `~/.gamebus_campaign_assistant/<workspace_id>/`
- Contains: snapshots, metadata files, analysis profiles, point rules
- Use `get_or_create_workspace_for_campaign()` (never instantiate directly)
- Key property: `workspace.snapshot_id` is a hash of the campaign file; reobtain it for each rerun

### 4. Legacy Checker Integration

The legacy checker is **dynamically loaded** from `src/campaign_assistant/legacy/gamebus_campaign_checker.py`:
```python
# In checker/wrapper.py
spec = importlib.util.spec_from_file_location(...)
legacy_checker = importlib.util.module_from_spec(spec)
CampaignChecker = legacy_checker.CampaignChecker
```

**Do not import it directly.** Use `run_campaign_checks()` instead:
```python
from campaign_assistant.checker import run_campaign_checks
result = run_campaign_checks(file_path, checks=[...], export_excel=False)
```

### 5. Check Types (Enums in `checker/schema.py`)

Seven check types; always use constants, not strings:
```python
CONSISTENCY, VISUALIZATIONINTERN, REACHABILITY, TARGETPOINTSREACHABLE, SECRETS, SPELLCHECKER, TTMSTRUCTURE
```

Each has a **severity level** for prioritization:
- **High**: TTM, TargetPointsReachable, Reachability, Consistency
- **Medium**: VisualizationIntern, Secrets
- **Low**: SpellChecker

### 6. Session Logging (Audit Trail)

Every user action is logged to `logs/session_<id>.jsonl` (line-delimited JSON):
```python
from campaign_assistant.session_logging import SessionLogger
logger = SessionLogger()
logger.log("event_type", {"key": "value"})
```

SessionLogger is injected into the coordinator. When debugging, **always check the log file first** for what the user actually did.

### 7. Streamlit Session State Management

Streamlit reruns the entire script on button clicks/input changes. The app preserves state across reruns:
```python
st.session_state.result      # Campaign analysis result (persists across reruns)
st.session_state.messages    # Chat history
st.session_state.settings    # User email, saved campaigns (from local storage)
st.session_state.app_config  # Global config (from config/app_config.json)
```

**Avoid mutating these directly in the UI;** instead use coordinator/storage functions that properly handle state.

## Key Files to Know

| Path | Purpose |
|------|---------|
| `src/campaign_assistant/app.py` | Main Streamlit entrypoint; tabs, user flow |
| `src/campaign_assistant/orchestration/coordinator.py` | Runs the 5-agent pipeline; orchestrates analysis |
| `src/campaign_assistant/checker/wrapper.py` | Wraps legacy checker; normalizes issues |
| `src/campaign_assistant/agents/base.py` | Base class for all agents |
| `src/campaign_assistant/workspace/` | Workspace directory management & metadata loading |
| `src/campaign_assistant/ui/actions.py` | UI actions (upload, download, run analysis) |
| `src/campaign_assistant/ui/chat.py` | Chat Q&A and panel rendering |
| `src/campaign_assistant/storage.py` | Persistent user settings (keyring, JSON) |
| `pyproject.toml` | Package metadata, dependencies, pytest config |

## External Dependencies & Integrations

- **Streamlit**: Web framework; manages session, page config, widgets
- **Pandas & openpyxl**: Excel file reading/writing
- **requests & keyring**: GameBus API calls + secure credential storage
- **language-tool-python**: Spelling checks in checker
- **Legacy checker**: Historical GameBus checker logic (isolated in `legacy/` folder)

## Common Pitfalls to Avoid

1. **Importing the legacy checker directly** → Use `run_campaign_checks()` wrapper instead
2. **Modifying context fields in agents** → Use `context.shared[key] = value`
3. **Forgetting to set `success=True` on AgentResponse** → Pipeline halts silently
4. **Not handling FileNotFoundError in workspace code** → Workspace files can be deleted between reruns
5. **Modifying st.session_state.settings without persisting** → Changes lost on next run; use `storage.py` functions
6. **Assuming check IDs are user-facing strings** → They're enum-like constants; display via `FRIENDLY_CHECK_NAMES` dict

## Testing Strategy

- Use `pytest` with fixtures from `conftest.py`
- Mock Streamlit components with `@patch("streamlit....")`
- Mock legacy checker in agent tests (it's dynamically loaded)
- Keep test files in mirror structure: `tests/agents/test_*.py` mirrors `src/campaign_assistant/agents/`

