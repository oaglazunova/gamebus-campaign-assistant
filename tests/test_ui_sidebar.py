from unittest.mock import MagicMock, patch
from pathlib import Path
from campaign_assistant.ui.sidebar import render_sidebar

def test_render_sidebar_download_button_state():
    # Mock streamlit
    with patch("campaign_assistant.ui.sidebar.st") as mock_st, \
         patch("campaign_assistant.ui.sidebar.save_password") as mock_save_password, \
         patch("campaign_assistant.ui.sidebar.load_password") as mock_load_password, \
         patch("campaign_assistant.ui.sidebar.save_settings") as mock_save_settings:
        
        mock_load_password.return_value = None
        
        # Initial setup: No result in session state
        mock_st.session_state = MagicMock()
        mock_st.session_state.settings = {"last_source_mode": "Upload Excel file"}
        mock_st.session_state.get.return_value = None # No result
        
        # mock text_input to return strings
        mock_st.text_input.return_value = ""
        mock_st.checkbox.return_value = False
        mock_st.radio.return_value = "Upload Excel file"
        mock_st.multiselect.return_value = []
        
        # We need to mock the context managers used in sidebar
        mock_st.sidebar = MagicMock()
        mock_st.expander.return_value.__enter__.return_value = None
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        
        # 1. No result: Download button should be disabled (via st.button)
        render_sidebar()
        
        # Check if st.button was called for the disabled state
        # It's called after Analyzing campaign button
        # The key for disabled button is 'sidebar_download_report_disabled'
        disabled_button_calls = [
            call for call in mock_st.button.call_args_list 
            if call.kwargs.get("key") == "sidebar_download_report_disabled"
        ]
        assert len(disabled_button_calls) == 1
        assert disabled_button_calls[0].kwargs.get("disabled") is True
        


        
        result = {
            "excel_report_path": "dummy.xlsx",
            "summary": {"total_issues": 3}
        }
        mock_st.session_state.get.return_value = result
        
        with patch("campaign_assistant.ui.sidebar.Path.exists", return_value=True), \
             patch("campaign_assistant.ui.sidebar.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            render_sidebar()
            
            # Should have called download_button
            mock_st.download_button.assert_called_once()
            assert mock_st.download_button.call_args.kwargs.get("disabled") is False

        # 3. Result exists, NO issues found, file exists: Download button should be disabled
        mock_st.button.reset_mock()
        mock_st.download_button.reset_mock()
        
        result_no_issues = {
            "excel_report_path": "dummy.xlsx",
            "summary": {"total_issues": 0}
        }
        mock_st.session_state.get.return_value = result_no_issues
        
        with patch("campaign_assistant.ui.sidebar.Path.exists", return_value=True):
            render_sidebar()
            
            # Should NOT have called download_button (because we use st.button for disabled state)
            mock_st.download_button.assert_not_called()
            
            # Should have called st.button with disabled=True
            disabled_button_calls = [
                call for call in mock_st.button.call_args_list 
                if call.kwargs.get("key") == "sidebar_download_report_disabled"
            ]
            assert len(disabled_button_calls) == 1
            assert disabled_button_calls[0].kwargs.get("disabled") is True

        # 4. Result exists, issues found, but report NOT generated: Download button should be disabled
        mock_st.button.reset_mock()
        mock_st.download_button.reset_mock()
        
        result_no_report = {
            "excel_report_path": None,
            "summary": {"total_issues": 5}
        }
        mock_st.session_state.get.return_value = result_no_report
        
        render_sidebar()
        
        mock_st.download_button.assert_not_called()
        disabled_button_calls = [
            call for call in mock_st.button.call_args_list 
            if call.kwargs.get("key") == "sidebar_download_report_disabled"
        ]
        assert len(disabled_button_calls) == 1
        assert disabled_button_calls[0].kwargs.get("disabled") is True
