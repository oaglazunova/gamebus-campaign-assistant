from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from checker_wrapper.checker_wrapper import (
    CONSISTENCY,
    REACHABILITY,
    SECRETS,
    SPELLCHECKER,
    TARGETPOINTSREACHABLE,
    TTMSTRUCTURE,
    VISUALIZATIONINTERN,
    explain_ttm,
    run_campaign_checks,
    summarize_result,
)

st.set_page_config(page_title="GameBus Campaign Assistant", page_icon="🩺", layout="wide")

CHECK_OPTIONS = [
    REACHABILITY,
    CONSISTENCY,
    VISUALIZATIONINTERN,
    TARGETPOINTSREACHABLE,
    SECRETS,
    TTMSTRUCTURE,
    # SPELLCHECKER,  # keep disabled in MVP; it needs extra local setup
]

FRIENDLY_NAMES = {
    REACHABILITY: "Reachability",
    CONSISTENCY: "Consistency",
    VISUALIZATIONINTERN: "Visualization internals",
    TARGETPOINTSREACHABLE: "Target points reachable",
    SECRETS: "Secrets",
    TTMSTRUCTURE: "TTM structure",
    SPELLCHECKER: "Spellchecker",
}


def save_uploaded_file(uploaded_file) -> Path:
    temp_dir = Path(tempfile.gettempdir()) / "gamebus_campaign_assistant_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = temp_dir / uploaded_file.name
    file_path.write_bytes(uploaded_file.getbuffer())
    return file_path


def format_issue(issue: Dict[str, Any]) -> str:
    wave_note = "active wave" if issue.get("active_wave") else "inactive / non-active wave"
    challenge = issue.get("challenge") or "(no challenge name)"
    visualization = issue.get("visualization") or "(no visualization)"
    return (
        f"- **{challenge}** in **{visualization}** ({wave_note})\n"
        f"  - {issue.get('message')}\n"
        f"  - Edit URL: {issue.get('url')}"
    )


def issues_for_check(result: Dict[str, Any], check_name: str) -> List[Dict[str, Any]]:
    return result.get("issues_by_check", {}).get(check_name, [])


def answer_question(question: str, result: Dict[str, Any]) -> str:
    q = question.lower().strip()

    if any(x in q for x in ["summary", "summarize", "overview"]):
        return summarize_result(result)

    if "failed" in q and "check" in q:
        failed = result["summary"]["failed_checks"]
        if not failed:
            return "No checks failed."
        return "Failed checks: " + ", ".join(f"`{x}`" for x in failed)

    if "fix first" in q or "priority" in q or "priorit" in q:
        issues = result.get("prioritized_issues", [])[:5]
        if not issues:
            return "There are no issues to prioritize."
        lines = ["I would fix these first:"]
        for issue in issues:
            lines.append(format_issue(issue))
        return "\n".join(lines)

    if "ttm" in q and ("explain" in q or "what" in q or "mean" in q):
        return explain_ttm()

    for check_name in CHECK_OPTIONS + [SPELLCHECKER]:
        if check_name in q:
            issues = issues_for_check(result, check_name)
            friendly = FRIENDLY_NAMES.get(check_name, check_name)
            if not issues:
                return f"I found no {friendly.lower()} issues."
            lines = [f"Here are the **{friendly}** issues:"]
            for issue in issues[:20]:
                lines.append(format_issue(issue))
            if len(issues) > 20:
                lines.append(f"... and {len(issues) - 20} more.")
            if check_name == TTMSTRUCTURE:
                lines.append("\n" + explain_ttm())
            return "\n".join(lines)

    if "active wave" in q:
        active = [i for i in result.get("prioritized_issues", []) if i.get("active_wave")]
        if not active:
            return "I found no prioritized issues in currently active waves."
        lines = ["These prioritized issues are in active waves:"]
        for issue in active[:10]:
            lines.append(format_issue(issue))
        return "\n".join(lines)

    return (
        "I can help with:\n"
        "- `summary` or `overview`\n"
        "- `which checks failed`\n"
        "- `show ttm issues`\n"
        "- `show reachability issues`\n"
        "- `show consistency issues`\n"
        "- `show targetpointsreachable issues`\n"
        "- `what should I fix first`\n"
        "- `explain ttm`"
    )


def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "result" not in st.session_state:
        st.session_state.result = None


init_state()

st.title("GameBus Campaign Assistant")
st.caption("MVP: upload a GameBus campaign Excel export, run the existing checks, and inspect the results through chat.")

with st.sidebar:
    st.header("Run checks")
    uploaded_file = st.file_uploader("Upload a campaign Excel export", type=["xlsx"])

    selected_checks = st.multiselect(
        "Checks to run",
        options=CHECK_OPTIONS,
        default=CHECK_OPTIONS,
        format_func=lambda x: FRIENDLY_NAMES.get(x, x),
    )

    export_excel = st.checkbox("Generate downloadable Excel issue report", value=True)

    run_clicked = st.button("Analyze campaign", type="primary", use_container_width=True)

if run_clicked:
    if not uploaded_file:
        st.error("Please upload a .xlsx campaign export first.")
    elif not selected_checks:
        st.error("Please select at least one check.")
    else:
        with st.spinner("Running campaign checks..."):
            file_path = save_uploaded_file(uploaded_file)
            result = run_campaign_checks(file_path, checks=selected_checks, export_excel=export_excel)
            st.session_state.result = result
            st.session_state.messages = [
                {"role": "assistant", "content": summarize_result(result)}
            ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.result:
    result = st.session_state.result

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Quick overview")
        st.write(result["summary"])

    with col2:
        if result.get("excel_report_path"):
            report_path = Path(result["excel_report_path"])
            st.download_button(
                label="Download Excel issue report",
                data=report_path.read_bytes(),
                file_name=report_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    with st.expander("Issues by check type", expanded=False):
        for check_name in result["checks_run"]:
            issues = result["issues_by_check"].get(check_name, [])
            st.markdown(f"### {FRIENDLY_NAMES.get(check_name, check_name)} ({len(issues)})")
            if not issues:
                st.write("No issues.")
            else:
                for issue in issues[:10]:
                    st.markdown(format_issue(issue))
                if len(issues) > 10:
                    st.write(f"... and {len(issues) - 10} more.")

    user_question = st.chat_input("Ask about this campaign check result...")
    if user_question:
        st.session_state.messages.append({"role": "user", "content": user_question})
        answer = answer_question(user_question, result)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
else:
    st.info("Upload a campaign export and click **Analyze campaign** to begin.")