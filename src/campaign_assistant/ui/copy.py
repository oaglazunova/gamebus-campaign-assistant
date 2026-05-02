from __future__ import annotations


WORKFLOW_PAGE_COPY = {
    "Overview": {
        "description": "Review the current campaign analysis status and decide where to go next.",
        "empty": "Choose a campaign source and click **Analyze campaign** to begin.",
        "open_label": "Open Overview",
    },
    "Setup": {
        "description": "Edit workspace metadata, annotations, and supporting files, then re-run analysis.",
        "empty": "Analyze a campaign to open workspace setup.",
        "open_label": "Open Setup",
    },
    "Findings": {
        "description": "Start with priorities and detailed issues. Open interpretation only when you need more context.",
        "empty": "Analyze a campaign to inspect findings.",
        "open_label": "Open Findings",
    },
    "Fixes": {
        "description": "Review grouped repair proposals, approve what you want, and generate drafts.",
        "empty": "Analyze a campaign to review fix proposals.",
        "open_label": "Open Fixes",
    },
    "Assistant": {
        "description": "Ask focused questions about the current analysis or use one of the suggested prompts.",
        "empty": "Analyze a campaign to use the assistant.",
        "open_label": "Open Assistant",
    },
}


ASSISTANT_FALLBACK_TEXT = (
    "I can help you with the current workflow. Try one of these prompts:\n\n"
    "- `Summarize the issues`\n"
    "- `What should I fix first?`\n"
    "- `Which checks failed?`\n"
    "- `What setup is missing?`\n"
    "- `Show point/gatekeeping findings`\n"
    "- `Show theory grounding`\n"
    "- `Show fix proposals`\n"
    "- `What did the agents do?`\n"
)