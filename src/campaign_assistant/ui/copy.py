from __future__ import annotations


WORKFLOW_PAGE_COPY = {
    "Overview": {
        "description": "Review the current campaign analysis status and decide where to go next.",
        "empty": "Choose a campaign source and click **Analyze campaign** to begin.",
        "open_label": "Open Overview",
    },
    "Findings": {
        "description": "Review detected campaign issues, starting with high-priority findings.",
        "empty": "Analyze a campaign to inspect findings.",
        "open_label": "Open Findings",
    },
    "Fixes": {
        "description": "Review suggested next steps for detected findings.",
        "empty": "Analyze a campaign to review suggested next steps.",
        "open_label": "Open Fixes",
    },
    "Assistant": {
        "description": (
            "Ask one chat assistant about the current campaign analysis, findings, "
            "possible fixes, or behavior-change theory support."
        ),
        "empty": "Analyze a campaign to use the assistant.",
        "open_label": "Open Assistant",
    },
}


ASSISTANT_FALLBACK_TEXT = (
    "I can help you with the current campaign analysis. Try one of these prompts:\n\n"
    "- `Summarize the issues`\n"
    "- `What should I fix first?`\n"
    "- `Which checks failed?`\n"
    "- `Explain the highest-priority issue`\n"
    "- `How can I fix target point issues?`\n"
    "- `Does this campaign seem aligned with TTM?`\n"
    "- `How can I make this campaign more COM-B aligned?`\n"
)