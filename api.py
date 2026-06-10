import asyncio
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

from crew import run_agent, AGENT_MAP, CONTEXT_MAP
import tools.memory_tools as memory

app = FastAPI(title="AI Agents API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_memory_available = bool(
    os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY")
)

# Seconds before a running agent task is cancelled and a 504 is returned.
# Override via AGENT_TIMEOUT env var.
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))

# Fallback in-memory store used when Supabase env vars are absent
_sessions: dict[str, list[dict]] = {}


def _load_history(session_id: str) -> list[dict]:
    if _memory_available:
        return memory.load_history(session_id)
    return _sessions.get(session_id, [])


def _save_turn(session_id: str, agent_type: str, project: str, user_msg: str, assistant_msg: str) -> None:
    if _memory_available:
        memory.save_message(session_id, agent_type, project, "user",      user_msg)
        memory.save_message(session_id, agent_type, project, "assistant", assistant_msg)
    else:
        prev = _sessions.get(session_id, [])
        _sessions[session_id] = prev + [
            {"role": "user",      "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]


def _clear_session(session_id: str) -> None:
    if _memory_available:
        memory.clear_session(session_id)
    else:
        _sessions.pop(session_id, None)


class ChatRequest(BaseModel):
    agent: str
    message: str
    project: str = "ironroad"
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    agent: str
    project: str
    session_id: str


@app.get("/")
def serve_ui():
    return FileResponse("ui/index.html")


@app.get("/agents")
def list_agents():
    return {"agents": list(AGENT_MAP.keys())}


@app.get("/projects")
def list_projects():
    return {"projects": list(CONTEXT_MAP.keys())}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())

    try:
        history = await asyncio.to_thread(_load_history, sid)
    except Exception as e:
        print(f"[WARN] Failed to load history: {e}")
        history = []

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_agent,
                req.agent,
                req.message,
                req.project,
                history,
            ),
            timeout=AGENT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Agent timed out after {AGENT_TIMEOUT}s. Try a simpler request.",
        )

    try:
        await asyncio.to_thread(_save_turn, sid, req.agent, req.project, req.message, result)
    except Exception as e:
        print(f"[WARN] Failed to save turn: {e}")

    return ChatResponse(response=result, agent=req.agent, project=req.project, session_id=sid)


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    try:
        _clear_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"cleared": session_id}


@app.get("/health")
def health():
    return {
        "status":           "ok",
        "key_loaded":       bool(os.getenv("ANTHROPIC_API_KEY")),
        "memory_backend":   "supabase" if _memory_available else "in-memory",
        "active_sessions":  len(_sessions) if not _memory_available else None,
    }
