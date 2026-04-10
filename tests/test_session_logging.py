from campaign_assistant.session_logging import SessionLogger


def test_session_logger_writes_jsonl(tmp_path):
    logger = SessionLogger(log_dir=tmp_path)
    logger.start_session(
        campaign_source="upload",
        uploaded_file_name="campaign.xlsx",
        uploaded_file_hash="abc123",
        selected_checks=["ttm"],
    )
    logger.log_chat_user("Show me TTM issues")
    logger.log_chat_assistant("There are 2 TTM issues.")

    text = logger.read_text()

    assert "session_context" in text
    assert "chat_user_message" in text
    assert "chat_assistant_message" in text