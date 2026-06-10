"""Supabase-backed conversation memory."""

import os
from supabase import create_client, Client

TABLE = "agent_memory"


def _client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise EnvironmentError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
    return create_client(url, key)


def save_message(
    session_id: str,
    agent_type: str,
    project: str,
    role: str,
    content: str,
) -> None:
    """Insert a single message into agent_memory."""
    _client().table(TABLE).insert({
        "session_id": session_id,
        "agent_type": agent_type,
        "project":    project,
        "role":       role,
        "content":    content,
    }).execute()


def load_history(session_id: str, limit: int = 20) -> list[dict]:
    """Return the most recent `limit` messages for a session as {role, content} dicts."""
    response = (
        _client()
        .table(TABLE)
        .select("role, content")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return response.data or []


def clear_session(session_id: str) -> None:
    """Delete all rows for a session."""
    _client().table(TABLE).delete().eq("session_id", session_id).execute()
