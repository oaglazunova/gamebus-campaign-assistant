from __future__ import annotations


WORKFLOW_PAGE_COPY = {
    "Overview": {
        "description": "Review the current campaign analysis status and decide where to go next.",
        "empty": "Choose a campaign source and click **Analyze campaign** to begin.",
        "open_label": "Open Overview",
    },
    "Findings": {
        "description": "Review detected campaign findings, starting with high-priority findings.",
        "empty": "Analyze a campaign to inspect findings.",
        "open_label": "Open Findings",
    },
    "Assistant": {
        "description": (
            "Ask one chat assistant about the current campaign analysis, findings, "
            "possible improvements, or behavior-change theory support."
        ),
        "empty": "Analyze a campaign to use the assistant.",
        "open_label": "Open Assistant",
    },
}


ASSISTANT_FALLBACK_TEXT = (
    "I can help you with the current campaign analysis. Try one of these prompts:\n\n"
    "- `Summarize the findings`\n"
    "- `What should I inspect first?`\n"
    "- `Which checks failed?`\n"
    "- `Explain the highest-priority finding`\n"
    "- `How can I fix the point target findings?`\n"
    "- `Does this campaign seem aligned with TTM?`\n"
    "- `How can I make this campaign more COM-B aligned?`\n"
)