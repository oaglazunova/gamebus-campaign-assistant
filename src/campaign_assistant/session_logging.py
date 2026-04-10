from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_json(obj: Any) -> Any:
    """
    Convert values to something JSON-safe.
    """
    if isinstance(obj, Path):
        return str(obj)

    try:
        json.dumps(obj)
        return obj
    except TypeError:
        if hasattr(obj, "__dict__"):
            return str(obj)
        return repr(obj)


@dataclass
class SessionContext:
    session_id: str
    created_at: str
    campaign_source: Optional[str] = None
    uploaded_file_name: Optional[str] = None
    uploaded_file_hash: Optional[str] = None
    campaign_abbreviation: Optional[str] = None
    selected_checks: Optional[list[str]] = None


class SessionLogger:
    def __init__(self, log_dir: str | Path = "logs", session_id: Optional[str] = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.log_path = self.log_dir / f"session_{self.session_id}.jsonl"
        self._context_logged = False

    def log(self, event_type: str, payload: Dict[str, Any]) -> None:
        record = {
            "ts": utc_now_iso(),
            "session_id": self.session_id,
            "event_type": event_type,
            "payload": safe_json(payload),
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def start_session(
        self,
        *,
        campaign_source: Optional[str] = None,
        uploaded_file_name: Optional[str] = None,
        uploaded_file_hash: Optional[str] = None,
        campaign_abbreviation: Optional[str] = None,
        selected_checks: Optional[list[str]] = None,
    ) -> None:
        """
        Write one session-context event per Streamlit session.
        """
        if self._context_logged:
            return

        self._context_logged = True
        self.log(
            "session_context",
            {
                "campaign_source": campaign_source,
                "uploaded_file_name": uploaded_file_name,
                "uploaded_file_hash": uploaded_file_hash,
                "campaign_abbreviation": campaign_abbreviation,
                "selected_checks": selected_checks,
            },
        )

    def log_upload(
        self,
        *,
        file_name: str,
        saved_path: str,
        file_hash: str,
        size_bytes: int,
    ) -> None:
        self.log(
            "file_uploaded",
            {
                "file_name": file_name,
                "saved_path": saved_path,
                "file_hash": file_hash,
                "size_bytes": size_bytes,
            },
        )

    def log_download(
        self,
        *,
        campaign_abbreviation: str,
        base_url: str,
        file_name: str,
        file_hash: str,
        saved_path: str,
    ) -> None:
        self.log(
            "campaign_downloaded",
            {
                "campaign_abbreviation": campaign_abbreviation,
                "base_url": base_url,
                "file_name": file_name,
                "file_hash": file_hash,
                "saved_path": saved_path,
            },
        )

    def log_analysis_requested(
        self,
        *,
        file_path: str,
        selected_checks: list[str],
        export_excel: bool,
    ) -> None:
        self.log(
            "analysis_requested",
            {
                "file_path": file_path,
                "selected_checks": selected_checks,
                "export_excel": export_excel,
            },
        )

    def log_analysis_completed(
        self,
        *,
        file_path: str,
        selected_checks: list[str],
        export_excel: bool,
        result_summary: Dict[str, Any],
        assistant_summary: str,
        excel_report_path: Optional[str] = None,
    ) -> None:
        self.log(
            "analysis_completed",
            {
                "file_path": file_path,
                "selected_checks": selected_checks,
                "export_excel": export_excel,
                "result_summary": result_summary,
                "assistant_summary": assistant_summary,
                "excel_report_path": excel_report_path,
            },
        )

    def log_chat_user(self, message: str) -> None:
        self.log("chat_user_message", {"message": message})

    def log_chat_assistant(self, message: str) -> None:
        self.log("chat_assistant_message", {"message": message})

    def log_error(
        self,
        *,
        where: str,
        exc: Exception,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.log(
            "error",
            {
                "where": where,
                "error_type": type(exc).__name__,
                "message": str(exc),
                "extra": extra or {},
            },
        )

    def read_text(self) -> str:
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding="utf-8")